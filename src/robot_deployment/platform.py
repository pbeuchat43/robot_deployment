"""Admit the selected host and render reviewable, versioned prerequisite actions."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import argparse
import json
import os
from pathlib import Path
import platform as host_platform
import re
import shlex
import shutil
import subprocess
import sys

from .artifacts import run
from .configuration import require, load, encoded, digest

PACKAGES = """
ca-certificates git build-essential cmake ninja-build pkg-config libssl-dev libusb-1.0-0-dev
libopencv-dev python3-dev python3-venv python3-pip python3-colcon-common-extensions
ros-jazzy-ros-base ros-jazzy-ament-cmake ros-jazzy-ament-index-cpp ros-jazzy-rclcpp
ros-jazzy-rclcpp-components ros-jazzy-rcl-interfaces ros-jazzy-rclpy
ros-jazzy-rosidl-default-generators ros-jazzy-rosidl-default-runtime
ros-jazzy-sensor-msgs ros-jazzy-std-msgs ros-jazzy-geometry-msgs ros-jazzy-nav-msgs
ros-jazzy-launch ros-jazzy-launch-ros ros-jazzy-tf2-ros
cuda-nvcc-13-2 cuda-cudart-dev-13-2 libnvinfer-dev libnvinfer-headers-dev
libnvinfer10 libnvonnxparsers-dev libnvonnxparsers10
libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libgstreamer-plugins-bad1.0-dev
gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good
gstreamer1.0-plugins-bad gstreamer1.0-nice python3-gi python3-gst-1.0 python3-numpy
gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gir1.2-gst-plugins-bad-1.0
""".split()
ROS_BOOTSTRAP_URL = "https://github.com/ros-infrastructure/ros-apt-source/releases/download/1.1.0/ros2-apt-source_1.1.0.noble_all.deb"
ROS_BOOTSTRAP_SHA = "35441f3092fd05773a3c397fab38661bec466584c7a1f1c05366579997cb5fe7"


def package_version(name):
    result = subprocess.run(["dpkg-query", "-W", "-f=${db:Status-Abbrev} ${Version}", name], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return result.stdout.split()[-1] if result.returncode == 0 and result.stdout.startswith("ii ") else None


def inspect():
    require(sys.platform == "linux", "Host inspection must run on the target Linux robot")
    os_release = host_platform.freedesktop_os_release()
    dt = Path("/proc/device-tree/compatible")
    compatible = dt.read_bytes().decode().replace("\x00", " ").lower() if dt.exists() else ""
    packages = {name: package_version(name) for name in ("nvidia-l4t-core", "cuda-cudart-13-2", "libnvinfer10", "ros-jazzy-ros-base")}
    return dict(architecture=host_platform.machine(), os=os_release.get("ID"), os_version=os_release.get("VERSION_ID"),
                kernel=host_platform.release(), python=host_platform.python_version(), compatible=compatible,
                packages=packages, boot_id=Path("/proc/sys/kernel/random/boot_id").read_text().strip())


def admit(declared, observed):
    for key in ("architecture", "os", "os_version"):
        require(observed[key] == declared[key], f"Unsupported {key}: expected {declared[key]}, observed {observed[key]}")
    for name in ("kernel", "python"):
        require(observed[name].startswith(declared[name + "_family"] + "."), f"Unsupported {name} family")
    l4t = observed["packages"]["nvidia-l4t-core"]
    require(l4t is not None and l4t.split("-")[0] == declared["l4t"], "Install the selected JetPack/L4T base image first; this tool never upgrades it")
    require(any(item in observed["compatible"] for item in declared["modules"]), "Unsupported Jetson module; qualify an explicit platform profile")
    require(any(item in observed["compatible"] for item in declared["carriers"]), "Unsupported carrier; supply and qualify its BSP profile")
    for name, family in (("cuda-cudart-13-2", declared["cuda_family"]), ("libnvinfer10", declared["tensorrt_family"])):
        installed = observed["packages"][name]
        require(installed is None or installed.startswith(family + "."), f"Installed {name} is outside selected platform")
    return observed


def package_plan(graph):
    observed = admit(graph["platform"], inspect())
    packages = list(PACKAGES)
    if graph["site"]["visual_odometry"]["enabled"]:
        if graph["site"]["visual_odometry"]["backend"] == "docker":
            # JetPack supplies the NVIDIA runtime. Validate daemon/GPU setup in
            # the backend build/qualification; never change Docker during launch.
            require(shutil.which("docker") is not None, "Install Docker and NVIDIA Container Toolkit during host maintenance")
        else:
            packages.extend(("libnvvpi4", "ros-jazzy-cv-bridge", "ros-jazzy-visualization-msgs",
                "ros-jazzy-diagnostic-msgs", "ros-jazzy-tf2-geometry-msgs", "ros-jazzy-message-filters"))
    if graph["composition"].get("firmware"):
        packages.extend(("gcc-arm-none-eabi", "libnewlib-arm-none-eabi", "libstdc++-arm-none-eabi-newlib"))
    if graph["platform"]["encoder"] == "hardware":
        packages.append("nvidia-l4t-gstreamer")
    else:
        packages.append("gstreamer1.0-plugins-ugly")  # x264enc, explicitly software on Nano.
    selected, missing = {}, {}
    for name in packages:
        installed = package_version(name)
        policy = run(["apt-cache", "policy", name], capture=True)
        match = re.search(r"Candidate:\s+(\S+)", policy)
        candidate = match.group(1) if match and match.group(1) != "(none)" else None
        version = installed or candidate
        require(version is not None, f"Package unavailable: {name}; prepare the declared Ubuntu/ROS/NVIDIA repositories and refresh apt metadata")
        if name.startswith(("libnvinfer", "libnvonnxparsers")):
            require(version == "10.16.2.10-1+cuda13.2", f"Unexpected TensorRT package selection: {name}={version}")
        if name.startswith("nvidia-l4t-"):
            require(version.split("-")[0] == graph["platform"]["l4t"], "NVIDIA package would change the selected BSP family")
        selected[name] = version
        if installed is None:
            missing[name] = version
    argv = ["apt-get", "install", "--no-remove", "--no-install-recommends", *[name + "=" + value for name, value in missing.items()]]
    simulation = run([argv[0], "-s", *argv[1:]], capture=True) if missing else "No packages missing."
    reject_bsp_changes(simulation)
    return dict(schema_version=1, platform=graph["platform"]["id"], host=observed,
                packages=selected, missing=missing, argv=argv, simulation=simulation,
                simulation_sha256=digest(simulation.encode()))


def reject_bsp_changes(simulation):
    require(not re.search(r"^Remv ", simulation, re.MULTILINE), "Prerequisites would remove installed packages; resolve explicitly")
    require(not re.search(r"^Inst nvidia-l4t-\S+ \[", simulation, re.MULTILINE), "Prerequisites would upgrade the BSP; retain the selected image")


def prerequisite_script(plan):
    """Script repeats the exact transaction simulation before privileged install."""
    if not plan["missing"]:
        return "#!/bin/bash\nset -euo pipefail\nprintf '%s\\n' 'All declared prerequisites are installed.'\n"
    command = shlex.join(plan["argv"])
    simulation = shlex.join([plan["argv"][0], "-s", *plan["argv"][1:]])
    l4t = shlex.quote(plan["host"]["packages"]["nvidia-l4t-core"])
    # Compare the meaningful transaction lines; apt advisory text can depend on uid.
    transactions = "\n".join(line for line in plan["simulation"].splitlines() if line.startswith(("Inst ", "Conf ", "Remv ")))
    return ("#!/bin/bash\nset -euo pipefail\nexport LC_ALL=C\n"
            "test \"$(id -u)\" = 0 || { echo 'Run this reviewed script with sudo' >&2; exit 2; }\n"
            f"test \"$(dpkg-query -W -f='${{Version}}' nvidia-l4t-core)\" = {l4t}\n"
            f"expected={shlex.quote(transactions)}\n"
            f"actual=$({simulation} | sed -n '/^Inst /p;/^Conf /p;/^Remv /p')\n"
            "test \"$actual\" = \"$expected\" || { printf '%s\\n' 'Package transaction changed; regenerate the plan.' \"$actual\" >&2; exit 2; }\n"
            f"{command} -y\n")


def repository_script():
    """Fresh-host repository bootstrap; separate from selecting package versions."""
    return f'''#!/bin/bash
set -euo pipefail
test "$(id -u)" = 0
test "$(dpkg --print-architecture)" = arm64
. /etc/os-release
test "$ID:$VERSION_ID" = ubuntu:24.04
export LC_ALL=C
apt-get update
apt-get install --no-remove -y ca-certificates curl software-properties-common
add-apt-repository -y universe
artifact=$(mktemp /tmp/robot-ros-source.XXXXXXXX.deb)
trap 'rm -f -- "$artifact"' EXIT
curl --fail --location --retry 3 {ROS_BOOTSTRAP_URL} --output "$artifact"
printf '%s  %s\\n' {ROS_BOOTSTRAP_SHA} "$artifact" | sha256sum --check -
dpkg -i "$artifact"
apt-get update
printf '%s\\n' 'Repository setup complete. Resolve and review the platform prerequisite plan next.'
'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--definitions", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New package plan JSON; sibling .sh contains root actions")
    args = parser.parse_args(argv)
    graph = load(args.site, args.definitions)
    plan = package_plan(graph)
    with args.output.open("x") as stream:
        json.dump(plan, stream, indent=2)
    with args.output.with_suffix(".sh").open("x") as stream:
        stream.write(prerequisite_script(plan))
    print(json.dumps(dict(plan=str(args.output), missing=plan["missing"])))


if __name__ == "__main__":
    main()
