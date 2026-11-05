"""Workspace builds preserve sources and require a clean output after underlay changes."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from robot_deployment.build import clean_outputs, ros
from robot_deployment.configuration import ConfigurationError


class BuildTests(unittest.TestCase):
    def test_clean_refuses_symlink_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "student-src"
            outside.mkdir()
            original = outside / "algorithm.py"
            original.write_text("keep")
            output = root / "outputs"
            output.mkdir()
            (output / "build").symlink_to(outside)
            with self.assertRaisesRegex(ConfigurationError, "Unsafe"):
                clean_outputs(output)
            self.assertEqual(original.read_text(), "keep")

    def test_student_underlay_change_requires_explicit_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            student = root / "student"
            (student / "src").mkdir(parents=True)
            original = student / "src/algorithm.py"
            original.write_text("keep")
            installation = root / "installation"
            for release in ("first", "second"):
                setup = installation / "releases" / release / "ros/install/setup.bash"
                setup.parent.mkdir(parents=True)
                setup.write_text("# fixture")
            graph = dict(site=dict(storage=dict(installation_root=str(installation)), workspaces=dict(student=str(student))))
            with patch("robot_deployment.build.graph_for", return_value=graph), \
                    patch("robot_deployment.build.current", return_value="first") as selected, \
                    patch("robot_deployment.build.subprocess.run") as command:
                result = ros(workspace="student")
                self.assertFalse(result["runtime_restarted"])
                self.assertEqual(command.call_count, 1)
                output = student / ".robot-deployment"
                (output / "build").mkdir()
                (output / "build/generated").write_text("old output")
                selected.return_value = "second"
                with self.assertRaisesRegex(ConfigurationError, "underlay changed"):
                    ros(workspace="student")
                self.assertEqual(command.call_count, 1)
                ros(workspace="student", clean=True)
                self.assertEqual(command.call_count, 2)
                self.assertFalse((output / "build").exists())
                self.assertEqual(original.read_text(), "keep")
