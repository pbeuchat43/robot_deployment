"""Concrete calls to component-owned builders for the selected perception system."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from .artifacts import acquire_git, download
from .configuration import encoded, file_digest, require, within
from .records import write_json
from .output import progress


class Commands:
    def __init__(self, release):
        self.directory = Path(release) / "build/logs"
        self.directory.mkdir(parents=True, exist_ok=True)

    def __call__(self, argv, *, cwd=None, env=None):
        sequence = len(list(self.directory.glob("*.json"))) + 1
        record = self.directory / f"{sequence:04d}.json"
        output = record.with_suffix(".log")
        value = dict(argv=list(map(str, argv)), cwd=str(cwd) if cwd else None, started_at=time.time())
        write_json(record, value)
        progress(dict(event="build_command", argv=value["argv"], log=str(output)))
        with output.open("w") as stream:
            result = subprocess.run(value["argv"], cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT)
        value.update(returncode=result.returncode, completed_at=time.time())
        write_json(record, value)
        if result.returncode:
            raise subprocess.CalledProcessError(result.returncode, value["argv"], output=str(output))


def sources(graph, cache, source_cache):
    lock = graph["sources"]
    require(set(lock["components"]) == {"rgbd_camera", "rgbd_object_detector", "robot_runtime", "visual_odometry"}, "Unsupported component selection")
    result = {name: acquire_git(name, selected, cache, source_cache=source_cache) for name, selected in lock["components"].items()}
    vehicle = graph["composition"]["units"].get("vehicle")
    if vehicle:
        result["rc_car_interface"] = acquire_git("rc_car_interface", vehicle["source"], cache, source_cache=source_cache)
    result["vision_msgs"] = acquire_git("vision_msgs", lock["dependencies"]["vision_msgs"], cache, source_cache=source_cache)
    # The legacy detector is only an artifact source; it is never built or installed.
    result["cone_artifact"] = acquire_git("cone_artifact", lock["models"]["cones"]["source"], cache, source_cache=source_cache)
    for name, script in (("depthai", "build_sdk.sh"), ("librealsense", "build_realsense_sdk.sh")):
        text = (result["rgbd_camera"] / "tools" / script).read_text()
        require(lock["dependencies"][name]["commit"] in text, f"Selected {name} revision disagrees with its component-owned builder")
    return result


def sdk(name, source, release, command):
    script = "build_sdk.sh" if name == "depthai" else "build_realsense_sdk.sh"
    command(["bash", source / "tools" / script, release / "sdk" / name])


def ros_environment(release):
    return dict(HOME=str(Path.home()), PATH="/usr/local/cuda-13.2/bin:/usr/bin:/bin",
        LD_LIBRARY_PATH=":".join(str(release / "sdk" / name / "lib") for name in ("depthai", "realsense")),
        LANG="C.UTF-8", CMAKE_BUILD_PARALLEL_LEVEL="2")


def with_ros(argv, *, setup=None):
    if setup:
        return ["/bin/bash", "-c", 'set -eo pipefail; source /opt/ros/jazzy/setup.bash; source "$1"; shift; exec "$@"',
                "robot-build", str(setup), *map(str, argv)]
    return ["/bin/bash", "-c", 'set -eo pipefail; source /opt/ros/jazzy/setup.bash; exec "$@"', "robot-build", *map(str, argv)]


def ros_packages(selected):
    return ("rgbd_camera", "rgbd_object_detector", "vision_msgs", "robot_runtime") + tuple(name for name in ("visual_odometry", "rc_car_interface") if name in selected)


def ros_source(name, checkout):
    return checkout / {"robot_runtime": "ros/robot_runtime_recording", "visual_odometry": "visual_odometry_interfaces"}.get(name, "")


def ros_build(selected, release, command):
    workspace = release / "ros"
    (workspace / "src").mkdir(parents=True)
    for name in ros_packages(selected):
        # Colcon compiles from verified sources and writes separate build/install trees.
        package = ros_source(name, selected[name])
        require(package.is_dir(), "Missing pinned ROS package: " + str(package))
        link_name = {"robot_runtime": "robot_runtime_recording", "visual_odometry": "visual_odometry_interfaces"}.get(name, name)
        (workspace / "src" / link_name).symlink_to(package, target_is_directory=True)
    prefixes = ";".join(str(release / "sdk" / name) for name in ("depthai", "realsense"))
    argv = ["colcon", "build", "--merge-install", "--executor", "sequential", "--cmake-args",
            "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_TESTING=OFF", "-DRGBD_CAMERA_ENABLE_REALSENSE=ON",
            "-DCMAKE_PREFIX_PATH=" + prefixes, "-DCUDAToolkit_ROOT=/usr/local/cuda-13.2",
            "-DNLOHMANN_JSON_INCLUDE_DIR=" + str(release / "sdk/depthai/include")]
    command(with_ros(argv), cwd=workspace, env=ros_environment(release))


def python_environment(graph, selected, release, deployment_wheel, command):
    build_env = release / "build/python"
    command(["/usr/bin/python3", "-m", "venv", build_env])
    builder = build_env / "bin/python"
    command([builder, "-m", "pip", "install", "-r", graph["root"] / "config/requirements-build.lock"])
    runtime_source = release / "build/runtime-source"
    shutil.copytree(selected["robot_runtime"], runtime_source, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    wheels = release / "wheels"
    wheels.mkdir()
    command([builder, "-m", "build", "--wheel", "--no-isolation", "--outdir", wheels, runtime_source])
    require(deployment_wheel.is_file() and deployment_wheel.name.startswith("robot_deployment-"), "Supply the selected deployment wheel")
    shutil.copyfile(deployment_wheel, wheels / deployment_wheel.name)
    command([builder, "-m", "pip", "download", "--only-binary=:all:", "--dest", wheels,
             "-r", graph["root"] / "config/requirements-runtime.lock"])
    venv = release / "venv"
    command(["/usr/bin/python3", "-m", "venv", "--system-site-packages", venv])
    interpreter = venv / "bin/python"
    command([interpreter, "-m", "pip", "install", "--no-index", "--find-links", wheels,
             "--ignore-installed", "-r", graph["root"] / "config/requirements-runtime.lock",
             *sorted(wheels.glob("robot_runtime-*.whl")), wheels / deployment_wheel.name])
    command([interpreter, "-c", "import robot_runtime, robot_deployment, gi; print(robot_runtime.__version__, robot_deployment.__version__)"])


def model_inputs(graph, selected, release, cache, command):
    directory = release / "model-inputs"
    directory.mkdir()
    cone = graph["sources"]["models"]["cones"]
    source = within(selected["cone_artifact"], cone["path"])
    require(file_digest(source) == cone["onnx_sha256"], "Pinned cone repository artifact hash mismatch")
    shutil.copyfile(source, directory / "cones.onnx")
    coco = graph["sources"]["models"]["coco"]
    checkpoint = download(coco["checkpoint_url"], coco["checkpoint_sha256"], cache)
    # Only a verified normalized ONNX plus its exact exported descriptor can skip export.
    exported_cache = cache / ("coco-export-" + graph["sources"]["components"]["rgbd_object_detector"]["commit"])
    if exported_cache.exists():
        require(file_digest(exported_cache / "yolov8n.onnx") == coco["onnx_sha256"], "Corrupt cached COCO export")
        cached = json.loads((exported_cache / "cache.json").read_text())
        require(file_digest(exported_cache / "yolov8n-coco80.json") == cached["profile_sha256"], "Corrupt cached exported descriptor")
    else:
        export_env = release / "build/export-python"
        command(["/usr/bin/python3", "-m", "venv", export_env])
        python = export_env / "bin/python"
        command([python, "-m", "pip", "install", "-r", selected["rgbd_object_detector"] / "tools/requirements-export.lock"])
        command([python, selected["rgbd_object_detector"] / "tools/export_yolov8n.py", "--weights", checkpoint, "--output", exported_cache])
        require(file_digest(exported_cache / "yolov8n.onnx") == coco["onnx_sha256"], "Normalized COCO ONNX differs from selected artifact")
        write_json(exported_cache / "cache.json", dict(schema_version=1,
            profile_sha256=file_digest(exported_cache / "yolov8n-coco80.json")))
    shutil.copyfile(exported_cache / "yolov8n.onnx", directory / "coco.onnx")
    shutil.copyfile(exported_cache / "yolov8n-coco80.json", directory / "coco-profile.json")
    for name, generated in (("cones", None), ("coco", directory / "coco-profile.json")):
        descriptor = within(selected["rgbd_object_detector"], graph["composition"]["models"][name]["descriptor"])
        if generated:
            require(json.loads(generated.read_text()) == json.loads(descriptor.read_text()),
                    "Exported COCO descriptor differs from the selected component descriptor")
        else:
            shutil.copyfile(descriptor, directory / "cones-profile.json")
    shutil.copyfile(selected["rgbd_object_detector"] / "NOTICE.md", directory / "NOTICE.md")
    write_json(directory / "provenance.json", dict(schema_version=1, selections=graph["sources"]["models"],
        checkpoint_sha256=file_digest(checkpoint), exported_profile_sha256=file_digest(directory / "coco-profile.json")))


def engines(release, command):
    for name in ("cones", "coco"):
        destination = release / "models" / name
        destination.mkdir(parents=True)
        shutil.copyfile(release / "model-inputs" / (name + "-profile.json"), destination / "profile.json")
        command(with_ros(["ros2", "run", "rgbd_object_detector", "build_engine",
            release / "model-inputs" / (name + ".onnx"), destination / "model.engine", destination / "profile.json"],
            setup=release / "ros/install/setup.bash"), env=ros_environment(release))


def native(selected, release, cache, command):
    command(["/usr/bin/python3", selected["robot_runtime"] / "deployment/build-av-native.py",
             "--work", release / "build/av-native", "--cache", cache, "--destination", release / "av-native"])


def odometry(graph, selected, release, cache, command):
    command(["/usr/bin/python3", selected["visual_odometry"] / "deployment/install.py",
        "--backend", graph["site"]["visual_odometry"]["backend"], "--camera-source", selected["rgbd_camera"],
        "--destination", release / "visual-odometry", "--work", release / "build/visual-odometry", "--cache", cache,
        "--source-id", graph["sources"]["components"]["visual_odometry"]["commit"],
        "--camera-source-id", graph["sources"]["components"]["rgbd_camera"]["commit"]])
