"""Interactive Traxxas endpoint programming through the generic RCPv1 maintenance client."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import time

from .configuration import require

RECIPES = {
    "xl-5": "https://traxxas.com/sites/default/files/KC1761-R01_3018R-XL5_INST_140430-EN.pdf",
    "vxl-3s": "https://traxxas.com/media/productattach/C-67097-4/2/67097-4-om-en-r01.pdf",
}


class MaintenanceClient:
    """Bounded line client for the interface-owned, exclusive USB process."""

    def __init__(self, executable, device, profile, build):
        self.process = subprocess.Popen(
            [str(executable), device, profile, build],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0,
        )
        self.buffer = bytearray()

    def _line(self, timeout):
        end = time.monotonic() + timeout
        while b"\n" not in self.buffer:
            remaining = end - time.monotonic()
            if remaining <= 0 or not select.select([self.process.stdout], [], [], remaining)[0]:
                raise ValueError("Timed out waiting for Pico maintenance status")
            chunk = os.read(self.process.stdout.fileno(), 128)
            require(chunk, "Pico maintenance client closed before status")
            self.buffer.extend(chunk)
            require(len(self.buffer) <= 256, "Invalid maintenance client response length")
        line, _, rest = self.buffer.partition(b"\n")
        self.buffer = rest
        return line.decode("ascii").split()

    def ready(self, device, profile):
        values = self._line(1.5)
        require(len(values) == 5 and values[:3] == ["READY", device, profile],
                "Maintenance client did not confirm the selected Pico and profile")

    def command(self, command, expected_mode, drive=None, steer=None):
        self.process.stdin.write((command + "\n").encode("ascii"))
        values = self._line(.25)
        require(len(values) == 4 and values[:2] == ["OK", expected_mode],
                "Maintenance client did not confirm mode " + expected_mode)
        pulses = tuple(map(int, values[2:]))
        require(all(0 < pulse < 20_000 for pulse in pulses), "Invalid programmed pulse in maintenance status")
        require(drive is None or pulses[0] == drive,
                "Programmed drive pulse does not match the selected endpoint")
        require(steer is None or pulses[1] == steer, "Steering did not remain at neutral")
        return pulses

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=.5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=.5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=.5)
        finally:
            self.process.stdout.close()


def prompt_with_pulse(client, prompt, pulse, steering, until, *, terminal):
    """Renew one pulse while waiting for the operator to observe the ESC cue."""
    print(prompt, file=sys.stderr, flush=True)
    while time.monotonic() < until:
        before = time.monotonic()
        client.command(f"PULSE {pulse}", "MAINTENANCE", pulse, steering)
        wait = min(until, before + .08) - time.monotonic()
        if select.select([terminal], [], [], max(0, wait))[0]:
            reply = terminal.readline()
            require(reply and reply.strip() == "", "ESC procedure cancelled by operator")
            return
    raise ValueError("ESC cue deadline elapsed")


def program(client, neutral, forward, reverse, *, terminal):
    _, steering = client.command("HOLD", "HOLD", neutral)
    # The Pico independently enforces two complete staged neutral PWM frames.
    time.sleep(.065)
    client.command("ENTER", "MAINTENANCE", neutral, steering)
    exited = False
    try:
        prompt_with_pulse(client,
            "With the ESC off, follow its manual to enter EZ-Set programming. At one red blink press Enter.",
            neutral, steering, time.monotonic() + 65, terminal=terminal)
        time.sleep(.065)
        # Forward and reverse share one continuous nonneutral budget.
        deadline = time.monotonic() + 12
        prompt_with_pulse(client, "Forward is commanded. At two red blinks press Enter.",
                          forward, steering, deadline, terminal=terminal)
        prompt_with_pulse(client, "Reverse/brake is commanded. At the documented success indication press Enter.",
                          reverse, steering, deadline, terminal=terminal)
        client.command(f"PULSE {neutral}", "MAINTENANCE", neutral, steering)
        client.command("EXIT", "HOLD", neutral, steering)
        exited = True
    finally:
        if not exited:
            try:
                client.command("ABORT", "HOLD", neutral, steering)
            except (OSError, ValueError):
                # Closing the link and the independent MCU lease also latch Hold.
                pass


def calibrate(site_path=None, definitions=None, *, device_id, profile_id, build_id,
              maintenance_client, esc, neutral_us, forward_us, reverse_us):
    from robot_runtime.maintenance import stopped
    from . import maintenance, services
    from .commands import graph_for
    from .records import locked, write_json

    require(re.fullmatch(r"[0-9A-F]{16}", device_id), "An exact Pico serial is required")
    require(all(re.fullmatch(r"[A-Za-z0-9_-]{1,24}", value) for value in (profile_id, build_id)),
            "Exact manifest profile and build IDs are required")
    require(esc in RECIPES, "Unsupported ESC recipe")
    require(400 <= reverse_us < neutral_us < forward_us <= 2600, "Invalid calibration endpoints")
    require(sys.stdin.isatty(), "Calibration requires an interactive terminal")
    require(maintenance_client.is_absolute() and maintenance_client.is_file() and os.access(maintenance_client, os.X_OK),
            "Select an absolute path to the installed rc_car_maintenance_link executable")
    site = graph_for(site_path, definitions)["site"]
    storage = site["storage"]
    state = Path(storage["data_root"]) / "runtime"
    root = Path(storage["installation_root"])
    with locked(root):
        require(not services.active(site), "Stop runtime management and all owned vehicle workloads first")
        maintenance.audited_stopped(site, management_active=False)
        with stopped(state):
            print(f"Selected ESC instructions: {RECIPES[esc]}", file=sys.stderr, flush=True)
            require(confirm("Follow the model manual to isolate propulsion. Type ISOLATED to continue: ") == "ISOLATED",
                    "Propulsion isolation was not confirmed")
            link = MaintenanceClient(maintenance_client, device_id, profile_id, build_id)
            try:
                link.ready(device_id, profile_id)
                program(link, neutral_us, forward_us, reverse_us, terminal=sys.stdin)
            finally:
                link.close()
            require(confirm("Confirm the ESC accepted the endpoints while propulsion remains isolated [y/N]: ").lower() == "y",
                    "ESC acceptance was not confirmed. Pico remains in Hold.")
            folder = Path(storage["data_root"]) / "deployment/calibrations"
            folder.mkdir(parents=True, exist_ok=True, mode=0o700)
            record = folder / (str(time.time_ns()) + ".json")
            result = dict(schema_version=1, esc=esc, device_id=device_id, profile_id=profile_id,
                          build_id=build_id, neutral_us=neutral_us, forward_us=forward_us, reverse_us=reverse_us,
                          operator_observed_esc_acceptance=True, pico_mode="HOLD", completed_at=time.time())
            write_json(record, result)
            return dict(result, record=str(record))


def confirm(prompt):
    print(prompt, end="", file=sys.stderr, flush=True)
    return input()
