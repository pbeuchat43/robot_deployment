"""Optional selected Pico integrations; component tools retain target checks."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import json
import os
from pathlib import Path
import subprocess
import uuid

from .artifacts import acquire_git, run, verify_source
from .commands import graph_for
from .configuration import require, within
from .maintenance import current
from .records import claim, locked, write_json

PLATFORMS = {"waveshare_rp2040_zero": "rp2040", "waveshare_rp2350_zero": "rp2350-arm-s"}


def selected(graph, target):
    recipe = graph["composition"].get("firmware", {}).get(target)
    require(recipe is not None, f"Composition does not select {target} firmware; declare its exact source, component path and supported board, then install the selected toolchain")
    return recipe


def provision(graph, release, cache, command, *, source_cache=None):
    sdk_selection = graph["sources"]["dependencies"]["pico_sdk"]
    tool_selection = graph["sources"]["dependencies"]["picotool"]
    require(sdk_selection["version"] == tool_selection["version"] == "2.3.1", "These component interfaces require Pico SDK/picotool 2.3.1")
    sdk = acquire_git("pico-sdk", sdk_selection, cache, source_cache=source_cache)
    command(["git", "submodule", "update", "--init", "--recursive", "--jobs", "2"], cwd=sdk)
    submodules = run(["git", "submodule", "status", "--recursive"], cwd=sdk, capture=True)
    require(all(line and line[0] not in ("-", "+", "U") for line in submodules.splitlines()), "Pico SDK submodule identity mismatch")
    verify_source(sdk, sdk_selection["commit"])
    tool = acquire_git("picotool", tool_selection, cache, source_cache=source_cache)
    destination = release / "firmware"
    destination.mkdir()
    build = release / "build/picotool"
    command(["cmake", "-S", tool, "-B", build, "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
        "-DPICO_SDK_PATH=" + str(sdk), "-DCMAKE_INSTALL_PREFIX=" + str(destination / "tools"),
        "-DPICOTOOL_FLAT_INSTALL=1", "-DPICOTOOL_NO_LIBUSB=OFF"])
    command(["cmake", "--build", build, "--parallel", "2"])
    command(["cmake", "--install", build])
    flat = destination / "tools/picotool"
    for name in ("picotool", "picotoolConfig.cmake"):
        require((flat / name).is_file() and not (flat / name).is_symlink(), "Picotool requires a regular flat installation: " + name)
    version = run([flat / "picotool", "version"], capture=True)
    require(version.startswith("picotool v2.3.1") and "without usb" not in version.lower(), "USB-enabled picotool 2.3.1 is required")
    libraries = run(["ldd", flat / "picotool"], capture=True)
    require("libusb-1.0" in libraries and "not found" not in libraries, "Picotool USB libraries are unresolved")
    recipes = {}
    for target, recipe in graph["composition"]["firmware"].items():
        repository = acquire_git("firmware-" + target, recipe["source"], cache, source_cache=source_cache)
        source = within(repository, recipe["path"])
        require((source / "CMakeLists.txt").is_file(), "Selected firmware component has no build interface")
        recipes[target] = dict(repository=str(repository), source=str(source), commit=recipe["source"]["commit"], board=recipe["board"])
    write_json(destination / "tools.json", dict(schema_version=1, pico_sdk=dict(sdk_selection, path=str(sdk)),
        picotool=dict(tool_selection, path=str(flat)), sdk_submodules=submodules, recipes=recipes))


def installed(graph, target):
    recipe = selected(graph, target)
    release_id = current(graph["site"])
    require(release_id is not None, "Select a completed installation before firmware operations")
    release = Path(graph["site"]["storage"]["installation_root"]) / "releases" / release_id
    path = release / "firmware/tools.json"
    require(path.is_file(), "Install the selected firmware toolchain first")
    tools = json.loads(path.read_text())
    expected = tools["recipes"].get(target)
    require(expected and expected["commit"] == recipe["source"]["commit"] and expected["board"] == recipe["board"], "Installed firmware selection differs from composition; upgrade explicitly")
    verify_source(Path(expected["repository"]), expected["commit"])
    require(tools["pico_sdk"]["commit"] == graph["sources"]["dependencies"]["pico_sdk"]["commit"] and
            tools["picotool"]["commit"] == graph["sources"]["dependencies"]["picotool"]["commit"], "Installed Pico tool selections changed")
    verify_source(Path(tools["pico_sdk"]["path"]), tools["pico_sdk"]["commit"])
    return recipe, tools, release


def info(site_path=None, definitions=None, *, target):
    graph = graph_for(site_path, definitions)
    recipe = selected(graph, target)
    return dict(target=target, recipe=recipe, pico_sdk=graph["sources"]["dependencies"]["pico_sdk"],
                picotool=graph["sources"]["dependencies"]["picotool"], device_probe="not_run")


def build(site_path=None, definitions=None, *, target):
    graph = graph_for(site_path, definitions)
    recipe, tools, release = installed(graph, target)
    output = claim(Path(graph["site"]["storage"]["data_root"]) / "build/firmware" / target / recipe["board"] / recipe["source"]["commit"], purpose="firmware-build")
    source = tools["recipes"][target]["source"]
    sdk, picotool = tools["pico_sdk"]["path"], tools["picotool"]["path"]
    with locked(output):
        subprocess.run(["cmake", "-S", source, "-B", str(output / "build"), "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
            "-DPICO_BOARD=" + recipe["board"], "-DPICO_PLATFORM=" + PLATFORMS[recipe["board"]],
            "-DPICO_SDK_PATH=" + sdk, "-Dpicotool_DIR=" + picotool, "-DFETCHCONTENT_FULLY_DISCONNECTED=ON"], check=True)
        subprocess.run(["cmake", "--build", str(output / "build"), "--target", target + "_firmware_bundle", "--parallel", "2"], check=True)
    return dict(target=target, board=recipe["board"], manifest=str(output / "build" / (target + "_pico_firmware.manifest.json")), flashed=False)


def flash_call(target, tools, python, manifest, device_id, report):
    source = Path(tools["recipes"][target]["source"])
    argv = [str(python), str(source / "tools" / ("flash_" + target + "_firmware.py"))]
    env = dict(os.environ, PICO_SDK_PATH=tools["pico_sdk"]["path"])
    if target == "bno08x":
        argv += ["flash", "--report", str(report), "--expected-pico-sdk-commit", tools["pico_sdk"]["commit"]]
        env["BNO08X_PICOTOOL_DIR"] = tools["picotool"]["path"]
    else:
        require(report is None, "The Traxxas owner emits its report to stdout and has no --report option")
        argv += ["--picotool-dir", tools["picotool"]["path"]]
    argv += ["--manifest", str(manifest), "--device-id", device_id]
    return argv, env


def flash(site_path=None, definitions=None, *, target, manifest, device_id, report=None):
    graph = graph_for(site_path, definitions)
    _recipe, tools, release = installed(graph, target)
    if target == "bno08x" and report is None:
        reports = Path(graph["site"]["storage"]["data_root"]) / "deployment/firmware-reports"
        reports.mkdir(exist_ok=True)
        report = reports / (uuid.uuid4().hex + ".json")
    argv, env = flash_call(target, tools, release / "venv/bin/python", manifest, device_id, report)
    # Inherit the terminal: the component's explicit target confirmation remains.
    subprocess.run(argv, env=env, check=True)
    return dict(target=target, result="component_completed", report=str(report) if report else "component stdout")
