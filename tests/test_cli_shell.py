"""No-side-effect routing and owned Bash integration contracts."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from robot_deployment.cli import build_parser, main, complete
from robot_deployment.configuration import ConfigurationError, Inputs, definition_root
from robot_deployment.firmware import flash_call, selected
from robot_deployment.shell import COMMAND, ALIAS, install, remove, paths


class CliTests(unittest.TestCase):
    def test_shared_runtime_aliases_and_restart(self):
        parser = build_parser()
        for name in ("log", "logs"):
            args = parser.parse_args(["runtime", name, "perception", "--follow"])
            self.assertTrue(args.follow)
            self.assertEqual(args.target, "perception")
        args = parser.parse_args(["runtime", "restart", "perception", "--mode", "oak-both"])
        self.assertIsNone(args.expected_run)
        self.assertEqual(args.mode, "oak-both")

    def test_every_route_can_explain_without_dispatch(self):
        routes = [
            ["install"], ["upgrade"], ["rollback"], ["doctor"],
            ["config", "validate"], ["config", "show"], ["config", "render", "--release", "/abs/release", "--output", "/abs/profile"],
            ["host", "plan", "--output", "/abs/plan"], ["host", "setup", "--output", "/abs/setup"], ["host", "repositories", "--output", "/abs/repos"],
            ["info", "host"], ["info", "installation"], ["info", "mcu", "traxxas"],
            ["build", "ros", "student"], ["build", "ros", "system", "--clean"], ["build", "mcu", "bno08x"],
            ["flash", "mcu", "bno08x", "--manifest", "/abs/manifest", "--device-id", "0123456789ABCDEF"],
            ["runtime", "--state", "/abs/state", "start", "perception"],
            ["shell", "install", "--alias"], ["shell", "remove"],
        ]
        with patch("subprocess.run", side_effect=AssertionError("Must not execute")), patch("robot_runtime.ipc.request", side_effect=AssertionError("Must not contact manager")):
            for argv in routes:
                output = io.StringIO()
                with self.subTest(argv=argv), redirect_stdout(output):
                    self.assertEqual(main([*argv, "--show-call", "--json"]), 0)
                result = json.loads(output.getvalue())
                self.assertFalse(result["executed"])
                self.assertIn(":", result["entry_point"])
                self.assertEqual(result["interpreter"], sys.executable)
                self.assertEqual(result["argv"][0], sys.executable)
                self.assertNotIn("--show-call", result["argv"])

    def test_readable_and_json_output_share_dispatch(self):
        result = dict(valid=True, composition="fixture")
        with patch("robot_deployment.commands.config", return_value=result) as dispatch:
            readable, structured = io.StringIO(), io.StringIO()
            with redirect_stdout(readable):
                self.assertEqual(main(["config", "validate"]), 0)
            with redirect_stdout(structured):
                self.assertEqual(main(["config", "validate", "--json"]), 0)
            self.assertIn("Valid: yes", readable.getvalue())
            self.assertEqual(json.loads(structured.getvalue()), result)
            self.assertEqual(dispatch.call_args_list[0], dispatch.call_args_list[1])

    def test_explanation_resolves_local_context_without_dispatch(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}, clear=False):
            context = Path(directory) / "robot_deployment/context.json"
            context.parent.mkdir()
            context.write_text(json.dumps(dict(schema_version=1, site="/private/site.yaml")))
            output = io.StringIO()
            with patch("robot_deployment.commands.doctor", side_effect=AssertionError("Must not execute")), redirect_stdout(output):
                self.assertEqual(main(["doctor", "--show-call", "--json"]), 0)
            value = json.loads(output.getvalue())
            self.assertEqual(value["arguments"]["site_path"], "/private/site.yaml")
            self.assertEqual(value["argv"][-2:], ["--site", "/private/site.yaml"])

    def test_help_and_completion_need_no_runtime(self):
        with patch("subprocess.run", side_effect=AssertionError("Must not execute")), tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}, clear=False):
            for argv in (["--help"], ["runtime", "--help"], ["build", "ros", "--help"]):
                with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as error:
                    main(argv)
                self.assertEqual(error.exception.code, 0)
            self.assertIn("runtime", complete(["run"]))
            self.assertIn("restart", complete(["runtime", "re"]))
            self.assertIn("student", complete(["build", "ros", "st"]))
            self.assertIn("--json", complete(["doctor", "--j"]))
            output = io.StringIO()
            with redirect_stdout(output), self.assertRaises(SystemExit):
                main(["install", "--help"])
            for text in ("Example:", "partial stage", "--json", "exits 0", "stopped"):
                self.assertIn(text, output.getvalue())
            empty = io.StringIO()
            with redirect_stdout(empty):
                self.assertEqual(main(["_complete", "--", "install", "--site", "/nonexistent-prefix"]), 0)
            self.assertEqual(empty.getvalue(), "")  # A blank candidate blocks Bash filename fallback.

    def test_firmware_is_unselected_and_preserves_owner_arguments(self):
        with self.assertRaisesRegex(ConfigurationError, "does not select"):
            selected(dict(composition={}), "traxxas")
        tools = dict(recipes={"traxxas": dict(source="/component/traxxas"), "bno08x": dict(source="/component/bno08x")},
                     pico_sdk=dict(path="/tools/sdk", commit="a" * 40), picotool=dict(path="/tools/picotool"))
        for target in ("traxxas", "bno08x"):
            argv, env = flash_call(target, tools, "/python", "/bundle/manifest", "0123456789ABCDEF", "/new/report" if target == "bno08x" else None)
            self.assertNotIn("--yes", argv)
            self.assertNotIn("--force", argv)
            self.assertIn("--device-id", argv)
            if target == "bno08x":
                self.assertIn("--expected-pico-sdk-commit", argv)
                self.assertEqual(env["BNO08X_PICOTOOL_DIR"], "/tools/picotool")
            else:
                self.assertIn("--picotool-dir", argv)


class ShellTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="robot shell ")
        self.home = Path(self.temp.name)
        self.site = Inputs().read(definition_root() / "config/site.example.yaml")
        self.site["storage"]["installation_root"] = str(self.home / "installation")
        (self.home / ".bashrc").write_text("# existing customizations\nexport EXISTING=retained\n")

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def empty(_name, _home):
        return dict(kind="", value="")

    def test_alias_rerun_syntax_and_owned_remove(self):
        original = (self.home / ".bashrc").read_text()
        first = install(self.site, alias=True, home=self.home, probe=self.empty)
        self.assertTrue(first["alias"])
        before = {key: path.read_bytes() for key, path in paths(self.home).items() if key != "home"}
        install(self.site, alias=True, home=self.home, probe=self.empty)
        self.assertEqual(before, {key: path.read_bytes() for key, path in paths(self.home).items() if key != "home"})
        subprocess.run(["bash", "-n", str(paths(self.home)["snippet"])], check=True)
        subprocess.run(["bash", "-n", str(paths(self.home)["executable"])], check=True)
        subprocess.run(["bash", "-n", str(self.home / ".bashrc")], check=True)
        remove(self.site, home=self.home)
        self.assertEqual((self.home / ".bashrc").read_text(), original)

    def test_alias_conflict_keeps_full_command(self):
        def probe(name, _home):
            return dict(kind="function", value="") if name == ALIAS else self.empty(name, _home)
        result = install(self.site, alias=True, home=self.home, probe=probe)
        self.assertTrue(result["installed"])
        self.assertFalse(result["alias"])
        self.assertNotIn("alias " + ALIAS + "=", paths(self.home)["snippet"].read_text())
        self.assertTrue(paths(self.home)["executable"].is_file())

    def test_full_command_conflict_and_edited_hook_preserved(self):
        original = (self.home / ".bashrc").read_text()
        result = install(self.site, home=self.home, probe=lambda *_: dict(kind="file", value="/unrelated/" + COMMAND))
        self.assertFalse(result["installed"])
        self.assertEqual((self.home / ".bashrc").read_text(), original)
        install(self.site, home=self.home, probe=self.empty)
        startup = self.home / ".bashrc"
        startup.write_text(startup.read_text().replace("[ ! -r ", "# user edit\n[ ! -r "))
        changed = startup.read_text()
        with self.assertRaisesRegex(ConfigurationError, "edited"):
            remove(self.site, home=self.home)
        self.assertEqual(startup.read_text(), changed)

    def test_interactive_alias_dispatch_and_real_resolution(self):
        current = self.home / "installation/current"
        current.mkdir(parents=True)
        (current / "venv").symlink_to(Path(sys.prefix), target_is_directory=True)
        with patch.dict(os.environ, {"PATH": "/usr/bin:/bin", "HOME": str(self.home)}):
            installed = install(self.site, alias=True, home=self.home)
            self.assertTrue(installed["installed"] and installed["alias"], installed)
            checked = subprocess.run(["bash", "--noprofile", "-ic",
                COMMAND + " --version; " + ALIAS + " --version; complete -p " + COMMAND + " " + ALIAS],
                check=True, capture_output=True, text=True, timeout=10)
            from robot_deployment import __version__
            self.assertEqual([line for line in checked.stdout.splitlines() if line == __version__], [__version__, __version__])
            self.assertEqual(checked.stdout.count("-F _robot_deployment_complete"), 2)
            self.assertTrue(install(self.site, alias=True, home=self.home)["alias"])
            remove(self.site, home=self.home)
            cleared = subprocess.run(["bash", "--noprofile", "-ic", "type -t " + ALIAS],
                                     capture_output=True, text=True, timeout=10)
            self.assertNotEqual(cleared.returncode, 0)
