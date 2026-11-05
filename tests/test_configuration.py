"""Configuration boundaries; no ROS, IPC or devices required."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import json
from pathlib import Path
import shutil
import tempfile
import sys
import unittest

from robot_deployment.configuration import (ConfigurationError, Inputs, definition_root, encoded,
                                            digest, load, parameters, structure_identity, within)
from robot_deployment.preparation import effective, prepare
from robot_deployment.profile import build_profile
from robot_runtime.prepared import execute, freeze, load as read_prepared
from robot_runtime.profile import validate


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.work = Path(self.temporary.name)
        self.root = self.work / "definitions"
        shutil.copytree(definition_root(), self.root, ignore=shutil.ignore_patterns(".git", "__pycache__", "build", "*.egg-info", "dist"))
        self.site = Inputs().read(self.root / "config/site.example.yaml")
        self.site["storage"] = dict(installation_root=str(self.work / "installation"), data_root=str(self.work / "data"))
        self.student = self.work / "student"
        (self.student / "config").mkdir(parents=True)
        self.site["workspaces"] = dict(student=str(self.student))
        self.path = self.work / "site.yaml"
        self.save()

    def tearDown(self):
        for item in self.work.rglob("*"):
            if item.is_dir():
                item.chmod(0o700)
            elif not item.is_symlink():
                item.chmod(0o600)
        self.temporary.cleanup()

    def save(self):
        self.path.write_bytes(encoded(self.site))

    def graph(self):
        return load(self.path, self.root)

    def request(self, text):
        (self.student / "config/requests.yaml").write_text(text)

    def test_default_and_allowed_request(self):
        self.assertEqual(parameters(self.graph())[0]["detector_cones"]["score_threshold"], .5)
        self.request("cones_score_threshold: 0.65\n")
        nodes, requests = parameters(self.graph())
        self.assertEqual(nodes["detector_cones"]["score_threshold"], .65)
        self.assertEqual(nodes["detector_cones"]["max_detections"], 20)
        self.assertEqual(len(requests), 1)

    def test_unknown_request_type_and_bound(self):
        for text in ("max_detections: 3", "cones_score_threshold: true", "cones_score_threshold: 0.95", "cones_score_threshold: .nan"):
            with self.subTest(text=text), self.assertRaises(ConfigurationError):
                self.request(text)
                parameters(self.graph())

    def test_duplicate_alias_and_unknown_site(self):
        for text in ("x: 1\nx: 2", "x: &value [1]\ny: *value"):
            self.path.write_text(text)
            with self.assertRaises(ConfigurationError):
                Inputs().read(self.path)
        self.site["models"] = {}
        self.save()
        with self.assertRaises(ConfigurationError):
            self.graph()

    def test_unsupported_schema_and_wrong_backend(self):
        self.site["schema_version"] = True
        self.save()
        with self.assertRaises(ConfigurationError):
            self.graph()
        self.site["schema_version"] = 1
        self.site["camera_profiles"]["oak"] = "d455-30"
        self.save()
        with self.assertRaises(ConfigurationError):
            self.graph()

    def test_relative_boundaries_include_symlinks(self):
        outside = self.work / "outside"
        outside.mkdir()
        (self.root / "outside-link").symlink_to(outside)
        for path in ("../outside", "/tmp/outside", "outside-link/request.yaml"):
            with self.subTest(path=path), self.assertRaises(ConfigurationError):
                within(self.root, path)

    def test_one_read_for_each_authority(self):
        inputs = Inputs()
        graph = load(self.path, self.root, inputs=inputs)
        self.site["robot_id"] = "changed"
        self.save()
        self.assertEqual(inputs.read(self.path)["robot_id"], "car-02")
        self.assertEqual(graph["site"]["robot_id"], "car-02")
        self.assertEqual(len(inputs.sources), len({item["path"] for item in inputs.sources}))

    def test_six_modes_mount_and_default_discovery(self):
        graph = self.graph()
        profile = build_profile(graph, self.path, self.work / "release", self.work / "runtime.json")
        checked, revision = validate(profile, check_paths=False)
        self.assertTrue(revision)
        unit = next(unit for unit in checked["units"] if unit["id"] == "perception")
        modes = unit["launch_modes"]
        self.assertEqual(len(modes), 6)
        for mode in modes:
            value = effective(self.graph(), self.work / "release", mode["id"], check_artifacts=False)
            self.assertEqual(value["nodes"]["camera"]["device_id"], "")
            self.assertEqual(value["nodes"]["camera"]["optical_frame"], "front_camera_optical")
            self.assertEqual(value["mount"]["parent_frame"], "base_link")
        self.assertEqual(unit["default_launch_mode"], "oak-both")

    def test_explicit_identity_is_variant_scoped(self):
        before = structure_identity(self.graph())
        self.site["hardware"]["front_camera"]["device_ids"] = {"oak_d_rvc2": "selected-camera"}
        self.save()
        self.assertEqual(structure_identity(self.graph()), before)
        oak = effective(self.graph(), self.work, "oak-cones", check_artifacts=False)
        d455 = effective(self.graph(), self.work, "d455-cones", check_artifacts=False)
        self.assertEqual(oak["nodes"]["camera"]["device_id"], "selected-camera")
        self.assertEqual(d455["nodes"]["camera"]["device_id"], "")

    def test_grouped_final_parameters(self):
        path = self.root / "parameters/perception.yaml"
        document = Inputs().read(path)
        document["nodes"]["camera"].update(fps=60., pairing_tolerance_ms=10.)
        path.write_bytes(encoded(document))
        with self.assertRaisesRegex(ConfigurationError, "half a frame"):
            effective(self.graph(), self.work, "d455-both", check_artifacts=False)

    def test_runtime_snapshot_survives_source_edits(self):
        self.request("cones_score_threshold: 0.6")
        candidate = prepare(self.path, self.work, "perception", "revision", "oak-both", root=self.root, check_artifacts=False)
        runtime = self.work / "runtime"
        runtime.mkdir()
        frozen = freeze(candidate, runtime, "perception", "revision", "oak-both")
        self.request("cones_score_threshold: 0.9")
        manifest, files = read_prepared(frozen)
        value = json.loads(files["effective"])
        self.assertEqual(value["nodes"]["detector_cones"]["score_threshold"], .6)
        ros = json.loads(files["ros-parameters"])
        self.assertEqual(ros["/perception/detector_cones"]["ros__parameters"]["score_threshold"], .6)
        self.assertEqual(manifest["mode"], "oak-both")

    def test_structural_edit_requires_stopped_maintenance(self):
        identity = structure_identity(self.graph())
        self.site["ros"]["domain_id"] += 1
        self.save()
        with self.assertRaisesRegex(ConfigurationError, "Structural"):
            prepare(self.path, self.work, "perception", "revision", "oak-both", root=self.root,
                    expected_structure=identity, check_artifacts=False)

    def test_missing_artifact_fails_before_candidate(self):
        with self.assertRaisesRegex(ConfigurationError, "Missing installed"):
            prepare(self.path, self.work, "perception", "revision", "oak-both", root=self.root)
        self.assertFalse((self.work / "data/deployment/prepared").exists())

    def artifacts(self):
        for name in ("cones", "coco"):
            directory = self.work / "models" / name
            directory.mkdir(parents=True)
            (directory / "model.engine").write_bytes(b"synthetic engine")
            (directory / "profile.json").write_bytes(b"synthetic descriptor")
            (directory / "model.engine.json").write_bytes(encoded(dict(schema_version=2,
                engine_sha256=digest(b"synthetic engine"), profile_sha256=digest(b"synthetic descriptor"))))

    def test_corrupt_artifact_rejected_before_candidate(self):
        self.artifacts()
        (self.work / "models/cones/model.engine").write_bytes(b"changed")
        with self.assertRaisesRegex(ConfigurationError, "engine hash mismatch"):
            prepare(self.path, self.work, "perception", "revision", "oak-both", root=self.root)
        self.assertFalse((self.work / "data/deployment/prepared").exists())

    def test_installed_preparer_through_runtime_worker(self):
        self.artifacts()
        target = dict(unit_id="perception", config_revision="revision", mode="d455-both",
            working_directory=str(self.work), environment={"PATH": "/usr/bin:/bin"},
            preparation=dict(timeout_seconds=5, argv=[sys.executable, "-m", "robot_deployment.preparation",
                "--site", str(self.path), "--release", str(self.work), "--definitions", str(self.root),
                "--expected-structure", structure_identity(self.graph())]))
        result = execute(target)
        self.assertEqual(result["mode"], "d455-both")
        self.assertEqual(result["unit_id"], "perception")


if __name__ == "__main__":
    unittest.main()
