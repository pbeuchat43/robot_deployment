"""Every public command family shares the operator output contract."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from robot_deployment import cli, pico
from robot_deployment.components import Commands
from robot_deployment.output import output_mode, progress
from robot_runtime.common import Fault


class OutputTests(unittest.TestCase):
    def invoke(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err), patch("robot_deployment.commands.resolve_site", return_value=None):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_every_deployment_family_renders_nested_results(self):
        routes = [
            (["install"], "commands.install"), (["upgrade"], "commands.install"),
            (["rollback"], "commands.rollback"), (["doctor"], "commands.doctor"),
            (["config", "validate"], "commands.config"), (["config", "show"], "commands.config"),
            (["config", "render", "--release", "/release", "--output", "/profile"], "commands.config"),
            (["host", "plan", "--output", "/plan"], "commands.host"),
            (["host", "setup", "--output", "/setup"], "commands.host"),
            (["host", "repositories", "--output", "/repositories"], "commands.host"),
            (["info", "host"], "commands.info"), (["info", "installation"], "commands.info"),
            (["info", "mcu", "rc-car"], "commands.info"),
            (["build", "ros", "student"], "build.ros"), (["build", "mcu", "bno08x"], "firmware.build"),
            (["flash", "mcu", "bno08x", "--device-id", "id", "--manifest", "/manifest"], "firmware.flash"),
            (["flash", "mcu", "rc-car", "--device-id", "id", "--manifest", "/manifest"], "firmware.flash_rc_car"),
            (["pico", "list"], "pico.listing"), (["pico", "rc-car", "status"], "pico.operate"),
            (["pico", "rc-car", "doctor"], "pico.operate"),
            (["calibrate", "traxxas", "esc", "--device-id", "id", "--profile-id", "profile", "--build-id", "build",
              "--maintenance-client", "/client", "--esc", "xl-5"], "calibration.calibrate"),
            (["shell", "install"], "commands.shell"), (["shell", "remove"], "commands.shell"),
        ]
        payload = dict(completed=True, details=dict(result="unchanged", pending=False),
                       devices=[dict(usb_port="1-2", state="BOOTSEL", usb_accessible=False)])
        for argv, target in routes:
            for flag in ([], ["--json"]):
                with self.subTest(argv=argv, flag=flag), patch("robot_deployment." + target, return_value=payload) as called:
                    code, out, err = self.invoke([*argv, *flag])
                self.assertEqual(code, 0)
                called.assert_called_once()
                self.assertEqual(err, "")
                if flag:
                    self.assertEqual(json.loads(out), payload)
                else:
                    self.assertIn("Completed: yes", out)
                    self.assertIn("Pending: no", out)
                    self.assertIn("BOOTSEL", out)
                    self.assertNotIn('{', out)

    def test_runtime_format_is_explicit_in_dispatch_and_replay(self):
        payload = dict(fresh=False, units=[dict(unit_id="camera", lifecycle="stopped", readiness="unavailable",
                                              ownership="none", fresh=False, blocked=False)])
        for flag in ([], ["--json"]):
            with patch("robot_runtime.cli.request", return_value=payload):
                code, out, _ = self.invoke([*flag, "runtime", "--state", "/state", "status"])
            self.assertEqual(code, 0)
            if flag:
                self.assertEqual(json.loads(out), payload)
            else:
                self.assertIn("Unit id", out)
                self.assertIn("Ownership", out)
                self.assertNotIn('{', out)
        _, out, _ = self.invoke(["runtime", "--state", "/state", "status", "--show-call", "--json"])
        explanation = json.loads(out)
        self.assertEqual(explanation["arguments"]["argv"], ["--json", "--state", "/state", "status"])
        self.assertEqual(explanation["argv"][3:], explanation["arguments"]["argv"])
        with patch("robot_runtime.cli.main", return_value=0) as runtime:
            self.invoke(["runtime", "--state", "/state", "status"])
        self.assertEqual(runtime.call_args.kwargs["argv"][0], "--human")

    def test_installation_summarizes_inventory_without_changing_json(self):
        result = dict(selected="release", installation=dict(result="succeeded", release="/release",
            identity=dict(platform="fixture", deployment=dict(deployment_commit="commit", runtime_commit="runtime")),
            stages=[dict(name="python", result="succeeded", artifacts={"private/file": dict(sha256="digest")})]))
        with patch("robot_deployment.commands.info", return_value=result):
            _, human, _ = self.invoke(["info", "installation"])
            _, structured, _ = self.invoke(["info", "installation", "--json"])
        self.assertIn("Recorded result: succeeded", human)
        self.assertIn("Deployment commit: commit", human)
        self.assertIn("Artifacts", human)
        self.assertNotIn("private/file", human)
        self.assertNotIn("digest", human)
        self.assertEqual(json.loads(structured), result)

    def test_json_at_root_family_and_leaf_survives_nested_parsing(self):
        for argv in (["--json", "runtime", "ros", "status"], ["runtime", "--json", "ros", "status"],
                     ["runtime", "ros", "--json", "status"], ["runtime", "ros", "status", "--json"]):
            with self.subTest(argv=argv), patch("robot_runtime.cli.request", return_value=dict(topics=[])):
                self.assertEqual(json.loads(self.invoke(argv)[1]), dict(topics=[]))

    def test_errors_exit_codes_and_stdout_are_preserved(self):
        for error, expected_code in ((ValueError("invalid selection"), 2),
                (Fault("blocked", "owned", units=["worker"]), 2),
                (subprocess.CalledProcessError(7, ["builder"]), 7),
                (subprocess.CalledProcessError(-15, ["builder"]), 143), (KeyboardInterrupt(), 130)):
            for flag in ([], ["--json"]):
                with self.subTest(error=error, flag=flag), patch("robot_deployment.commands.config", side_effect=error):
                    code, out, err = self.invoke(["config", "validate", *flag])
                self.assertEqual(code, expected_code)
                self.assertEqual(out, "")
                if isinstance(error, KeyboardInterrupt):
                    self.assertEqual(err, "")
                elif flag:
                    expected = error.as_dict() if isinstance(error, Fault) else dict(code="deployment_error", message=str(error))
                    self.assertEqual(json.loads(err), dict(error=expected))
                else:
                    self.assertIn("Error [", err)
                    self.assertNotIn('{', err)
        for flag in ([], ["--json"]):
            err = io.StringIO()
            with patch("robot_runtime.cli.request", side_effect=Fault("transport_unknown", "offline")), \
                 redirect_stderr(err), self.assertRaises(SystemExit) as exited:
                cli.main(["runtime", "--state", "/state", "status", *flag])
            self.assertEqual(exited.exception.code, 1)
            self.assertIn("transport_unknown", err.getvalue())

    def test_parser_errors_are_machine_readable_when_requested(self):
        for argv in (["--json", "build", "ros"], ["build", "ros", "--json"], ["runtime", "ros", "unknown", "--json"]):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err), self.assertRaises(SystemExit) as exited:
                cli.main(argv)
            self.assertEqual(exited.exception.code, 2)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(json.loads(err.getvalue())["error"]["code"], "invalid_arguments")

    def test_progress_uses_stderr_and_does_not_pollute_json_results(self):
        def install(**_):
            progress(dict(event="stage", stage="sdk-camera"))
            return dict(installed=True)
        for flag in ([], ["--json"]):
            with patch("robot_deployment.commands.install", side_effect=install):
                code, out, err = self.invoke(["install", *flag])
            self.assertEqual(code, 0)
            if flag:
                self.assertEqual(json.loads(out), dict(installed=True))
                self.assertEqual(json.loads(err), dict(event="stage", stage="sdk-camera"))
            else:
                self.assertEqual(out, "Installed: yes\n")
                self.assertIn("Stage: sdk-camera", err)
                self.assertNotIn('{', err)

    def test_calibration_confirmation_still_reads_input_and_keeps_stdout_clean(self):
        from robot_deployment.calibration import confirm
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err), patch("builtins.input", return_value="ISOLATED") as read:
            self.assertEqual(confirm("Type ISOLATED: "), "ISOLATED")
        read.assert_called_once_with()
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "Type ISOLATED: ")

    def test_real_child_output_does_not_mix_with_results(self):
        # Runs only on Jah: exercise actual descriptor routing, not just mocks.
        from robot_deployment.artifacts import run
        with tempfile.TemporaryFile(mode="w+") as err, redirect_stderr(err), redirect_stdout(io.StringIO()) as out:
            run([sys.executable, "-c", "print('tool diagnostic')"])
            self.assertEqual(out.getvalue(), "")
            err.seek(0)
            self.assertEqual(err.read(), "tool diagnostic\n")
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryFile(mode="w+") as err, \
             redirect_stderr(err), redirect_stdout(io.StringIO()) as out, output_mode(structured=False):
            command = Commands(Path(directory))
            command([sys.executable, "-c", "print('stored tool output')"])
            self.assertEqual(out.getvalue(), "")
            self.assertIn("stored tool output", next(command.directory.glob("*.log")).read_text())
            err.seek(0)
            self.assertIn("Event: build_command", err.read())

    def test_pico_watch_and_uncertain_mode_keep_format_and_returncode(self):
        sample = dict(tick_ms=12, mode="HOLD", reason="HOST", rc_quality="GOOD", rc_drive_us=1500,
            rc_steer_us=1500, drive_pwm_us=1500, steer_pwm_us=1500, pan_pwm_us=1500,
            drive_source="HOLD", steer_source="RC")
        for structured in (False, True):
            child = MagicMock()
            child.__enter__.return_value = child
            child.stdout = iter([json.dumps(sample) + "\n"])
            child.wait.return_value = 3
            child.poll.return_value = 3
            out = io.StringIO()
            with patch.object(pico.subprocess, "Popen", return_value=child), redirect_stdout(out):
                code = pico._show_watch(["/client", "watch"], structured=structured)
            self.assertEqual(code, 3)
            if structured:
                self.assertEqual(json.loads(out.getvalue()), sample)
            else:
                self.assertIn("PWM 1500/1500/1500", out.getvalue())
            reply = dict(accepted=False, confirmed=False, result="UNCERTAIN")
            with patch.object(pico, "resolve", return_value=(None, Path("/client"), "device", "profile", "build")), \
                 patch.object(pico, "read_client", return_value=(reply, 3)), redirect_stdout(io.StringIO()) as out:
                self.assertEqual(pico.operate(action="hold", structured=structured), 3)
            if structured:
                self.assertEqual(json.loads(out.getvalue()), reply)
            else:
                self.assertIn("Confirmed: no", out.getvalue())
