"""Explicit ROS builds in owned output directories; no runtime lifecycle calls."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import json
from pathlib import Path
import shutil
import subprocess

from .artifacts import verify_source
from .commands import graph_for
from .components import ros_environment, ros_packages, with_ros
from .configuration import file_digest, require
from .maintenance import current
from .records import claim, locked, write_json


def clean_outputs(root):
    root = Path(root).resolve()
    for name in ("build", "install", "log"):
        target = root / name
        require(not target.is_symlink() and target.resolve().is_relative_to(root), "Unsafe generated build path: " + str(target))
        if target.exists():
            shutil.rmtree(target)


def ros(site_path=None, definitions=None, *, workspace, clean=False):
    graph = graph_for(site_path, definitions)
    site = graph["site"]
    selected = current(site)
    require(selected is not None, "Select a completed system installation before building workspaces")
    installation = Path(site["storage"]["installation_root"])
    release = installation / "releases" / selected
    setup = release / "ros/install/setup.bash"
    require(setup.is_file(), "Selected system ROS underlay is missing")
    if workspace == "student":
        binding = site["workspaces"].get("student")
        require(binding is not None, "Declare workspaces.student in the private site")
        source = Path(binding).resolve() / "src"
        require(source.is_dir(), "Student workspace requires an existing src directory")
        output = claim(source.parent / ".robot-deployment", purpose="student-build")
    else:
        output = claim(Path(site["storage"]["data_root"]) / "build/system" / selected, purpose="system-build")
        source = output / "src"
        source.mkdir(exist_ok=True)
        selections = dict(graph["sources"]["components"], vision_msgs=graph["sources"]["dependencies"]["vision_msgs"])
        vehicle = graph["composition"]["units"].get("vehicle")
        if vehicle:
            selections["rc_car_interface"] = vehicle["source"]
        for name in ros_packages(selections):
            revision = selections[name]["commit"]
            checkout = installation / "cache/git" / (name + "-" + revision)
            require(checkout.is_dir(), "Missing pinned system source; complete installation first: " + name)
            verify_source(checkout, revision)
            package = checkout / "ros/robot_runtime_recording" if name == "robot_runtime" else checkout
            require(package.is_dir(), "Missing pinned ROS package: " + str(package))
            link = source / ("robot_runtime_recording" if name == "robot_runtime" else name)
            if link.exists() or link.is_symlink():
                require(link.is_symlink() and link.resolve() == package.resolve(), "System source binding changed; use a new owned build directory")
            else:
                link.symlink_to(package, target_is_directory=True)
    with locked(output):
        record = output / "binding.json"
        identity = dict(schema_version=1, underlay=str(setup), underlay_sha256=file_digest(setup), workspace=workspace)
        if record.exists() and json.loads(record.read_text()) != identity:
            require(clean, "System underlay changed; rebuild with --clean to avoid mixing generated artifacts")
        if clean:
            clean_outputs(output)
        write_json(record, identity)
        argv = ["colcon", "--log-base", str(output / "log"), "build", "--base-paths", str(source),
            "--build-base", str(output / "build"), "--install-base", str(output / "install"), "--merge-install", "--executor", "sequential"]
        if workspace == "system":
            argv += ["--cmake-args", "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_TESTING=OFF", "-DRGBD_CAMERA_ENABLE_REALSENSE=ON",
                "-DCMAKE_PREFIX_PATH=" + ";".join(str(release / "sdk" / name) for name in ("depthai", "realsense")),
                "-DCUDAToolkit_ROOT=/usr/local/cuda-13.2",
                "-DNLOHMANN_JSON_INCLUDE_DIR=" + str(release / "sdk/depthai/include")]
        subprocess.run(with_ros(argv, setup=setup if workspace == "student" else None),
                       env=ros_environment(release), cwd=source.parent, check=True)
    return dict(workspace=workspace, install=str(output / "install"), runtime_restarted=False, dependencies_installed=False)
