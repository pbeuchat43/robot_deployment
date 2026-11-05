"""Validate editable startup inputs before handing a candidate to runtime."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import argparse
import json
import os
from pathlib import Path
import sys
import uuid

from .configuration import (load, parameters, require, structure_identity, validate_parameters,
                            encoded, digest, file_digest, VARIANTS)


def effective(graph, release, mode, *, check_artifacts=True):
    require(mode in {family + "-" + model for family in ("oak", "d455") for model in ("cones", "coco", "both")}, "Unknown perception mode")
    family, model = mode.split("-", 1)
    selected = ["cones", "coco"] if model == "both" else [model]
    nodes, admitted = parameters(graph)
    camera = dict(graph["cameras"]["defaults"], **graph["cameras"]["profiles"][graph["site"]["camera_profiles"][family]])
    camera.pop("width")
    camera.pop("height")
    camera.update(nodes["camera"])
    validate_parameters(dict(nodes, camera={key: value for key, value in camera.items() if key != "backend"}))
    variant = next(key for key, value in VARIANTS.items() if value == family)
    camera["device_id"] = graph["site"]["hardware"]["front_camera"]["device_ids"].get(variant, "")
    mount = graph["robot_model"]["mounts"]["front_camera"]
    camera["optical_frame"] = mount["optical_frame"]
    nodes["camera"] = camera
    for selected_model in selected:
        paths = dict(engine_path=str(Path(release) / "models" / selected_model / "model.engine"),
                     model_profile=str(Path(release) / "models" / selected_model / "profile.json"))
        if check_artifacts:
            for path in paths.values():
                require(Path(path).is_file(), f"Missing installed model artifact: {path}; complete installation first")
            manifest_path = Path(paths["engine_path"] + ".json")
            require(manifest_path.is_file(), "Missing engine compatibility manifest")
            manifest = graph["inputs"].read(manifest_path)
            require(manifest.get("schema_version") == 2, "Unsupported engine compatibility manifest")
            require(file_digest(paths["engine_path"]) == manifest.get("engine_sha256"), "Installed engine hash mismatch")
            require(file_digest(paths["model_profile"]) == manifest.get("profile_sha256"), "Installed descriptor hash mismatch")
        nodes["detector_" + selected_model].update(paths, publish_overlay=True, overlay_spatial=True)
    nodes["combined_overlay"].update(overlay_spatial=True)
    return dict(schema_version=1, namespace=graph["site"]["ros"]["namespace"], mode=mode, selected_models=selected,
                nodes=nodes, mount=mount, geometry=graph["robot_model"]["geometry"],
                provenance=dict(sources=list(graph["inputs"].sources), requests=admitted,
                                structure_sha256=structure_identity(graph)))


def prepare(site_path, release, unit, revision, mode, *, root=None, expected_structure=None, check_artifacts=True):
    require(unit == "perception", "This preparer only admits the perception unit")
    graph = load(site_path, root)
    if expected_structure:
        require(structure_identity(graph) == expected_structure,
                "Structural configuration changed; render/select a new profile during stopped maintenance")
    snapshot = effective(graph, release, mode, check_artifacts=check_artifacts)
    destination = Path(graph["site"]["storage"]["data_root"]) / "deployment/prepared" / uuid.uuid4().hex
    destination.mkdir(parents=True, mode=0o700)
    ros = {"/" + snapshot["namespace"] + "/" + node: {"ros__parameters": values} for node, values in snapshot["nodes"].items()}
    files = []
    for name, value in (("effective", snapshot), ("ros-parameters", ros)):
        raw = encoded(value)
        path = destination / name
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        path.chmod(0o400)
        files.append(dict(name=name, path=str(path), sha256=digest(raw)))
    destination.chmod(0o500)
    return dict(schema_version=1, unit_id=unit, config_revision=revision, mode=mode, inputs=files)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--definitions", type=Path)
    parser.add_argument("--expected-structure")
    args = parser.parse_args(argv)
    try:
        candidate = prepare(args.site, args.release,
            os.environ["ROBOT_RUNTIME_PREPARE_UNIT"], os.environ["ROBOT_RUNTIME_PREPARE_REVISION"],
            os.environ["ROBOT_RUNTIME_PREPARE_MODE"], root=args.definitions, expected_structure=args.expected_structure)
        print(json.dumps(candidate))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
