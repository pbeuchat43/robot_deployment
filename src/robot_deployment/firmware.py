"""Optional selected Pico integrations; component tools retain target checks."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from .artifacts import acquire_git, run, verify_source
from .commands import graph_for
from .configuration import digest, file_digest, keys, require, within
from .maintenance import current
from .records import claim, locked, write_json

PLATFORMS = {"waveshare_rp2040_zero": "rp2040", "waveshare_rp2350_zero": "rp2350-arm-s"}
RC_MANIFEST = "rc_car_firmware.manifest.json"
RC_RECEIPT = "rc_car_firmware.selection.json"


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
        if target == "rc_car":
            recipes[target]["profile_sha256"] = graph["firmware_profiles"][target]["sha256"]
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
    if target == "rc_car":
        require(Path(expected["source"]) == within(Path(expected["repository"]), recipe["path"]) and
                expected.get("profile_sha256") == graph["firmware_profiles"][target]["sha256"],
                "Installed RC Car source or profile differs from selection; upgrade explicitly")
    require(tools["pico_sdk"]["commit"] == graph["sources"]["dependencies"]["pico_sdk"]["commit"] and
            tools["picotool"]["commit"] == graph["sources"]["dependencies"]["picotool"]["commit"], "Installed Pico tool selections changed")
    verify_source(Path(tools["pico_sdk"]["path"]), tools["pico_sdk"]["commit"])
    return recipe, tools, release


def info(site_path=None, definitions=None, *, target):
    graph = graph_for(site_path, definitions)
    recipe = selected(graph, target)
    result = dict(target=target, recipe=recipe, pico_sdk=graph["sources"]["dependencies"]["pico_sdk"],
                  picotool=graph["sources"]["dependencies"]["picotool"], device_probe="not_run")
    if target == "rc_car":
        expected = rc_selection(graph, recipe)
        result.update(profile_sha256=expected["profile_sha256"], expected_profile_id=expected["profile_sha256"][:16],
                      artifact_manifest=str(output_dir(graph, target, recipe) / "build" / RC_MANIFEST),
                      site_pins=graph["site"]["hardware"].get("rc_car"))
    return result


def rc_selection(graph, recipe):
    return dict(source=recipe["source"]["commit"], board=recipe["board"],
                profile_sha256=graph["firmware_profiles"]["rc_car"]["sha256"],
                sdk=graph["sources"]["dependencies"]["pico_sdk"]["commit"],
                picotool=graph["sources"]["dependencies"]["picotool"]["commit"])


def output_dir(graph, target, recipe):
    root = Path(graph["site"]["storage"]["data_root"]) / "build/firmware" / target / recipe["board"] / recipe["source"]["commit"]
    return root / rc_selection(graph, recipe)["profile_sha256"] if target == "rc_car" else root


def rc_manifest(path, expected):
    value = json.loads(path.read_text())
    keys(value, ("board", "protocol", "build_id", "profile_id", "uf2", "sha256"), context="RC Car manifest")
    require(value["board"] == expected["board"] and value["profile_id"] == expected["profile_sha256"][:16] and
            value["protocol"] == "RCPv1" and value["uf2"] == "rc_car_firmware.uf2",
            "RC Car manifest does not match the selected board, protocol, profile, or artifact name")
    for key, size in (("build_id", 16), ("sha256", 64)):
        require(isinstance(value[key], str) and re.fullmatch(rf"[0-9a-f]{{{size}}}", value[key]),
                "Malformed RC Car manifest " + key)
    artifact = path.parent / value["uf2"]
    require(artifact.is_file() and not artifact.is_symlink() and file_digest(artifact) == value["sha256"],
            "RC Car UF2 digest mismatch")
    return value


def build(site_path=None, definitions=None, *, target):
    graph = graph_for(site_path, definitions)
    recipe, tools, release = installed(graph, target)
    output = claim(output_dir(graph, target, recipe), purpose="firmware-build")
    source = tools["recipes"][target]["source"]
    sdk, picotool = tools["pico_sdk"]["path"], tools["picotool"]["path"]
    with locked(output):
        extra = []
        if target == "rc_car":
            expected = rc_selection(graph, recipe)
            raw = graph["inputs"].read_bytes(graph["firmware_profiles"][target]["path"])
            require(digest(raw) == expected["profile_sha256"], "RC Car profile changed during build admission")
            header = output / "vehicle-profile.hpp"
            if header.exists():
                require(header.is_file() and not header.is_symlink() and file_digest(header) == expected["profile_sha256"],
                        "Owned RC Car build directory has a mismatched profile header")
            else:
                with header.open("xb") as stream:
                    stream.write(raw)
            extra.append("-DRC_CAR_PROFILE=" + str(header))
        subprocess.run(["cmake", "-S", source, "-B", str(output / "build"), "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
            "-DPICO_BOARD=" + recipe["board"], "-DPICO_PLATFORM=" + PLATFORMS[recipe["board"]],
            "-DPICO_SDK_PATH=" + sdk, "-Dpicotool_DIR=" + picotool, "-DFETCHCONTENT_FULLY_DISCONNECTED=ON", *extra], check=True, stdout=sys.stderr)
        subprocess.run(["cmake", "--build", str(output / "build"), "--target", target + "_firmware_bundle", "--parallel", "2"], check=True, stdout=sys.stderr)
        manifest = output / "build" / (RC_MANIFEST if target == "rc_car" else target + "_pico_firmware.manifest.json")
        if target == "rc_car":
            value = rc_manifest(manifest, expected)
            write_json(manifest.with_name(RC_RECEIPT), dict(selection=expected, manifest_sha256=file_digest(manifest),
                                                          uf2_sha256=value["sha256"]))
    return dict(target=target, board=recipe["board"], manifest=str(manifest), flashed=False)


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
    # Keep interactive stdin and the component's target confirmation; reserve
    # stdout for the deployment result, even when the component prints a report.
    subprocess.run(argv, env=env, check=True, stdout=sys.stderr)
    return dict(target=target, result="component_completed", report=str(report) if report else "component stdout")


def boot_id(picotool, target):
    """Read device identity from picotool's Device Information section."""
    output = subprocess.run([picotool, "info", "-a", *scope(target)], text=True, capture_output=True,
                            check=True, timeout=10).stdout
    device = output.partition("Device Information")[2].split("\n\n", 1)[0]
    label = "flash id" if target["chip"] == "RP2040" else "chipid"
    silicon = re.search(r"(?m)^\s*type:\s*(RP2040|RP2350)\b", device)
    identity = re.search(rf"(?mi)^\s*{label}:\s*(?:0x)?([0-9a-f]{{16}})\s*$", device)
    require(silicon and silicon.group(1) == target["chip"] and identity,
            "picotool did not establish the expected silicon and chip ID")
    return identity.group(1).upper()


