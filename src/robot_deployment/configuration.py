"""Strict configuration and bounded, explicitly delegated launch parameters."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import yaml

VARIANTS = {"oak_d_rvc2": "oak", "realsense_d455": "d455"}
NODES = ("camera", "detector_cones", "detector_coco", "combined_overlay")


class ConfigurationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ConfigurationError(message)


def keys(value, required, optional=(), *, context="configuration"):
    require(isinstance(value, dict), f"{context}: expected mapping")
    require(all(isinstance(key, str) for key in value), f"{context}: keys must be strings")
    missing, unknown = set(required) - value.keys(), value.keys() - set(required) - set(optional)
    require(not missing and not unknown, f"{context}: missing {sorted(missing)}, unknown {sorted(unknown)}")


def version(value, required, optional=(), *, context):
    keys(value, ("schema_version", *required), optional, context=context)
    require(type(value["schema_version"]) is int and value["schema_version"] == 1,
            f"{context}: unsupported schema_version")


def number(value, low, high, context, *, integer=False):
    require(type(value) is int if integer else type(value) in (int, float), f"{context}: invalid numeric type")
    require(math.isfinite(value) and low <= value <= high, f"{context}: must be {low}..{high}")


def identifier(value, context):
    require(isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", value), f"{context}: invalid identifier")
    return value


def absolute(value, context):
    require(isinstance(value, str) and value.startswith("/") and ".." not in Path(value).parts
            and "\x00" not in value and "\n" not in value, f"{context}: expected normalized absolute Linux path")
    return Path(value)


def within(root, relative):
    require(isinstance(relative, str) and not Path(relative).is_absolute(), "Definition paths must be relative")
    result = (root / relative).resolve()
    require(result.is_relative_to(root.resolve()), f"Path escapes declared root: {relative}")
    return result


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class StrictLoader(yaml.SafeLoader):
    def compose_node(self, parent, index):
        require(not self.check_event(yaml.AliasEvent), "YAML aliases are unsupported; write each value explicitly")
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            require(isinstance(key, str), "YAML keys must be strings")
            require(key not in result, f"Duplicate YAML key: {key}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


class Inputs:
    """One read per source; retain the actual admitted bytes' identities."""
    def __init__(self):
        self.values = {}
        self.raw = {}
        self.sources = []

    def read_bytes(self, path):
        path = Path(path).resolve()
        if path not in self.raw:
            with path.open("rb") as stream:
                raw = stream.read(262145)
            require(len(raw) <= 262144, f"{path}: exceeds 256 KiB")
            self.raw[path] = raw
            self.sources.append(dict(path=str(path), sha256=digest(raw)))
        return self.raw[path]

    def read(self, path):
        path = Path(path).resolve()
        if path not in self.values:
            raw = self.read_bytes(path)
            try:
                value = yaml.load(raw.decode("utf-8"), Loader=StrictLoader)
            except (yaml.YAMLError, UnicodeError, RecursionError) as exc:
                raise ConfigurationError(f"{path}: malformed YAML/JSON") from exc
            require(isinstance(value, dict), f"{path}: expected mapping")
            self.values[path] = value
        return copy.deepcopy(self.values[path])


def definition_root():
    installed = Path(sys.prefix) / "share/robot_deployment"
    return installed if installed.is_dir() else Path(__file__).resolve().parents[2]


