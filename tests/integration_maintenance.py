"""Real user-systemd selection/rollback with synthetic releases on reserved Jah.

Uses installed packages, a new private root and unique service names. Does not
build components, open hardware, enable boot services or alter existing runtimes.
"""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import argparse
import getpass
import json
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import uuid

from robot_runtime.auth import write_credential
from robot_runtime.common import Fault
from robot_runtime.ipc import request
from robot_runtime.profile import validate
from robot_deployment.configuration import ConfigurationError, Inputs, definition_root
from robot_deployment.maintenance import activate, current, rollback
from robot_deployment.platform import inspect
from robot_deployment.records import Attempt, claim, write_json
from robot_deployment import services


def wait_for(read, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            value = read()
            if value:
                return value
        except Fault as exc:
            if exc.code != "transport_unknown":
                raise
        time.sleep(.1)
    raise AssertionError("Timed out waiting for isolated runtime state")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="New private output directory on reserved Jah")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    root.mkdir(mode=0o700)
    token = uuid.uuid4().hex[:10]
    site = Inputs().read(definition_root() / "config/site.example.yaml")
    site.update(robot_id="maintenance-fixture", runtime_account=getpass.getuser(), runtime_namespace="m" + token)
    site["storage"] = dict(installation_root=str(root / "installation"), data_root=str(root / "data"))
    site["management"] = dict(start=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        web_port = listener.getsockname()[1]
    site["network"] = dict(hostname="localhost", media_address="127.0.0.1", web_host="127.0.0.1", web_port=web_port)
    site["credentials"] = dict(web_secret_file=str(root / "credential.json"),
        tls_certificate_file=str(root / "cert.pem"), tls_private_key_file=str(root / "key.pem"))
    write_credential(root / "credential.json", secrets.token_urlsafe(24))
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", root / "key.pem",
        "-out", root / "cert.pem", "-days", "1", "-subj", "/CN=localhost",
        "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (root / "key.pem").chmod(0o600)
    installation = claim(root / "installation", purpose="installation")
    records = claim(root / "data/deployment", purpose="records")
    (records / "installations").mkdir()
    state = root / "data/runtime"
    observed = inspect()
    revisions = {}
    for identity in ("first", "second", "incompatible"):
        release = installation / "releases" / identity
        attempt = Attempt(release, records / "installations" / (identity + ".json"), dict(synthetic_fixture=True, label=identity))
        shutil.copytree(definition_root(), release / "definitions")
        write_json(release / "site.snapshot.json", site)
        (release / "venv").symlink_to(Path(sys.prefix), target_is_directory=True)
        profile, revision = validate(dict(schema_version=1, robot_id=site["robot_id"], namespace=site["runtime_namespace"], units=[dict(
            id="fixture", label=identity, argv=["/bin/sleep", "300"], working_directory=str(root),
            environment={}, stop=dict(signal="SIGTERM", timeout_seconds=3), public_logs=True)]))
        revisions[identity] = revision
        write_json(release / "runtime.json", profile)
        write_json(release / "profile.identity.json", dict(config_revision=revision))
        write_json(release / "host.json", dict(packages={"nvidia-l4t-core": observed["packages"]["nvidia-l4t-core"]}))
        outputs = ["definitions", "site.snapshot.json", "venv", "runtime.json", "profile.identity.json", "host.json"]
        attempt.stage("synthetic-fixture", outputs, lambda: None)
        attempt.value.update(result="succeeded", state_schema=99 if identity == "incompatible" else 1)
        attempt.save()
    report = dict(passed=False, checks=[], cleanup_errors=[], synthetic=True, namespace=site["runtime_namespace"])
    directory = Path.home() / ".config/systemd/user"

    def status():
        return request(state, "status", fresh=True)

    def cli(*arguments):
        result = subprocess.run([sys.executable, "-m", "robot_deployment.cli", "runtime", "--state", state, *arguments],
                                check=True, text=True, capture_output=True, timeout=20)
        return json.loads(result.stdout)

    try:
        activate(site, "first")
        first = wait_for(lambda: value if (value := status())["fresh"] and value["config_revision"] == revisions["first"] else None)
        assert all(not unit["blocked"] for unit in first["units"])
        report["checks"].append("selection_starts_management_without_workloads")
        started = cli("start", "fixture")
        wait_for(lambda: status()["units"][0]["lifecycle"] == "running")
        try:
            activate(site, "second")
            raise AssertionError("Selection changed with an owned workload")
        except ConfigurationError as exc:
            assert "workloads or transitions remain" in str(exc), str(exc)
        assert current(site) == "first" and status()["units"][0]["run_id"] == started["run_id"]
        report["checks"].append("live_workload_blocks_selection_without_stopping_it")
        cli("stop", "fixture", "--expected-run", started["run_id"])
        wait_for(lambda: not status()["units"][0]["blocked"])
        activate(site, "second")
        assert current(site) == "second" and status()["config_revision"] == revisions["second"]
        rollback(site)
        final = status()
        assert current(site) == "first" and final["config_revision"] == revisions["first"]
        assert not final["units"][0]["blocked"] and final["units"][0]["run_id"] == started["run_id"]
        assert len(list((records / "selections").glob("*.sqlite3"))) == 3
        report["checks"].append("stopped_upgrade_rollback_preserves_history_without_replay")
        history = (records / "selection.json").read_bytes()
        assert activate(site, "first")["result"] == "unchanged"
        assert (records / "selection.json").read_bytes() == history
        try:
            activate(site, "incompatible")
            raise AssertionError("Incompatible state schema selected")
        except ConfigurationError as exc:
            assert "state compatibility" in str(exc), str(exc)
        assert current(site) == "first"
        report["checks"].append("idempotent_reselection_and_incompatible_state_rejection")
        report["passed"] = True
    except BaseException as exc:
        report["error"] = repr(exc)
        raise
    finally:
        try:
            if services.active(site):
                for unit in status()["units"]:
                    if unit["blocked"]:
                        cli("stop", unit["unit_id"], "--expected-run", unit["run_id"])
                wait_for(lambda: not any(unit["blocked"] for unit in status()["units"]))
                report["final_status"] = status()
                services.control("stop", site)
            assert not services.active(site)
            if (records / "services.json").exists():
                services.remove(site, directory)
                subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        except BaseException as exc:
            report["cleanup_errors"].append(repr(exc))
            report["passed"] = False
        write_json(root / "report.json", report)
        print(json.dumps(report, indent=2))
        if report["cleanup_errors"]:
            raise RuntimeError("Inspect isolated maintenance cleanup: " + str(root))


if __name__ == "__main__":
    main()
