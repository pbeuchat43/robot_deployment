#!/usr/bin/env python3
"""One shared camera with one or both detector components; no installer behavior."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import json
import os


def main():
    from robot_runtime.prepared import run_inputs
    from .configuration import require
    manifest, inputs = run_inputs()
    snapshot = json.loads(inputs["effective"])
    require(snapshot["schema_version"] == 1 and manifest["unit_id"] == "perception", "Invalid perception snapshot")
    camera = snapshot["nodes"]["camera"]
    selected = snapshot["selected_models"]
    # No mutable site, composition or student file is read here.
    from launch import LaunchDescription, LaunchService
    from launch_ros.actions import ComposableNodeContainer, Node
    from launch_ros.descriptions import ComposableNode
    namespace = snapshot["namespace"]
    common = dict(namespace=namespace, extra_arguments=[{"use_intra_process_comms": True}])
    detectors = []
    for selected_model in selected:
        detectors.append(ComposableNode(package="rgbd_object_detector", plugin="rgbd_object_detector::DetectorNode",
            name="detector_" + selected_model,
            parameters=[snapshot["nodes"]["detector_" + selected_model]],
            remappings=[("frames", "camera/frames")], **common))
    if len(selected) == 2:
        detectors.append(ComposableNode(package="rgbd_object_detector", plugin="rgbd_object_detector::CombinedOverlayNode",
            name="combined_overlay", parameters=[snapshot["nodes"]["combined_overlay"]],
            remappings=[("frames", "camera/frames"), ("first_capture_detections", "detector_cones/capture_detections"),
                ("second_capture_detections", "detector_coco/capture_detections")], **common))
    container = ComposableNodeContainer(name="perception_container", namespace=namespace,
        package="rclcpp_components", executable="component_container_mt", output="screen",
        # Validate/load inference before opening the sole camera session.
        composable_node_descriptions=[*detectors,
            ComposableNode(package="rgbd_camera", plugin="rgbd_camera::CameraNode", name="camera", parameters=[camera], **common),
        ])
    mount = snapshot["mount"]
    transforms = []
    for name, parent, child, xyz, rpy in (
        ("camera_mount", mount["parent_frame"], mount["child_frame"], mount["translation_m"], mount["rotation_rpy_rad"]),
        ("camera_optical", mount["child_frame"], mount["optical_frame"], [0., 0., 0.], mount["optical_rotation_rpy_rad"])):
        arguments = ["--frame-id", parent, "--child-frame-id", child]
        for flag, value in zip(("--x", "--y", "--z", "--roll", "--pitch", "--yaw"), [*xyz, *rpy]):
            arguments.extend((flag, str(value)))
        transforms.append(Node(package="tf2_ros", executable="static_transform_publisher", name=name,
            namespace=namespace, arguments=arguments, output="screen"))
    print(json.dumps(dict(event="prepared_launch", run_id=os.environ.get("ROBOT_RUNTIME_RUN"),
        mode=manifest["mode"], source_hashes=snapshot["provenance"]["sources"])), flush=True)
    service = LaunchService()
    service.include_launch_description(LaunchDescription([*transforms, container]))
    return service.run()


if __name__ == "__main__":
    raise SystemExit(main())
