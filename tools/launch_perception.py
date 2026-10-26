#!/usr/bin/env python3
"""Explicit single-camera/single-model composition; no installer behavior."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import argparse
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    cameras = json.loads((root / "config/cameras.json").read_text())
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--camera", choices=cameras["profiles"], required=True)
    parser.add_argument("--model", choices=("cones", "coco"), required=True)
    args = parser.parse_args()
    site = json.loads(args.site.read_text())
    camera = {**cameras["defaults"], **cameras["profiles"][args.camera]}
    camera.pop("width"); camera.pop("height")  # Geometry is verified by the camera provider.
    camera["device_id"] = site["device_ids"][camera["backend"]]
    model = site["models"][args.model]
    for name in ("engine", "profile"):
        if not Path(model[name]).is_file(): parser.error(f"Missing model {name}: {model[name]}")
    from launch import LaunchDescription, LaunchService
    from launch_ros.actions import ComposableNodeContainer
    from launch_ros.descriptions import ComposableNode
    namespace = site["ros_namespace"]
    common = dict(namespace=namespace, extra_arguments=[{"use_intra_process_comms": True}])
    container = ComposableNodeContainer(name="perception_container", namespace=namespace,
        package="rclcpp_components", executable="component_container_mt", output="screen",
        # Validate/load inference before opening the sole camera session.
        composable_node_descriptions=[
            ComposableNode(package="rgbd_object_detector", plugin="rgbd_object_detector::DetectorNode", name="detector",
                parameters=[dict(engine_path=model["engine"], model_profile=model["profile"],
                    publish_overlay=True, overlay_spatial=True,
                    overlay_capture_marker=site.get("measurement_marker", False))],
                remappings=[("frames", "camera/frames")], **common),
            ComposableNode(package="rgbd_camera", plugin="rgbd_camera::CameraNode", name="camera", parameters=[camera], **common),
        ])
    service = LaunchService()
    service.include_launch_description(LaunchDescription([container]))
    return service.run()


if __name__ == "__main__":
    raise SystemExit(main())
