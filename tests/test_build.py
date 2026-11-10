"""Workspace builds preserve sources and require a clean output after underlay changes."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from robot_deployment.build import clean_outputs, ros
from robot_deployment.components import ros_build
from robot_deployment.configuration import ConfigurationError


class BuildTests(unittest.TestCase):
    def test_system_rebuild_includes_native_recorder_from_verified_runtime(self):
        for vehicle in (False, True):
            with self.subTest(vehicle=vehicle), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                installation = root / "installation"
                release = installation / "releases/fixture"
                setup = release / "ros/install/setup.bash"
                setup.parent.mkdir(parents=True)
                setup.write_text("# fixture")
                names = ("rgbd_camera", "rgbd_object_detector", "vision_msgs", "robot_runtime")
                if vehicle:
                    names += ("rc_car_interface",)
                selections = {name: dict(commit=name + "-revision") for name in names}
                for name, selection in selections.items():
                    checkout = installation / "cache/git" / (name + "-" + selection["commit"])
                    checkout.mkdir(parents=True)
                    if name == "robot_runtime":
                        (checkout / "ros/robot_runtime_recording").mkdir(parents=True)
                units = dict(vehicle=dict(source=selections["rc_car_interface"])) if vehicle else {}
                graph = dict(site=dict(storage=dict(installation_root=str(installation), data_root=str(root / "data"))),
                             composition=dict(units=units),
                             sources=dict(components={name: selections[name] for name in ("rgbd_camera", "rgbd_object_detector", "robot_runtime")},
                                          dependencies=dict(vision_msgs=selections["vision_msgs"])))
                with patch("robot_deployment.build.graph_for", return_value=graph), \
                        patch("robot_deployment.build.current", return_value="fixture"), \
                        patch("robot_deployment.build.verify_source") as verify, \
                        patch("robot_deployment.build.subprocess.run") as command:
                    result = ros(workspace="system")
                self.assertEqual(verify.call_count, len(names))
                source = root / "data/build/system/fixture/src"
                self.assertEqual({p.name for p in source.iterdir()},
                                 (set(names) - {"robot_runtime"}) | {"robot_runtime_recording"})
                self.assertEqual((source / "robot_runtime_recording").resolve(),
                                 installation / "cache/git/robot_runtime-robot_runtime-revision/ros/robot_runtime_recording")
                if vehicle:
                    self.assertEqual((source / "rc_car_interface").resolve(),
                                     installation / "cache/git/rc_car_interface-rc_car_interface-revision")
                self.assertIn("-DNLOHMANN_JSON_INCLUDE_DIR=" + str(release / "sdk/depthai/include"), command.call_args.args[0])
                self.assertFalse(result["runtime_restarted"])

    def test_installer_build_keeps_recorder_with_optional_vehicle(self):
        for vehicle in (False, True):
            with self.subTest(vehicle=vehicle), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                names = ("rgbd_camera", "rgbd_object_detector", "vision_msgs", "robot_runtime")
                if vehicle:
                    names += ("rc_car_interface",)
                selected = {name: root / "sources" / name for name in names}
                for path in selected.values():
                    path.mkdir(parents=True)
                recorder = selected["robot_runtime"] / "ros/robot_runtime_recording"
                recorder.mkdir(parents=True)
                release = root / "release"
                command = Mock()
                ros_build(selected, release, command)
                source = release / "ros/src"
                self.assertEqual({p.name for p in source.iterdir()},
                                 (set(names) - {"robot_runtime"}) | {"robot_runtime_recording"})
                self.assertEqual((source / "robot_runtime_recording").resolve(), recorder)
                if vehicle:
                    self.assertEqual((source / "rc_car_interface").resolve(), selected["rc_car_interface"])
                command.assert_called_once()
                self.assertEqual(command.call_args.kwargs["cwd"], release / "ros")
                self.assertIn("-DNLOHMANN_JSON_INCLUDE_DIR=" + str(release / "sdk/depthai/include"), command.call_args.args[0])

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
