"""Selection failure restores the previous release/configuration without replay."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
from contextlib import ExitStack
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from robot_deployment.configuration import ConfigurationError, Inputs, definition_root
from robot_deployment.maintenance import activate, audited_stopped, select_pointer
from robot_deployment.records import write_json
from robot_deployment.services import install as install_services


class MaintenanceTests(unittest.TestCase):
    def test_reselect_current_keeps_rollback_history_and_management(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = root / "releases/current-release"
            release.mkdir(parents=True)
            data = root / "data"
            (data / "deployment").mkdir(parents=True)
            history = data / "deployment/selection.json"
            write_json(history, dict(schema_version=1, current="current-release", previous="useful-previous"))
            before = history.read_bytes()
            select_pointer(root, "current-release")
            site = dict(storage=dict(installation_root=str(root), data_root=str(data)))
            with patch("robot_deployment.maintenance.verify_release", return_value=(release, dict(site=site))), \
                    patch("robot_deployment.maintenance.services.verify_owned"), \
                    patch("robot_deployment.maintenance.services.control", side_effect=AssertionError("No service change")), \
                    patch("robot_deployment.maintenance.audited_stopped", side_effect=AssertionError("No state transition")):
                result = activate(site, "current-release", service_directory=root / "services")
            self.assertEqual(result["result"], "unchanged")
            self.assertEqual(history.read_bytes(), before)

    def test_stale_or_owned_state_cannot_advance(self):
        site = Inputs().read(definition_root() / "config/site.example.yaml")
        for status in (dict(fresh=False, conflicts=[], units=[]), dict(fresh=True, conflicts=["foreign"], units=[]),
                       dict(fresh=True, conflicts=[], units=[dict(blocked=True)]),
                       dict(fresh=True, conflicts=[], units=[dict(blocked=False, transition_request_id="pending")])):
            with self.subTest(status=status), patch("robot_deployment.maintenance.request", return_value=status), self.assertRaises(ConfigurationError):
                audited_stopped(site, management_active=True)

    def test_failed_selection_restores_site_pointer_and_history(self):
        self.assert_selection_restored(pointer_failure=False)

    def test_pointer_sync_failure_restores_previous_pointer(self):
        self.assert_selection_restored(pointer_failure=True)

    def assert_selection_restored(self, *, pointer_failure):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root, data = home / "installation", home / "data"
            records = data / "deployment"
            records.mkdir(parents=True)
            (root / "releases/previous").mkdir(parents=True)
            candidate = root / "releases/candidate"
            candidate.mkdir()
            old = Inputs().read(definition_root() / "config/site.example.yaml")
            old["storage"] = dict(installation_root=str(root), data_root=str(data))
            old["management"]["start"] = False
            new = copy.deepcopy(old)
            new["management"]["start"] = True
            for key in new["credentials"]:
                path = home / key
                path.write_text("fixture")
                old["credentials"][key] = new["credentials"][key] = str(path)
            write_json(candidate / "profile.identity.json", dict(config_revision="candidate-revision"))
            write_json(records / "site.json", old)
            history = dict(schema_version=1, current="previous", previous="earlier")
            write_json(records / "selection.json", history)
            select_pointer(root, "previous")
            service_directory = home / "services"
            install_services(old, service_directory)
            with ExitStack() as patches:
                patches.enter_context(patch("robot_deployment.maintenance.verify_release", return_value=(candidate, dict(site=new))))
                patches.enter_context(patch("robot_deployment.maintenance.load", return_value=dict(site=old)))
                patches.enter_context(patch("robot_deployment.maintenance.services.verify_owned"))
                patches.enter_context(patch("robot_deployment.maintenance.services.active", return_value=False))
                patches.enter_context(patch("robot_deployment.maintenance.audited_stopped"))
                patches.enter_context(patch("robot_deployment.maintenance.subprocess.run"))
                if pointer_failure:
                    def replace_then_fail(root, release_id):
                        select_pointer(root, release_id)
                        if release_id == "candidate":
                            raise ValueError("fixture pointer sync failed")
                    patches.enter_context(patch("robot_deployment.maintenance.select_pointer", side_effect=replace_then_fail))
                else:
                    patches.enter_context(patch("robot_deployment.maintenance.start_management", side_effect=ValueError("fixture startup failed")))
                with self.assertRaisesRegex(ValueError, "fixture .* failed"):
                    activate(old, "candidate", service_directory=service_directory)
            self.assertEqual((root / "current").resolve().name, "previous")
            self.assertEqual(json.loads((records / "site.json").read_text()), old)
            self.assertEqual(json.loads((records / "selection.json").read_text()), history)
            event = json.loads(next((records / "selections").glob("*.json")).read_text())
            self.assertEqual(event["result"], "failed")
            self.assertTrue(event["previous_selection_restored"])
            self.assertFalse(event["application_workloads_started"])
