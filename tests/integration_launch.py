"""Inspect real ROS launch descriptions without starting a container or camera."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from launch import LaunchContext
from launch.utilities import perform_substitutions
from launch_ros.actions import ComposableNodeContainer
from rclpy.expand_topic_name import expand_topic_name

from robot_deployment.configuration import Inputs, definition_root, encoded, load
from robot_deployment.launch import main
from robot_deployment.preparation import effective


class LaunchTests(unittest.TestCase):
    def test_all_modes_resolve_capture_detections_in_selected_namespace(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            root = definition_root()
            site = Inputs().read(root / "config/site.example.yaml")
            site["storage"] = dict(installation_root=str(work / "installation"), data_root=str(work / "data"))
            site["workspaces"] = dict(student=str(work / "student"))
            site["ros"]["namespace"] = "capture_rename"
            (work / "student/config").mkdir(parents=True)
            path = work / "site.yaml"
            path.write_bytes(encoded(site))
            graph = load(path, root)
            context = LaunchContext()
            text = lambda value: perform_substitutions(context, value)
            for camera in ("oak", "d455"):
                for model in ("camera", "cones", "coco", "both"):
                    mode = camera + "-" + model
                    with self.subTest(mode=mode):
                        snapshot = effective(graph, work / "release", mode, check_artifacts=False)
                        manifest = dict(unit_id="perception", mode=mode)
                        with patch("robot_runtime.prepared.run_inputs", return_value=(manifest, {"effective": encoded(snapshot)})), \
                                patch("launch.LaunchService") as service, \
                                patch("launch_ros.actions.ComposableNodeContainer", wraps=ComposableNodeContainer) as container, \
                                contextlib.redirect_stdout(io.StringIO()):
                            service.return_value.run.return_value = 0
                            self.assertEqual(main(), 0)
                        service.return_value.include_launch_description.assert_called_once()
                        nodes = {text(node.node_name): node for node in container.call_args.kwargs["composable_node_descriptions"]}
                        models = ("cones", "coco") if model == "both" else () if model == "camera" else (model,)
                        expected = {"camera", *("detector_" + name for name in models)}
                        if model == "both":
                            expected.add("combined_overlay")
                        self.assertEqual(set(nodes), expected)
                        for name, node in nodes.items():
                            namespace = "/" + text(node.node_namespace)
                            self.assertEqual(namespace, "/capture_rename")
                            remaps = {text(source): text(target) for source, target in node.remappings or []}
                            if name.startswith("detector_"):
                                self.assertEqual(remaps, {"frames": "camera/frames"})
                                self.assertEqual(expand_topic_name("~/capture_detections", name, namespace),
                                                 f"/capture_rename/{name}/capture_detections")
                            elif name == "combined_overlay":
                                self.assertEqual(remaps, dict(frames="camera/frames",
                                    first_capture_detections="detector_cones/capture_detections",
                                    second_capture_detections="detector_coco/capture_detections"))
                                for input_name, model_name in (("first_capture_detections", "cones"),
                                                              ("second_capture_detections", "coco")):
                                    self.assertEqual(expand_topic_name(remaps[input_name], name, namespace),
                                        expand_topic_name("~/capture_detections", "detector_" + model_name, namespace))


if __name__ == "__main__":
    unittest.main()