def scope(target):
    return ["--bus", str(target["bus"]), "--address", str(target["address"])]


def find_boot(picotool, chip, device_id, port=None):
    from .pico import inventory

    candidates = [item for item in inventory() if item["state"] == "BOOTSEL" and item["chip"] == chip and
                  (port is None or item["usb_port"] == port)]
    matches = [item for item in candidates if boot_id(picotool, item) == device_id]
    require(len(matches) == 1, "Expected exactly one matching BOOTSEL Pico. Use pico list and check the device ID and USB port.")
    return matches[0]


def confirm_boot(picotool, target, device_id):
    from .pico import inventory

    candidates = [item for item in inventory() if item["usb_port"] == target["usb_port"]]
    require(len(candidates) == 1 and candidates[0] == target and boot_id(picotool, target) == device_id,
            "Selected BOOTSEL target changed during maintenance")


def postflight(client, target, device_id, value):
    from .pico import application, inventory, read_client

    until = time.monotonic() + 6
    while time.monotonic() < until:
        matches = application(inventory(), device_id)
        if len(matches) == 1 and matches[0]["usb_port"] == target["usb_port"] and matches[0]["tty"] and \
                os.access(matches[0]["tty"], os.R_OK | os.W_OK):
            status, code = read_client(client, "status", device_id, value["profile_id"], value["build_id"])
            require(code == 0 and status.get("fresh") and status.get("device") == device_id and
                    status.get("board") == value["board"] and status.get("profile") == value["profile_id"] and
                    status.get("build") == value["build_id"], "Running RCPv1 identity differs from the verified artifact")
            return status
        time.sleep(.05)
    raise ValueError("The selected Pico did not return as an accessible RCPv1 application on the same USB port")


