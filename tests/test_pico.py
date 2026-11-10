"""Pico command, snapshot and flash contracts without physical devices."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
from contextlib import nullcontext, redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from robot_deployment import cli, firmware, pico
from robot_deployment.configuration import Inputs, definition_root, digest, encoded, file_digest, load
from robot_deployment.installation import copy_definitions
from robot_deployment.profile import build_profile
from robot_runtime.profile import validate

DEVICE = "E123456789ABCDEF"
BOARD = "waveshare_rp2040_zero"
HEADER = b"// RC Car profile fixture\n"


class PicoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="pico-command-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_inventory_never_opens_serial(self):
        sysfs = self.root / "sys"
        ports = sysfs / "bus/usb/devices"
        tty = sysfs / "class/tty/ttyACM2"
        tty.mkdir(parents=True)
        for name, pid, product in (("1-2", "0003", "RP2 Boot"), ("1-3", "000a", "RC Car Pico"),
                                   ("1-4", "ffff", "Other device")):
            target = ports / name
            target.mkdir(parents=True)
            for key, value in dict(idVendor="2e8a", idProduct=pid, busnum="1", devnum=name[-1],
                                   product=product, serial=DEVICE).items():
                (target / key).write_text(value + "\n")
        interface = ports / "1-3/1-3:1.0"
        interface.mkdir()
        (tty / "device").symlink_to(interface)
        result = pico.inventory(sysfs, self.root / "dev")
        self.assertEqual([(x["usb_port"], x["state"], x["chip"]) for x in result],
                         [("1-2", "BOOTSEL", "RP2040"), ("1-3", "application", "RP2040")])
        self.assertEqual(pico.application(result, DEVICE)[0]["tty"], str(self.root / "dev/ttyACM2"))

    def test_cli_routes_are_explainable_without_executing(self):
        routes = [
            (["pico", "list"], "pico:listing"), (["pico", "rc-car", "status"], "pico:operate"),
            (["pico", "rc-car", "watch", "--duration", "2"], "pico:operate"),
            (["pico", "rc-car", "mode", "manual"], "pico:operate"),
            (["pico", "rc-car", "mode", "hold"], "pico:operate"),
            (["pico", "rc-car", "doctor"], "pico:operate"), (["info", "mcu", "rc-car"], "commands:info"),
            (["build", "mcu", "rc-car"], "firmware:build"),
            (["flash", "mcu", "rc-car", "--device-id", DEVICE, "--manifest", "/abs/manifest",
              "--actuators-isolated"], "firmware:flash_rc_car"),
        ]
        for args, route in routes:
            out = io.StringIO()
            with self.subTest(args=args), patch("subprocess.run", side_effect=AssertionError), redirect_stdout(out):
                self.assertEqual(cli.main([*args, "--show-call", "--json"]), 0)
                self.assertTrue(json.loads(out.getvalue())["entry_point"].endswith(route))

    def test_uncertain_mode_is_not_success(self):
        output = io.StringIO()
        reply = dict(accepted=False, confirmed=False, result="UNCERTAIN")
        with patch.object(pico, "resolve", return_value=(None, self.root / "client", DEVICE, "profile", "build")), \
             patch.object(pico, "read_client", return_value=(reply, 3)) as call, redirect_stdout(output):
            self.assertEqual(pico.operate(action="manual", structured=True), 3)
            self.assertEqual(json.loads(output.getvalue()), reply)
            call.assert_called_once_with(self.root / "client", "manual", DEVICE, "profile", "build")

    def test_optional_vehicle_profile_and_header_snapshot(self):
        import shutil
        source = definition_root()
        root = self.root / "definitions"
        for name in ("compositions", "config", "parameters", "platforms", "robot_models", "tools"):
            shutil.copytree(source / name, root / name)
        shutil.copyfile(source / "sources.json", root / "sources.json")
        site = Inputs().read(root / "config/site.example.yaml")
        site["storage"] = dict(installation_root=str(self.root / "install"), data_root=str(self.root / "data"))
        site["hardware"]["rc_car"] = dict(device_id=DEVICE, profile_id=digest(HEADER)[:16], build_id="a" * 16)
        site_path = self.root / "site.json"
        site_path.write_bytes(encoded(site))
        path = root / "compositions/rgbd-demo.yaml"
        default = load(site_path, root)
        self.assertEqual([unit["id"] for unit in build_profile(default, site_path, self.root, self.root / "runtime.json")["units"]],
                         ["perception", "video", "recording"])
        composition = Inputs().read(path)
        source_pin = dict(url="https://example.invalid/source.git", commit="a" * 40)
        composition["units"]["vehicle"] = dict(launcher="rc_car_interface", source=source_pin)
        composition["firmware"] = dict(rc_car=dict(source=source_pin, board=BOARD, path=".", profile="vehicle.hpp"))
        path.write_bytes(encoded(composition))
        (root / "vehicle.hpp").write_bytes(HEADER)
        graph = load(site_path, root)
        snapshot = self.root / "snapshot"
        (root / "vehicle.hpp").write_bytes(b"changed after admission")
        copy_definitions(graph, snapshot)
        self.assertEqual((snapshot / "vehicle.hpp").read_bytes(), HEADER)
        validated, _ = validate(build_profile(graph, site_path, self.root, self.root / "runtime.json"), check_paths=False)
        self.assertEqual([unit["id"] for unit in validated["units"]], ["perception", "video", "recording", "vehicle"])
        self.assertEqual(len(validated["units"][0]["launch_modes"]), 8)
        self.assertEqual(validated["recording"]["source_unit_id"], "perception")
        self.assertEqual(validated["units"][2]["requires_running"], ["perception"])
        self.assertEqual(validated["units"][-1]["id"], "vehicle")
        self.assertIn("device_id:=" + DEVICE, validated["units"][-1]["argv"])
        self.assertEqual(validated["ros"]["topics"][-1]["id"], "vehicle_status")
        self.assertEqual(validated["ros"]["services"][-1]["type"], "rc_car_interface/srv/SetRuntimeMode")

    def test_scoped_flash_report_and_mismatched_artifact(self):
        source = dict(commit="a" * 40)
        recipe = dict(source=source, board=BOARD)
        graph = dict(site=dict(storage=dict(data_root=str(self.root)), hardware={}),
            sources=dict(dependencies=dict(pico_sdk=source, picotool=source)),
            firmware_profiles=dict(rc_car=dict(sha256=digest(HEADER))))
        release = self.root / "release"
        ctl, tool = release / pico.HELPER, release / "tool/picotool"
        for path in (ctl, tool):
            path.parent.mkdir(parents=True)
            path.write_bytes(b"fixture")
            path.chmod(0o700)
        path = firmware.output_dir(graph, "rc_car", recipe) / "build" / firmware.RC_MANIFEST
        path.parent.mkdir(parents=True)
        uf2 = path.with_name("rc_car_firmware.uf2")
        uf2.write_bytes(b"firmware")
        expected = firmware.rc_selection(graph, recipe)
        value = dict(board=BOARD, protocol="RCPv1", build_id="a" * 16, profile_id=digest(HEADER)[:16],
                     uf2=uf2.name, sha256=file_digest(uf2))
        path.write_bytes(encoded(value))
        path.with_name(firmware.RC_RECEIPT).write_bytes(encoded(dict(
            selection=expected, manifest_sha256=file_digest(path), uf2_sha256=value["sha256"])))
        target = dict(bus=1, address=9, usb_port="1-2", chip="RP2040")
        commands = []
        def run(argv, **_):
            commands.append(argv[1])
            self.assertEqual(argv[-4:], ["--bus", "1", "--address", "9"])
            if argv[1] == "save":
                argv[4].write_bytes(b"previous flash")
            if argv[1] == "load":
                self.assertEqual(file_digest(argv[3]), value["sha256"])

        with patch.object(firmware, "graph_for", return_value=graph), \
             patch.object(firmware, "installed", return_value=(recipe, {"picotool": {"path": str(tool.parent)}}, release)), \
             patch.object(firmware, "find_boot", return_value=target) as probe, patch.object(firmware, "confirm_boot") as confirm, \
             patch.object(firmware.subprocess, "run", side_effect=run), patch.object(pico, "stopped_site", return_value=nullcontext()), \
             patch.object(firmware, "postflight", return_value={"fresh": True}):
            with self.assertRaisesRegex(ValueError, "actuators-isolated"):
                firmware.flash_rc_car(manifest=path, device_id=DEVICE)
            outcome = firmware.flash_rc_car(manifest=path, device_id=DEVICE, actuators_isolated=True)
            self.assertEqual(commands, ["save", "load", "reboot"])
            self.assertTrue(outcome["flashed_verified"] and outcome["application_verified"])
            self.assertEqual(confirm.call_count, 3)
            uf2.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                firmware.flash_rc_car(manifest=path, device_id=DEVICE, actuators_isolated=True)
            probe.assert_called_once()

    def test_boot_identity_uses_application_id_and_rejects_wrong_chip(self):
        target = dict(bus=1, address=4, chip="RP2040")
        output = ("Program Information\n id: 1111111111111111\n\n"
                  "Device Information\n type: RP2040\n flash id: 0x" + DEVICE + "\n\n")
        with patch.object(firmware.subprocess, "run", return_value=type("Process", (), {"stdout": output})()) as run:
            self.assertEqual(firmware.boot_id("/tool", target), DEVICE)
            self.assertEqual(run.call_args.args[0][-4:], ["--bus", "1", "--address", "4"])
            with self.assertRaisesRegex(ValueError, "expected silicon"):
                firmware.boot_id("/tool", dict(target, chip="RP2350"))

    def test_boot_selection_rejects_ambiguous_identity_and_changed_address(self):
        first = dict(bus=1, address=4, usb_port="1-2", chip="RP2040", state="BOOTSEL")
        second = dict(first, address=5, usb_port="1-3")
        with (patch.object(pico, "inventory", return_value=[first, second]),
              patch.object(firmware, "boot_id", return_value=DEVICE)):
            with self.assertRaisesRegex(ValueError, "exactly one"):
                firmware.find_boot("/tool", "RP2040", DEVICE)
            self.assertEqual(firmware.find_boot("/tool", "RP2040", DEVICE, "1-2"), first)
        with (patch.object(pico, "inventory", return_value=[dict(first, address=6)]),
              patch.object(firmware, "boot_id") as probe):
            with self.assertRaisesRegex(ValueError, "target changed"):
                firmware.confirm_boot("/tool", first, DEVICE)
            probe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
