"""Audited, stopped selection of a complete release; rollback has the same guard."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from robot_runtime.common import Fault
from robot_runtime.ipc import request
from robot_runtime.maintenance import STATE_SCHEMA, stopped

from .configuration import load, require
from .platform import admit, inspect, package_version
from .records import Attempt, locked, write_json
from . import services


def current(site):
    root = Path(site["storage"]["installation_root"])
    pointer = root / "current"
    if not pointer.exists() and not pointer.is_symlink():
        return None
    require(pointer.is_symlink(), "Current release path is unowned; expected a managed symlink")
    resolved = pointer.resolve()
    require(resolved.parent == root.resolve() / "releases" and resolved.is_dir(), "Invalid selected release reference")
    return resolved.name


def release_record(site, release_id):
    from .configuration import identifier
    identifier(release_id, "release ID")
    root = Path(site["storage"]["installation_root"])
    record = Path(site["storage"]["data_root"]) / "deployment/installations" / (release_id + ".json")
    require(record.is_file(), "No installation record for selected release: " + release_id)
    value = json.loads(record.read_text())
    require(value.get("schema_version") == 1 and value.get("result") == "succeeded", "Release is not a completed compatible installation")
    require(value.get("release") == str(root / "releases" / release_id), "Release record targets another installation root")
    require(value.get("state_schema") == STATE_SCHEMA, "Runtime state compatibility differs; rollback cannot migrate it")
    return value, record


def verify_release(site, release_id):
    value, record = release_record(site, release_id)
    release = Path(value["release"])
    Attempt(release, record, value["identity"]).verify()
    graph = load(release / "site.snapshot.json", release / "definitions")
    for key in ("storage", "runtime_account", "runtime_namespace", "robot_id"):
        require(graph["site"][key] == site[key], "Release cannot change installation identity or state binding: " + key)
    admit(graph["platform"], inspect())
    recorded_host = json.loads((release / "host.json").read_text())
    mismatches = [name for name, version in recorded_host["packages"].items() if package_version(name) != version]
    require(not mismatches, "Release host packages changed; application rollback cannot undo apt: " + ", ".join(mismatches))
    if graph["site"]["visual_odometry"]["enabled"]:
        from .odometry import artifact
        artifact(graph, release, check_available=True)
    return release, graph


def audited_stopped(site, *, management_active):
    state = Path(site["storage"]["data_root"]) / "runtime"
    try:
        status = request(state, "status", fresh=True)
    except Fault as exc:
        if exc.code != "transport_unknown" or management_active:
            raise
        return None  # The exclusive runtime-owned offline guard must still pass.
    require(status["fresh"] and not status["conflicts"], "Supervisor ownership is stale or conflicting; resolve through runtime before maintenance")
    require(not any(unit["blocked"] or unit.get("transition_request_id") for unit in status["units"]),
            "Application workloads or transitions remain owned; stop/resolve them before maintenance")
    return status


def select_pointer(root, release_id):
    root = Path(root)
    temporary = root / (".select-" + uuid.uuid4().hex)
    try:
        temporary.symlink_to(Path("releases") / release_id, target_is_directory=True)
        temporary.replace(root / "current")
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def start_management(site, revision):
    manager, web = services.names(site)
    for path in site["credentials"].values():
        require(Path(path).is_file(), "Management startup requires configured credential/TLS files: " + path)
    subprocess.run(["systemctl", "--user", "start", manager], check=True, stdout=sys.stderr)
    deadline = time.monotonic() + 15
    state = Path(site["storage"]["data_root"]) / "runtime"
    while time.monotonic() < deadline:
        try:
            status = request(state, "status", fresh=True)
            if status["fresh"] and status["config_revision"] == revision:
                require(not status["conflicts"] and not any(unit["blocked"] for unit in status["units"]), "Unexpected workload ownership after selection")
                break
        except Fault as exc:
            if exc.code != "transport_unknown":
                raise
        time.sleep(.2)
    else:
        raise ValueError("Management service did not confirm the selected profile")
    subprocess.run(["systemctl", "--user", "start", web], check=True, stdout=sys.stderr)
    # User services start asynchronously; an immediate systemctl acceptance is recorded
    # as management startup, not browser readiness or observed application performance.


def activate(site, release_id, *, service_directory=None):
    root = Path(site["storage"]["installation_root"])
    records = Path(site["storage"]["data_root"]) / "deployment"
    state = Path(site["storage"]["data_root"]) / "runtime"
    directory = Path(service_directory) if service_directory else Path.home() / ".config/systemd/user"
    with locked(root):
        release, graph = verify_release(site, release_id)
        candidate_site = graph["site"]
        previous_id = current(site)
        services.verify_owned(site, directory)
        if previous_id == release_id:
            # A verified rerun must not replace the useful rollback predecessor
            # with itself, restart management, or overwrite editable session IDs.
            return dict(schema_version=1, action="select", result="unchanged", release_id=release_id,
                        application_workloads_started=False)
        previous_site = load(root / "releases" / previous_id / "site.snapshot.json",
                             root / "releases" / previous_id / "definitions")["site"] if previous_id else None
        running = services.active(site)
        audited_stopped(site, management_active=running)
        start_after = candidate_site["management"]["start"] or running
        if start_after:
            for path in candidate_site["credentials"].values():
                require(Path(path).is_file(), "Prepare the configured credential/TLS files before management startup: " + path)
        event = dict(schema_version=1, action="select", previous_release=previous_id, release_id=release_id,
                     result="in_progress", started_at=time.time(), application_workloads_started=False,
                     rollback_scope="application release and managed site; no apt, firmware or image reversal")
        events = records / "selections"
        events.mkdir(exist_ok=True)
        event_path = events / (str(time.time_ns()) + ".json")
        write_json(event_path, event)
        managed_site = records / "site.json"
        previous_bytes = managed_site.read_bytes() if managed_site.exists() else None
        selection_path = records / "selection.json"
        previous_selection = selection_path.read_bytes() if selection_path.exists() else None
        switched = False
        configuration_changed = False
        try:
            if running:
                services.control("stop", site)
            with stopped(state, backup=events / (event_path.stem + ".sqlite3")) as evidence:
                event["runtime"] = evidence
                services.install(candidate_site, directory)
                configuration_changed = True
                write_json(managed_site, candidate_site)
                # Replacing the pointer can succeed before directory fsync fails.
                # Recovery must restore it even when the call itself raises.
                switched = True
                select_pointer(root, release_id)
                write_json(selection_path, dict(schema_version=1, current=release_id, previous=previous_id))
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, stdout=sys.stderr)
            if start_after:
                revision = json.loads((release / "profile.identity.json").read_text())["config_revision"]
                start_management(candidate_site, revision)
            event.update(result="succeeded", completed_at=time.time(), management_started=start_after)
            write_json(event_path, event)
            return event
        except BaseException as exc:
            event.update(result="failed", error=type(exc).__name__ + ": " + str(exc), completed_at=time.time())
            try:
                if configuration_changed:
                    if services.active(candidate_site):
                        services.control("stop", candidate_site)
                    with stopped(state):
                        if switched:
                            if previous_id:
                                select_pointer(root, previous_id)
                            else:
                                (root / "current").unlink(missing_ok=True)
                        if previous_bytes is not None:
                            write_json(managed_site, json.loads(previous_bytes))
                        else:
                            managed_site.unlink(missing_ok=True)
                        if previous_site:
                            services.install(previous_site, directory)
                        else:
                            services.remove(candidate_site, directory)
                        if previous_selection is not None:
                            write_json(selection_path, json.loads(previous_selection))
                        else:
                            selection_path.unlink(missing_ok=True)
                    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, stdout=sys.stderr)
                if running and previous_site:
                    old_revision = json.loads((root / "releases" / previous_id / "profile.identity.json").read_text())["config_revision"]
                    start_management(previous_site, old_revision)
                event["previous_selection_restored"] = True
            except BaseException as recovery:
                event.update(previous_selection_restored=False, recovery_error=type(recovery).__name__ + ": " + str(recovery))
            finally:
                write_json(event_path, event)
            if not event["previous_selection_restored"]:
                raise RuntimeError("Selection failed and recovery requires inspection: " + str(event_path)) from exc
            raise


def rollback(site, release_id=None, *, service_directory=None):
    if release_id is None:
        record = Path(site["storage"]["data_root"]) / "deployment/selection.json"
        require(record.is_file(), "No previous release selection is recorded")
        release_id = json.loads(record.read_text()).get("previous")
        require(release_id is not None, "No previous release is available")
    return activate(site, release_id, service_directory=service_directory)
