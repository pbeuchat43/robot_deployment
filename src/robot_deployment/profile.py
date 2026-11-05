#!/usr/bin/env python3
"""Render the selected composition through the independently owned runtime schema."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import json
from pathlib import Path

from .configuration import load, structure_identity, VARIANTS


def build_profile(graph, site_path, release, output):
    """Derive all artifact paths from one release; never probe devices or use IPC."""
    release, output = Path(release).resolve(), Path(output).resolve()
    source = graph["site"]
    data = Path(source["storage"]["data_root"])
    site = dict(robot_id=source["robot_id"], runtime_namespace=source["runtime_namespace"],
        workdir=str(data / "work"), native_prefix=str(release / "av-native"),
        ros_namespace=source["ros"]["namespace"], ros_domain_id=source["ros"]["domain_id"],
        ros_setup=str(release / "ros/install/setup.bash"), runtime_python=str(release / "venv/bin/python"),
        state=str(data / "runtime"), media_host=source["network"]["media_address"],
        media_udp_port=source["network"]["media_udp_port"],
        sdk_library_paths=[str(release / "sdk" / name / "lib") for name in ("depthai", "realsense")])
    work = Path(site["workdir"])
    native = Path(site["native_prefix"])
    wrapper = str(graph["root"] / "tools/with_ros.sh")
    namespace = "/" + site["ros_namespace"].strip("/")
    environment = dict(PATH="/usr/bin:/bin", RGBD_SETUP=site["ros_setup"],
        ROS_DOMAIN_ID=str(site["ros_domain_id"]), ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST",
        RMW_IMPLEMENTATION="rmw_fastrtps_cpp", ROS_LOG_DIR=str(work / "ros-log"),
        LD_LIBRARY_PATH=":".join(site.get("sdk_library_paths", [])))
    modes = []
    for camera, label in (("d455", "D455"), ("oak", "OAK-D")):
        camera_profile = source["camera_profiles"][camera]
        for model, model_label in (("cones", "Cones"), ("coco", "COCO 80"), ("both", "Cones + COCO 80")):
            modes.append(dict(id=camera + "-" + model, label=f"{label} / {model_label} / {camera_profile}",
                selections=dict(camera=camera, model=model),
                argv=["/bin/bash", wrapper, site["runtime_python"], "-m", "robot_deployment.launch"]))
    default_mode = VARIANTS[source["hardware"]["front_camera"]["variant"]] + "-both"
    selected = next(mode for mode in modes if mode["id"] == default_mode)
    perception = dict(id="perception", label="RGB-D perception", argv=selected["argv"],
        launch_modes=modes, default_launch_mode=default_mode,
        launch_selections=[dict(id="camera", label="Camera", choices=[dict(id="d455", label="D455"), dict(id="oak", label="OAK-D")]),
            dict(id="model", label="Models", choices=[dict(id="cones", label="Cones"), dict(id="coco", label="COCO 80"),
                dict(id="both", label="Cones + COCO 80")])],
        working_directory=str(work), environment=environment, stop=dict(signal="SIGINT", timeout_seconds=20), public_logs=True,
        preparation=dict(argv=[site["runtime_python"], "-m", "robot_deployment.preparation",
            "--site", str(Path(site_path).resolve()), "--definitions", str(graph["root"]),
            "--release", str(release), "--expected-structure", structure_identity(graph)], timeout_seconds=5))
    video_environment = dict(environment, GST_PLUGIN_PATH=str(native / "gstreamer"),
        GST_REGISTRY=str(work / "gst-registry.bin"), ROBOT_AV_GI_OVERRIDES=str(native / "gi"), PYTHONPATH=str(native / "python"))
    video = dict(id="video", label="Perception video", argv=["/bin/bash", wrapper, site["runtime_python"],
        "-m", "robot_runtime.av.worker", "--profile", str(output), "--state", site["state"], "--capability", "video"],
        working_directory=str(work), environment=video_environment,
        stop=dict(signal="SIGINT", timeout_seconds=15), public_logs=True)
    topics = []
    def status(identity, label, node, interface, fields, active_modes=None):
        topics.append(dict(id=identity, label=label, unit_id="perception", node=namespace + "/" + node,
            name=namespace + "/" + node + "/status", type=interface,
            qos=dict(reliability="best_effort", durability="volatile", depth=1),
            max_rate_hz=2, stale_after_seconds=1, max_serialized_bytes=16384, max_json_bytes=8192, fields=fields))
        if active_modes is not None:
            topics[-1]["active_modes"] = active_modes
    status("camera", "Acquisition", "camera", "rgbd_camera_interfaces/msg/Status",
        ["state", "detail", "backend", "source_id", "generation", "frames", "rejected_pairs", "sequence_gaps",
         "last_acquisition_ns", "clock_domain", "observed_ns", "last_skew_ns", "pairing_tolerance_ns"])
    overlay_choices = []
    for model, label in (("cones", "Cones"), ("coco", "COCO 80")):
        active_modes = [mode["id"] for mode in modes if mode["selections"]["model"] in (model, "both")]
        node = "detector_" + model
        status(model, label + " inference", node, "rgbd_object_detector_interfaces/msg/Status",
            ["state", "detail", "model_id", "model_profile_sha256", "engine_sha256", "generation", "processed", "replaced",
             "stale", "rejected", "failures", "last_source_age_ns", "last_inference_ns", "processing", "pending", "observed_ns"], active_modes)
        status(model + "_overlay", label + " presentation", node, "rgbd_object_detector_interfaces/msg/Status",
            ["overlay_enabled", "overlay_state", "overlay_detail", "overlay_processing", "overlay_pending", "overlay_rendered",
             "overlay_replaced", "overlay_stale", "overlay_superseded", "overlay_no_consumers", "overlay_failures", "overlay_last_render_ns"], active_modes)
        overlay_choices.append(dict(id=model, label=label, topic=namespace + "/" + node + "/overlay/image", active_modes=active_modes))
    dual_modes = [mode["id"] for mode in modes if mode["selections"]["model"] == "both"]
    status("combined_overlay", "Combined presentation", "combined_overlay", "rgbd_object_detector_interfaces/msg/CombinedOverlayStatus",
        ["state", "detail", "generation", "matched", "rendered", "rejected", "expired", "evicted",
         "replaced", "superseded", "no_consumers", "failures", "retained", "pending", "processing", "last_render_ns"], dual_modes)
    overlay_choices.append(dict(id="combined", label="Combined", topic=namespace + "/combined_overlay/overlay/image", active_modes=dual_modes))
    video_config = graph["composition"]["units"]["video"]
    video_settings = dict(width=640, height=480, fps=video_config["maximum_fps"], mode="fixed", bitrate=2500000, min_bitrate=250000, max_bitrate=2500000, keyframe_interval=1.0)
    profile = dict(schema_version=1, robot_id=site["robot_id"], namespace=site["runtime_namespace"], units=[perception, video],
        ros=dict(schema_version=1, python="/usr/bin/python3", setup_scripts=["/opt/ros/jazzy/setup.bash", site["ros_setup"]],
            domain_id=site["ros_domain_id"], discovery="LOCALHOST", topics=topics, services=[]),
        av=dict(services=[dict(id="video", label="Exact-capture perception overlay", kind="media", unit_id="video",
            host=site["media_host"], udp_port=site["media_udp_port"], max_sessions=2, encoder=graph["platform"]["encoder"],
            source=dict(kind="ros", label="Selected camera and detector", owner_unit="perception",
                choices=overlay_choices, default_choice=video_config["default_choice"], domain_id=site["ros_domain_id"]),
            profiles=dict(observer=video_settings, teleop=video_settings))]))
    return profile


def render(site_path, release, output, *, root=None, check_paths=True):
    from robot_runtime.profile import validate
    graph = load(site_path, root)
    profile = build_profile(graph, site_path, release, output)
    validated, revision = validate(profile, check_paths=check_paths)
    with Path(output).open("x") as stream:
        stream.write(json.dumps(validated, indent=2) + "\n")
    return revision
