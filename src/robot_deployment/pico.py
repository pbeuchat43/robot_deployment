"""Deployment-owned Pico discovery and operator routes."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
from contextlib import contextmanager, nullcontext
import json
import os
from pathlib import Path
import re
import subprocess

from .commands import graph_for
from .configuration import require

USB = {"0003": ("BOOTSEL", "RP2040"), "000f": ("BOOTSEL", "RP2350"),
       "000a": ("application", "RP2040"), "0009": ("application", "RP2350")}
HELPER = "ros/install/lib/rc_car_interface/rc_car_ctl"


def _attr(path):
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def inventory(sysfs=Path("/sys"), devices=Path("/dev")):
    """Read kernel metadata only. In BOOTSEL the ROM serial may differ from the application ID."""
    ttys = {}
    for tty in (sysfs / "class/tty").glob("ttyACM*"):
        try:
            parents = (tty / "device").resolve(strict=True).parents
        except OSError:
            continue
        for parent in parents:
            ttys.setdefault(parent, []).append(str(devices / tty.name))
    found = []
    for port in sorted((sysfs / "bus/usb/devices").glob("*")):
        product_id = _attr(port / "idProduct")
        if _attr(port / "idVendor") != "2e8a" or product_id not in USB:
            continue
        bus, address = _attr(port / "busnum"), _attr(port / "devnum")
        if not bus.isdecimal() or not address.isdecimal():
            continue
        state, chip = USB[product_id]
        paths = sorted(ttys.get(port.resolve(), []))
        usb_node = devices / "bus/usb" / f"{int(bus):03}" / f"{int(address):03}"
        found.append(dict(usb_port=port.name, bus=int(bus), address=int(address), vid_pid="2e8a:" + product_id,
                          product=_attr(port / "product"), usb_serial=_attr(port / "serial"), chip=chip,
                          state=state, tty=paths[0] if len(paths) == 1 else None,
                          usb_node=str(usb_node), usb_accessible=os.access(usb_node, os.R_OK | os.W_OK)))
    return found


def listing(**_):
    return dict(devices=inventory(), serial_opened=False)


def vehicle_pin(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,24}", value)


def device_pin(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9A-F]{16}", value)


def application(devices, device=None):
    return [item for item in devices if item["state"] == "application" and item["product"] == "RC Car Pico"
            and (device is None or item["usb_serial"] == device)]


@contextmanager
def stopped_site(site):
    """Hold both deployment and runtime reservations without stopping any process."""
    from robot_runtime.maintenance import stopped
    from . import maintenance, services
    from .records import locked

    root = Path(site["storage"]["installation_root"])
    state = Path(site["storage"]["data_root"]) / "runtime"
    with locked(root):
        require(not services.active(site), "Stop runtime management and owned workloads before direct Pico maintenance")
        maintenance.audited_stopped(site, management_active=False)
        with stopped(state):
            yield


def resolve(site_path, definitions, *, standalone, client, device_id, profile_id, build_id, needed=True):
    if standalone:
        require(site_path is None and definitions is None, "--standalone is separate from --site and --definitions")
        site = None
    else:
        require(client is None, "Use --standalone with an explicit --client")
        graph = graph_for(site_path, definitions)
        site = graph["site"]
        pins = site.get("hardware", {}).get("rc_car", {})
        for key, requested in (("device_id", device_id), ("profile_id", profile_id), ("build_id", build_id)):
            require(not (key in pins and requested is not None and pins[key] != requested),
                    f"{key} conflicts with the private site selection")
        device_id = device_id or pins.get("device_id")
        profile_id = profile_id or pins.get("profile_id")
        build_id = build_id or pins.get("build_id")
        client = Path(site["storage"]["installation_root"]) / "current" / HELPER
    require(device_id is None or device_pin(device_id), "Expected a 16-digit uppercase device ID")
    require(all(value is None or vehicle_pin(value) for value in (profile_id, build_id)), "Invalid profile or build ID")
    available = client is not None and client.is_absolute() and client.is_file() and os.access(client, os.X_OK)
    if needed:
        require(available, "Install rc_car_ctl or supply an absolute --standalone --client path")
    return site, client if available else None, device_id, profile_id, build_id


def client_argv(client, action, device=None, profile=None, build=None):
    result = [str(client), action]
    for option, value in (("--device-id", device), ("--profile-id", profile), ("--build-id", build)):
        if value:
            result.extend((option, value))
    return result


def read_client(client, action, device=None, profile=None, build=None):
    proc = subprocess.run(client_argv(client, action, device, profile, build),
                          text=True, capture_output=True, timeout=4)
    if not proc.stdout.strip():
        raise ValueError(proc.stderr.strip() or "Pico client returned no status")
    return json.loads(proc.stdout), proc.returncode


def _show_watch(argv, *, structured):
    with subprocess.Popen(argv, text=True, stdout=subprocess.PIPE) as child:
        try:
            for line in child.stdout:
                if structured:
                    print(line.rstrip(), flush=True)
                else:
                    s = json.loads(line)
                    print(f"{s['tick_ms']:>10} ms  {s['mode']:<9} {s['reason']:<15} "
                          f"RC {s['rc_quality']:<7} input {s['rc_drive_us']}/{s['rc_steer_us']} µs  "
                          f"PWM {s['drive_pwm_us']}/{s['steer_pwm_us']}/{s['pan_pwm_us']} µs  "
                          f"{s['drive_source']}/{s['steer_source']}", flush=True)
            return child.wait(timeout=3)
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=2)


def operate(site_path=None, definitions=None, *, action, standalone=False, client=None, device_id=None,
            profile_id=None, build_id=None, duration=30, structured=False):
    site, client, device, profile, build = resolve(site_path, definitions, standalone=standalone, client=client,
        device_id=device_id, profile_id=profile_id, build_id=build_id, needed=action != "doctor")
    if action == "doctor":
        return doctor(client, device, profile, build)
    if action == "watch":
        require(1 <= duration <= 600, "Watch duration must be 1–600 seconds")
        return _show_watch([*client_argv(client, action, device, profile, build), "--duration", str(duration)],
                           structured=structured)
    changing = action in ("manual", "hold")
    if changing:
        require(device and profile and build, "Mode changes require the exact device, profile, and build IDs")
    with stopped_site(site) if changing and site is not None else nullcontext():
        result, code = read_client(client, action, device, profile, build)
    if changing:
        from .cli import emit
        emit(result, structured=structured)
        return code
    require(code == 0 and result.get("fresh"), "Pico did not return a fresh status")
    return result


def doctor(client, device, profile, build):
    devices = inventory()
    matches = application(devices, device)
    result = dict(device_id=device, devices=devices, matching_application=len(matches),
                  client_available=client is not None)
    if len(matches) != 1:
        result["issue"] = ("Ambiguous RC Car Pico selection" if matches else
                           "No matching RC Car application. Check the cable, selector, or BOOTSEL state.")
        if not matches and any(d["state"] == "BOOTSEL" and not d["usb_accessible"] for d in devices):
            result["hint"] = "A BOOTSEL device is visible without read/write access. Check its USB permissions before flashing."
        return result
    tty = matches[0]["tty"]
    if not tty or not os.access(tty, os.R_OK | os.W_OK):
        result["issue"] = "Matching Pico has no accessible serial port. Check tty permissions and group membership."
        return result
    if not client:
        result["issue"] = "RC Car USB client is unavailable"
        return result
    try:
        status, code = read_client(client, "status", device, profile, build)
        result.update(ready=code == 0 and status.get("fresh", False), status=status)
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        result["issue"] = str(error)
        if "busy" in str(error).lower() or "temporarily unavailable" in str(error).lower():
            result["hint"] = "Use the running interface through runtime, or stop the current serial owner."
    return result
