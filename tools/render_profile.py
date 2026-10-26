#!/usr/bin/env python3
"""Render a runtime profile from explicit local paths and pinned choices."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import argparse
import json
from pathlib import Path


def render(site_path, output, d455="d455-30", oak="oak-30"):
    root = Path(__file__).resolve().parents[1]
    site = json.loads(site_path.read_text())
    if site["schema_version"] != 1:
        raise ValueError("Unsupported local deployment schema")
    work = Path(site["workdir"])
    native = Path(site["native_prefix"])
    wrapper = str(root / "tools/with_ros.sh")
    namespace = "/" + site["ros_namespace"].strip("/")
    environment = dict(PATH="/usr/bin:/bin", RGBD_SETUP=site["ros_setup"],
        ROS_DOMAIN_ID=str(site["ros_domain_id"]), ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST",
        RMW_IMPLEMENTATION="rmw_fastrtps_cpp", ROS_LOG_DIR=str(work / "ros-log"),
        LD_LIBRARY_PATH=":".join(site.get("sdk_library_paths", [])))
    modes = []
    for camera, camera_profile, label in (("d455", d455, "D455"), ("oak", oak, "OAK-D")):
        for model, model_label in (("cones", "Cones"), ("coco", "COCO 80")):
            modes.append(dict(id=camera + "-" + model, label=f"{label} / {model_label} / {camera_profile}",
                selections=dict(camera=camera, model=model),
                argv=["/bin/bash", wrapper, "/usr/bin/python3", str(root / "tools/launch_perception.py"),
                      "--site", str(site_path), "--camera", camera_profile, "--model", model]))
    perception = dict(id="perception", label="RGB-D perception", argv=modes[0]["argv"],
        launch_modes=modes, default_launch_mode=modes[0]["id"],
        launch_selections=[dict(id="camera", label="Camera", choices=[dict(id="d455", label="D455"), dict(id="oak", label="OAK-D")]),
            dict(id="model", label="Model", choices=[dict(id="cones", label="Cones"), dict(id="coco", label="COCO 80")])],
        working_directory=str(work), environment=environment, stop=dict(signal="SIGINT", timeout_seconds=20), public_logs=True)
    video_environment = dict(environment, GST_PLUGIN_PATH=str(native / "gstreamer"),
        GST_REGISTRY=str(work / "gst-registry.bin"), ROBOT_AV_GI_OVERRIDES=str(native / "gi"), PYTHONPATH=str(native / "python"))
    video = dict(id="video", label="Perception video", argv=["/bin/bash", wrapper, site["runtime_python"],
        "-m", "robot_runtime.av.worker", "--profile", str(output), "--state", site["state"], "--capability", "video"],
        working_directory=str(work), environment=video_environment,
        stop=dict(signal="SIGINT", timeout_seconds=15), public_logs=True)
    topics = []
    def status(identity, label, node, interface, fields):
        topics.append(dict(id=identity, label=label, unit_id="perception", node=namespace + "/" + node,
            name=namespace + "/" + node + "/status", type=interface,
            qos=dict(reliability="best_effort", durability="volatile", depth=1),
            max_rate_hz=2, stale_after_seconds=1, max_serialized_bytes=16384, max_json_bytes=8192, fields=fields))
    status("camera", "Acquisition", "camera", "rgbd_camera_interfaces/msg/Status",
        ["state", "detail", "backend", "source_id", "generation", "frames", "rejected_pairs", "sequence_gaps",
         "last_acquisition_ns", "clock_domain", "observed_ns", "last_skew_ns", "pairing_tolerance_ns"])
    status("detector", "Inference", "detector", "rgbd_object_detector_interfaces/msg/Status",
        ["state", "detail", "model_id", "model_profile_sha256", "engine_sha256", "generation", "processed", "replaced",
         "stale", "rejected", "failures", "last_source_age_ns", "last_inference_ns", "processing", "pending", "observed_ns"])
    status("overlay", "Presentation", "detector", "rgbd_object_detector_interfaces/msg/Status",
        ["overlay_enabled", "overlay_state", "overlay_detail", "overlay_processing", "overlay_pending", "overlay_rendered",
         "overlay_replaced", "overlay_stale", "overlay_superseded", "overlay_no_consumers", "overlay_failures", "overlay_last_render_ns"])
    video_settings = dict(width=640, height=480, fps=30, mode="fixed", bitrate=2500000, min_bitrate=250000, max_bitrate=2500000, keyframe_interval=1.0)
    profile = dict(schema_version=1, robot_id=site["robot_id"], namespace=site["runtime_namespace"], units=[perception, video],
        ros=dict(schema_version=1, python="/usr/bin/python3", setup_scripts=["/opt/ros/jazzy/setup.bash", site["ros_setup"]],
            domain_id=site["ros_domain_id"], discovery="LOCALHOST", topics=topics, services=[]),
        av=dict(services=[dict(id="video", label="Exact-capture perception overlay", kind="media", unit_id="video",
            host=site["media_host"], udp_port=site["media_udp_port"], max_sessions=2, encoder="hardware",
            source=dict(kind="ros", label="Selected camera and detector", owner_unit="perception",
                topic=namespace + "/detector/overlay/image", domain_id=site["ros_domain_id"]),
            profiles=dict(observer=video_settings, teleop=video_settings))]))
    from robot_runtime.profile import validate
    validated, revision = validate(profile)
    # Never replace an active profile implicitly. Choose a new output for changes.
    with output.open("x") as stream:
        stream.write(json.dumps(validated, indent=2) + "\n")
    return revision


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--d455", choices=("d455-30", "d455-60"), default="d455-30")
    parser.add_argument("--oak", choices=("oak-30", "oak-35", "oak-40"), default="oak-30")
    args = parser.parse_args()
    print(render(args.site.resolve(), args.output.resolve(), args.d455, args.oak))