def load(site_path, root=None, *, inputs=None):
    inputs = inputs or Inputs()
    root = Path(root or definition_root()).resolve()
    site = inputs.read(site_path)
    version(site, ("composition", "platform", "robot_id", "runtime_account", "storage", "network", "credentials"),
            ("ros", "runtime_namespace", "hardware", "camera_profiles", "workspaces", "management", "shell", "recording", "visual_odometry"), context="site")
    site.setdefault("visual_odometry", dict(enabled=False, backend="docker"))
    keys(site["visual_odometry"], ("enabled", "backend"), context="visual_odometry")
    require(type(site["visual_odometry"]["enabled"]) is bool and site["visual_odometry"]["backend"] in ("docker", "native"), "Select an explicit installed odometry backend")
    for key in ("composition", "platform", "robot_id", "runtime_account"):
        identifier(site[key], "site." + key)
    site.setdefault("runtime_namespace", "robot")
    identifier(site["runtime_namespace"], "runtime_namespace")
    keys(site["storage"], ("installation_root", "data_root"), context="site.storage")
    for key, value in site["storage"].items():
        absolute(value, key)
        require(value != "/", f"{key}: cannot be filesystem root")
    site.setdefault("recording", {})
    recording = site["recording"]
    defaults = dict(root=str(Path(site["storage"]["data_root"]) / "recordings"), budget_bytes=10000000000,
        reserve_bytes=1000000000, fps=30, segment_seconds=30, min_depth_m=.25, max_depth_m=15.,
        bitrates=dict(rgb=6000000, annotated=6000000, depth=4000000))
    keys(recording, (), defaults, context="recording")
    for key, value in defaults.items(): recording.setdefault(key, value)
    absolute(recording["root"], "recording.root")
    require(recording["root"] != "/", "Recording root cannot be filesystem root")
    for key, low, high in (("budget_bytes",1000000,1000000000000),("reserve_bytes",1000000,1000000000000),
                           ("fps",1,30),("segment_seconds",2,60)):
        number(recording[key],low,high,"recording."+key,integer=True)
    number(recording["min_depth_m"],.001,65.,"recording.min_depth_m")
    number(recording["max_depth_m"],recording["min_depth_m"],65.535,"recording.max_depth_m")
    require(recording["max_depth_m"]>recording["min_depth_m"],"Depth display range must be nonempty")
    keys(recording["bitrates"],("rgb","annotated","depth"),context="recording.bitrates")
    for bitrate in recording["bitrates"].values(): number(bitrate,100000,20000000,"recording bitrate",integer=True)
    keys(site["credentials"], ("web_secret_file", "tls_certificate_file", "tls_private_key_file"), context="site.credentials")
    for key, value in site["credentials"].items():
        absolute(value, key)  # References only: never open credential contents here.
    network = site["network"]
    keys(network, ("hostname", "media_address"), ("media_udp_port", "web_host", "web_port"), context="site.network")
    network.setdefault("media_udp_port", 8860)
    network.setdefault("web_host", "0.0.0.0")
    network.setdefault("web_port", 8443)
    for key in ("hostname", "media_address", "web_host"):
        require(isinstance(network[key], str) and re.fullmatch(r"[a-zA-Z0-9.:-]{1,253}", network[key]), f"network.{key}: invalid address/name")
    for key in ("media_udp_port", "web_port"):
        number(network[key], 1024, 65535, key, integer=True)
    site.setdefault("ros", dict(namespace="perception", domain_id=30))
    keys(site["ros"], ("namespace", "domain_id"), context="site.ros")
    require(isinstance(site["ros"]["namespace"], str) and re.fullmatch(r"[a-z][a-z0-9_]*(/[a-z][a-z0-9_]*)*", site["ros"]["namespace"]), "Invalid ROS namespace")
    number(site["ros"]["domain_id"], 0, 232, "ROS domain", integer=True)
    site.setdefault("workspaces", {})
    keys(site["workspaces"], (), ("student",), context="workspaces")
    for value in site["workspaces"].values():
        absolute(value, "workspace")
    for section, flag in (("management", "start"), ("shell", "alias")):
        site.setdefault(section, {flag: False})
        keys(site[section], (flag,), context=section)
        require(type(site[section][flag]) is bool, f"{section}.{flag}: expected boolean")
    composition = inputs.read(within(root, "compositions/" + site["composition"] + ".yaml"))
    version(composition, ("id", "robot_model", "sources", "cameras", "supported_platforms", "hardware", "models", "units", "workload_requests"), ("firmware",), context="composition")
    keys(composition.get("firmware", {}), (), ("bno08x", "traxxas", "rc_car"), context="firmware")
    firmware_profiles = {}
    for target, recipe in composition.get("firmware", {}).items():
        keys(recipe, ("source", "path", "board", "profile") if target == "rc_car" else
             ("source", "path", "board"), context="firmware recipe")
        keys(recipe["source"], ("url", "commit"), context="firmware source")
        require(isinstance(recipe["source"]["url"], str) and recipe["source"]["url"].startswith("https://"), "Firmware requires an explicit HTTPS source")
        require(recipe["board"] in ("waveshare_rp2040_zero", "waveshare_rp2350_zero"), "Unsupported firmware board")
        require(isinstance(recipe["source"]["commit"], str) and re.fullmatch(r"[0-9a-f]{40}", recipe["source"]["commit"]), "Firmware requires a full source commit")
        within(root, recipe["path"])
        if target == "rc_car":
            header = within(root, recipe["profile"])
            require(header.suffix == ".hpp", "RC Car profile must be a deployment-owned .hpp header")
            firmware_profiles[target] = dict(path=header, sha256=digest(inputs.read_bytes(header)))
    require(composition["id"] == site["composition"], "Composition identity mismatch")
    require(site["platform"] in composition["supported_platforms"], "Composition does not support selected platform")
    platform = inputs.read(within(root, "platforms/" + site["platform"] + ".yaml"))
    version(platform, ("id", "architecture", "os", "os_version", "l4t", "kernel_family", "python_family", "modules", "carriers", "cuda_family", "tensorrt_family", "encoder", "qualification"), context="platform")
    require(platform["id"] == site["platform"] and platform["encoder"] in ("hardware", "software"), "Invalid platform identity/encoder")
    model = inputs.read(within(root, composition["robot_model"]))
    validate_model(model)
    keys(composition["hardware"], ("front_camera",), context="composition hardware")
    selection = composition["hardware"]["front_camera"]
    keys(selection, ("default_variant", "allowed_variants"), context="camera selection")
    variants = selection["allowed_variants"]
    require(isinstance(variants, list) and set(variants) == set(VARIANTS), "This integration requires OAK-D and D455 variants")
    require(selection["default_variant"] in variants and set(variants) <= set(model["component_roles"]["front_camera"]["supported_variants"]), "Unsupported robot camera selection")
    site.setdefault("hardware", {"front_camera": {"variant": selection["default_variant"]}})
    keys(site["hardware"], ("front_camera",), ("rc_car",), context="site.hardware")
    if "rc_car" in site["hardware"]:
        pins = site["hardware"]["rc_car"]
        keys(pins, ("device_id", "profile_id", "build_id"), context="site.hardware.rc_car")
        require(isinstance(pins["device_id"], str) and re.fullmatch(r"[0-9A-F]{16}", pins["device_id"]),
                "RC Car needs an exact application device ID")
        for key in ("profile_id", "build_id"):
            require(isinstance(pins[key], str) and re.fullmatch(r"[A-Za-z0-9_-]{1,24}", pins[key]),
                    f"Invalid RC Car {key}")
        if "rc_car" in firmware_profiles:
            require(pins["profile_id"] == firmware_profiles["rc_car"]["sha256"][:16],
                    "Private RC Car profile pin differs from the selected header")
    camera = site["hardware"]["front_camera"]
    keys(camera, ("variant",), ("device_ids",), context="front_camera")
    require(camera["variant"] in variants, "Unsupported camera variant")
    camera.setdefault("device_ids", {})
    keys(camera["device_ids"], (), variants, context="camera session selections")
    for identity in camera["device_ids"].values():
        require(isinstance(identity, str) and re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", identity), "Invalid explicit camera session identity")
    cameras = inputs.read(within(root, composition["cameras"]))
    version(cameras, ("defaults", "profiles", "limits"), ("stereo_profiles",), context="cameras")
    require(isinstance(cameras.get("stereo_profiles", []), list) and
            all(name in cameras["profiles"] for name in cameras.get("stereo_profiles", [])), "Unknown stereo camera profile")
    site.setdefault("camera_profiles", dict(oak="oak-30", d455="d455-30"))
    keys(site["camera_profiles"], ("oak", "d455"), context="camera_profiles")
    for family, name in site["camera_profiles"].items():
        require(name in cameras["profiles"] and cameras["profiles"][name]["backend"] == ("realsense" if family == "d455" else "oak"), "Camera profile/backend mismatch")
    keys(composition["units"], ("perception", "video"), ("vehicle",), context="units")
    if "vehicle" in composition["units"]:
        vehicle = composition["units"]["vehicle"]
        keys(vehicle, ("launcher", "source"), context="vehicle")
        keys(vehicle["source"], ("url", "commit"), context="vehicle source")
        require(vehicle["launcher"] == "rc_car_interface" and "rc_car" in site["hardware"],
                "Vehicle unit needs the RC Car launcher and private hardware pins")
        require(isinstance(vehicle["source"]["url"], str) and vehicle["source"]["url"].startswith("https://") and
                isinstance(vehicle["source"]["commit"], str) and re.fullmatch(r"[0-9a-f]{40}", vehicle["source"]["commit"]),
                "Vehicle interface requires an exact HTTPS source commit")
    keys(composition["units"]["perception"], ("launcher", "parameter_files"), context="perception")
    keys(composition["units"]["video"], ("launcher", "choices", "default_choice", "maximum_fps"), context="video")
    video = composition["units"]["video"]
    require(composition["units"]["perception"]["launcher"] == "rgbd_perception" and video["launcher"] == "runtime_ros_video", "Unsupported installed launcher")
    require(video["choices"] == ["rgb", "cones", "coco", "combined"] and video["default_choice"] in video["choices"], "Invalid video choices")
    number(video["maximum_fps"], 1, 30, "video.maximum_fps", integer=True)
    keys(composition["models"], ("cones", "coco"), context="models")
    for descriptor in composition["models"].values():
        keys(descriptor, ("component", "descriptor"), context="model descriptor")
        require(descriptor["component"] == "rgbd_object_detector", "Unsupported detector owner")
        within(root, descriptor["descriptor"])
    sources = inputs.read(within(root, composition["sources"]))
    require(type(sources.get("schema_version")) is int and sources["schema_version"] == 1, "Unsupported sources schema")
    return dict(site=site, composition=composition, robot_model=model, platform=platform, cameras=cameras,
                sources=sources, root=root, inputs=inputs, firmware_profiles=firmware_profiles)


def validate_model(model):
    version(model, ("id", "geometry", "component_roles", "mounts"), context="robot model")
    identifier(model["id"], "robot model id")
    geometry = model["geometry"]
    keys(geometry, ("provenance", "axes", "body_m", "wheelbase_m", "wheel_radius_m", "base_frame"), context="geometry")
    require(geometry["axes"] == "x-forward-y-left-z-up", "Unsupported base coordinate convention")
    require(isinstance(geometry["provenance"], str) and bool(geometry["provenance"]), "Geometry needs provenance")
    keys(geometry["body_m"], ("length", "width", "height"), context="body dimensions")
    for key, value in {**geometry["body_m"], "wheelbase": geometry["wheelbase_m"], "wheel_radius": geometry["wheel_radius_m"]}.items():
        number(value, .001, 100, key)
    keys(model["component_roles"], ("front_camera",), context="component roles")
    role = model["component_roles"]["front_camera"]
    keys(role, ("supported_variants", "selection"), context="camera role")
    require(role["selection"] == "unique_available_device" and isinstance(role["supported_variants"], list)
            and set(role["supported_variants"]) <= set(VARIANTS), "Unsupported camera role selection")
    keys(model["mounts"], ("front_camera",), context="mounts")
    mount = model["mounts"]["front_camera"]
    keys(mount, ("parent_frame", "child_frame", "translation_m", "rotation_rpy_rad", "optical_frame", "optical_rotation_rpy_rad"), context="camera mount")
    for name in ("translation_m", "rotation_rpy_rad", "optical_rotation_rpy_rad"):
        require(isinstance(mount[name], list) and len(mount[name]) == 3, f"{name}: expected xyz/rpy triple")
        for value in mount[name]:
            number(value, -100, 100, name)
    for name in ("parent_frame", "child_frame", "optical_frame"):
        identifier(mount[name], name)
    require(mount["parent_frame"] == geometry["base_frame"] and len({mount[k] for k in ("parent_frame", "child_frame", "optical_frame")}) == 3, "Invalid mount frame tree")


def structure_identity(graph):
    site = copy.deepcopy(graph["site"])
    site["hardware"]["front_camera"].pop("device_ids")
    structure = {**{key: graph[key] for key in ("composition", "robot_model", "platform", "cameras", "sources")}, "site": site}
    if graph.get("firmware_profiles"):
        structure["firmware_profiles"] = {key: entry["sha256"] for key, entry in graph["firmware_profiles"].items()}
    return digest(encoded(structure))


CAMERA_BOUNDS = {"fps": (1, 60), "pairing_tolerance_ms": (.1, 50), "max_frame_age_ms": (10, 2000),
                 "startup_timeout_s": (5, 120), "stall_timeout_s": (1, 30), "width": (640,1280), "height": (360,720)}
DETECTOR_BOUNDS = {"score_threshold": (0, 1), "iou_threshold": (0, 1), "max_detections": (1, 100),
                   "pre_nms_limit": (1, 8400)}


def validate_parameters(nodes):
    keys(nodes, NODES, context="effective nodes")
    for node, parameters in nodes.items():
        bounds = CAMERA_BOUNDS if node == "camera" else DETECTOR_BOUNDS if node.startswith("detector_") else {}
        flags = ("enable_imu", "publish_images") if node == "camera" else ()
        choices = {"timestamp_policy": ("recover", "strict")} if node == "camera" else {}
        keys(parameters, (), (*bounds, *flags, *choices), context=node)
        for name, value in parameters.items():
            if name in flags:
                require(type(value) is bool, f"{node}.{name}: expected boolean")
            elif name in choices:
                require(isinstance(value, str) and value in choices[name],
                        f"{node}.{name}: expected recover or strict")
            else:
                number(value, *bounds[name], f"{node}.{name}", integer=name in ("max_detections", "pre_nms_limit", "width", "height"))
        if node.startswith("detector_") and "pre_nms_limit" in parameters and "max_detections" in parameters:
            require(parameters["max_detections"] <= parameters["pre_nms_limit"], f"{node}: max_detections exceeds pre_nms_limit")
    camera = nodes["camera"]
    if "width" in camera or "height" in camera:
        require((camera.get("width"),camera.get("height")) in ((640,360),(640,480),(640,640),(1280,720)), "Unsupported camera dimensions")
        require(camera['height'] not in (360,720) or camera.get('fps',30)<=30, 'Wide camera profiles support at most 30 Hz')
    if "fps" in camera and "pairing_tolerance_ms" in camera:
        require(camera["pairing_tolerance_ms"] < 500 / camera["fps"], "camera: pairing tolerance must be below half a frame period")


def parameters(graph):
    nodes = {name: {} for name in NODES}
    files = graph["composition"]["units"]["perception"]["parameter_files"]
    require(isinstance(files, list) and 1 <= len(files) <= 8, "Declare one to eight parameter files")
    for filename in files:
        document = graph["inputs"].read(within(graph["root"], filename))
        version(document, ("nodes",), context=filename)
        keys(document["nodes"], (), NODES, context=filename)
        for node, values in document["nodes"].items():
            require(isinstance(values, dict) and not (nodes[node].keys() & values.keys()), f"{filename}: duplicate parameter authority for {node}")
            nodes[node].update(values)
    validate_parameters(nodes)
    requests = graph["composition"]["workload_requests"]
    keys(requests, (), ("student",), context="workload requests")
    admitted = []
    for source, spec in requests.items():
        keys(spec, ("workspace_binding", "file", "optional", "mappings"), context=source)
        require(spec["workspace_binding"] == "student" and type(spec["optional"]) is bool, f"{source}: invalid binding")
        require(isinstance(spec["mappings"], dict) and len(spec["mappings"]) <= 64, f"{source}: invalid mappings")
        targets = set()
        for key, mapping in spec["mappings"].items():
            identifier(key, "request key")
            keys(mapping, ("target", "type", "units", "minimum", "maximum", "apply"), context=key)
            target = mapping["target"]
            keys(target, ("unit", "node", "parameter"), context=key)
            require(target["unit"] == "perception" and target["node"] in nodes and target["parameter"] in nodes[target["node"]], f"{key}: target needs a declared default")
            require(mapping["apply"] == "startup" and mapping["type"] in ("double", "integer"), f"{key}: unsupported request contract")
            require(isinstance(mapping["units"], str), f"{key}: declare units")
            number(mapping["minimum"], -1e9, 1e9, key)
            number(mapping["maximum"], mapping["minimum"], 1e9, key)
            identity = (target["node"], target["parameter"])
            require(identity not in targets, f"{key}: duplicate mapping target")
            targets.add(identity)
        workspace = graph["site"]["workspaces"].get(spec["workspace_binding"])
        if not workspace:
            require(spec["optional"], f"{source}: required workspace binding missing")
            continue
        path = within(Path(workspace), spec["file"])
        if not path.exists():
            require(spec["optional"], f"{path}: required request file missing")
            continue
        values = graph["inputs"].read(path)
        keys(values, (), spec["mappings"], context=str(path))
        for key, value in values.items():
            mapping = spec["mappings"][key]
            number(value, mapping["minimum"], mapping["maximum"], f"{path}:{key}", integer=mapping["type"] == "integer")
            target = mapping["target"]
            nodes[target["node"]][target["parameter"]] = float(value) if mapping["type"] == "double" else value
            admitted.append(dict(source=source, key=key, target=target, value=value))
    validate_parameters(nodes)
    return nodes, admitted
