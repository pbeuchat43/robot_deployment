"""Source, failed-stage and owned-file boundaries without host mutation."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from robot_deployment.artifacts import acquire_git, download, run
from robot_deployment.configuration import ConfigurationError, Inputs, definition_root, digest
from robot_deployment.platform import admit, reject_bsp_changes
from robot_deployment.records import Attempt, claim, locked
from robot_deployment.services import install as install_services
from robot_deployment.installation import wheel_identity


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_download_identity_and_corrupt_cache(self):
        cache = self.root / "cache"
        with patch("urllib.request.urlopen", return_value=io.BytesIO(b"selected")) as network:
            path = download("https://example.invalid/model", digest(b"selected"), cache)
            self.assertEqual(download("https://example.invalid/model", digest(b"selected"), cache), path)
            self.assertEqual(network.call_count, 1)
        path.write_bytes(b"changed")
        with self.assertRaisesRegex(ConfigurationError, "Corrupt cached"):
            download("https://example.invalid/model", digest(b"selected"), cache)
        with patch("urllib.request.urlopen", return_value=io.BytesIO(b"wrong")), self.assertRaisesRegex(ConfigurationError, "hash mismatch"):
            download("https://example.invalid/other", digest(b"another"), cache)
        self.assertEqual(len(list(cache.iterdir())), 1)

    def test_exact_local_source_and_modified_cache(self):
        local = self.root / "local/component"
        local.mkdir(parents=True)
        run(["git", "init", local], capture=True)
        run(["git", "config", "user.name", "Fixture"], cwd=local)
        run(["git", "config", "user.email", "fixture@example.invalid"], cwd=local)
        (local / "input").write_text("selected")
        run(["git", "add", "input"], cwd=local)
        run(["git", "commit", "-m", "fixture"], cwd=local, capture=True)
        commit = run(["git", "rev-parse", "HEAD"], cwd=local, capture=True)
        selected = dict(url="https://example.invalid/component.git", commit=commit)
        path = acquire_git("component", selected, self.root / "cache", source_cache=local.parent)
        self.assertEqual((path / "input").read_text(), "selected")
        (path / "input").write_text("changed")
        with self.assertRaisesRegex(ConfigurationError, "Modified source"):
            acquire_git("component", selected, self.root / "cache", source_cache=local.parent)

    def test_completed_stage_reused_only_if_unchanged(self):
        release, record = self.root / "release", self.root / "record.json"
        attempt = Attempt(release, record, dict(selection="a"))
        attempt.stage("fixture", ["artifact"], lambda: (release / "artifact").write_text("selected"))
        resumed = Attempt(release, record, dict(selection="a"))
        resumed.stage("fixture", ["artifact"], lambda: self.fail("Completed stage must be reused"))
        (release / "artifact").write_text("changed")
        with self.assertRaisesRegex(ConfigurationError, "outputs changed"):
            resumed.stage("fixture", ["artifact"], lambda: None)
        with self.assertRaisesRegex(ConfigurationError, "inputs changed"):
            Attempt(release, record, dict(selection="b"))

    def test_failed_stage_records_without_selection(self):
        release, record = self.root / "release", self.root / "record.json"
        attempt = Attempt(release, record, {})
        def fail():
            (release / "partial").write_text("unfinished")
            raise ValueError("fixture failure")
        with self.assertRaises(ValueError):
            attempt.stage("fixture", ["partial"], fail)
        self.assertEqual(json.loads(record.read_text())["result"], "failed")
        self.assertFalse((self.root / "current").exists())
        with self.assertRaisesRegex(ConfigurationError, "partial/failed"):
            Attempt(release, record, {}).stage("fixture", ["partial"], lambda: None)

    def test_unowned_directory_and_concurrent_installation(self):
        root = self.root / "install"
        root.mkdir()
        (root / "unrelated").write_text("preserve")
        with self.assertRaisesRegex(ConfigurationError, "unowned"):
            claim(root, purpose="installation")
        owned = claim(self.root / "owned", purpose="installation")
        with locked(owned):
            with self.assertRaisesRegex(ValueError, "Another installation"):
                with locked(owned):
                    self.fail("must not acquire twice")
        self.assertEqual((root / "unrelated").read_text(), "preserve")

    def test_platform_admission_and_bsp_transaction(self):
        declared = Inputs().read(definition_root() / "platforms/orin-nx-jp721.yaml")
        observed = dict(architecture="aarch64", os="ubuntu", os_version="24.04", kernel="6.8.12-tegra", python="3.12.3",
            compatible="nvidia,p3768-0000+p3767-0000", packages={"nvidia-l4t-core": "39.2.1-build", "cuda-cudart-13-2": "13.2.86-1", "libnvinfer10": "10.16.2.10-1+cuda13.2"})
        self.assertEqual(admit(declared, observed), observed)
        for key, value in (("architecture", "x86_64"), ("compatible", "custom-carrier"), ("python", "3.10.0")):
            with self.subTest(key=key), self.assertRaises(ConfigurationError):
                admit(declared, dict(observed, **{key: value}))
        for text in ("Remv something", "Inst nvidia-l4t-core [39.2.1] (39.3)"):
            with self.assertRaises(ConfigurationError):
                reject_bsp_changes(text)

    def test_management_files_preserve_unrelated_edits(self):
        site = Inputs().read(definition_root() / "config/site.example.yaml")
        site["storage"] = dict(installation_root=str(self.root / "install"), data_root=str(self.root / "data"))
        (self.root / "data/deployment").mkdir(parents=True)
        directory = self.root / "services"
        install_services(site, directory)
        install_services(site, directory)
        manager = directory / "robot-manager-robot.service"
        manager.write_text("user change")
        with self.assertRaisesRegex(ConfigurationError, "edited management"):
            install_services(site, directory)
        self.assertEqual(manager.read_text(), "user change")

    def test_wheel_must_record_compatible_source_identity(self):
        wheel = self.root / "robot_deployment-fixture.whl"
        sources = dict(components={"robot_runtime": dict(commit="b" * 40)})
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr("unrelated", "fixture")
        with self.assertRaisesRegex(ValueError, "bootstrap"):
            wheel_identity(wheel, sources)
        identity = dict(schema_version=1, deployment_commit="a" * 40, runtime_commit="b" * 40)
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr("robot_deployment/_build_identity.json", json.dumps(identity))
        self.assertEqual(wheel_identity(wheel, sources), identity)
        sources["components"]["robot_runtime"]["commit"] = "c" * 40
        with self.assertRaisesRegex(ConfigurationError, "runtime revision differ"):
            wheel_identity(wheel, sources)