def flash_rc_car(site_path=None, definitions=None, *, manifest, device_id, report=None, usb_port=None,
                 actuators_isolated=False):
    from .pico import HELPER, device_pin, stopped_site

    require(actuators_isolated, "Use physical BOOTSEL and confirm --actuators-isolated before flashing")
    require(device_pin(device_id), "An exact Pico device ID is required")
    graph = graph_for(site_path, definitions)
    site = graph["site"]
    recipe, tools, release = installed(graph, "rc_car")
    expected = rc_selection(graph, recipe)
    output = output_dir(graph, "rc_car", recipe)
    admitted = output / "build" / RC_MANIFEST
    require(manifest.resolve() == admitted.resolve() and not admitted.is_symlink(),
            "Use the manifest produced by build mcu rc-car for this selection")
    client = release / HELPER
    require(client.is_file() and os.access(client, os.X_OK), "Install rc_car_ctl to verify the application after flashing")
    tool = Path(tools["picotool"]["path"]) / "picotool"
    require(tool.is_file() and os.access(tool, os.X_OK), "Installed USB picotool is unavailable")
    chip = "RP2040" if recipe["board"] == "waveshare_rp2040_zero" else "RP2350"
    reports = Path(site["storage"]["data_root"]) / "deployment/firmware-reports"
    with stopped_site(site), locked(output):
        value = rc_manifest(admitted, expected)
        receipt = json.loads(admitted.with_name(RC_RECEIPT).read_text())
        require(receipt == dict(selection=expected, manifest_sha256=file_digest(admitted), uf2_sha256=value["sha256"]),
                "Artifact differs from the selected RC Car build receipt")
        pins = site["hardware"].get("rc_car", {})
        require(not pins or pins == dict(device_id=device_id, profile_id=value["profile_id"], build_id=value["build_id"]),
                "Device or artifact conflicts with the private site pins")
        reports.mkdir(parents=True, exist_ok=True, mode=0o700)
        report = report or reports / (uuid.uuid4().hex + ".json")
        # Reserve the report exclusively before touching the Pico. Never overwrite an unrelated record.
        with report.open("x"):
            pass
        record = dict(target="rc_car", device_id=device_id, board=recipe["board"], selection=expected,
                      manifest=value, flashed_verified=False, application_verified=False)
        try:
            with tempfile.TemporaryDirectory(dir=reports) as directory:
                staged = Path(directory) / value["uf2"]
                shutil.copyfile(admitted.parent / value["uf2"], staged)
                require(file_digest(staged) == value["sha256"], "Staged RC Car UF2 digest mismatch")
                target = find_boot(tool, chip, device_id, usb_port)
                record["usb_port"] = target["usb_port"]
                backup_dir = Path(tempfile.mkdtemp(prefix="backup-", dir=reports))
                backup = backup_dir / "previous.uf2"
                confirm_boot(tool, target, device_id)
                subprocess.run([tool, "save", "-a", "-v", backup, *scope(target)], check=True, timeout=90, stdout=sys.stderr)
                record["backup"] = str(backup)
                record["backup_sha256"] = file_digest(backup)
                confirm_boot(tool, target, device_id)
                subprocess.run([tool, "load", "-v", staged, *scope(target)], check=True, timeout=90, stdout=sys.stderr)
                record["flashed_verified"] = True
                confirm_boot(tool, target, device_id)
                cpu = ["--cpu", "arm"] if chip == "RP2350" else []
                subprocess.run([tool, "reboot", *cpu, *scope(target)], check=True, timeout=10, stdout=sys.stderr)
                record["status"] = postflight(client, target, device_id, value)
                record["application_verified"] = True
        except BaseException as error:
            record["error"] = str(error)
            raise ValueError(f"RC Car flash incomplete (flash bytes verified: {record['flashed_verified']}). See {report}: {error}") from error
        finally:
            write_json(report, record)
    return dict(record, report=str(report))
