"""Stage verified component artifacts and select only complete robot releases."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import argparse
import json
import os
from pathlib import Path
import pwd
import shutil
import sys
import time
import uuid
import zipfile

from . import components
from .configuration import load, parameters, structure_identity, encoded, digest, file_digest, identifier, require
from .platform import package_plan
from .preparation import effective
from .profile import build_profile
from .records import Attempt, claim, locked, write_json


def copy_definitions(graph, destination):
    destination.mkdir()
    files = {Path(item["path"]) for item in graph["inputs"].sources if Path(item["path"]).is_relative_to(graph["root"])}
    files.update(graph["root"] / path for path in ("tools/with_ros.sh", "config/requirements-runtime.lock", "config/requirements-build.lock"))
    for path in files:
        output = destination / path.relative_to(graph["root"])
        output.parent.mkdir(parents=True, exist_ok=True)
        if path in graph["inputs"].raw:
            output.write_bytes(graph["inputs"].raw[path])
        else:
            shutil.copyfile(path, output)


def configure(graph, release, command):
    from robot_runtime.profile import validate
    from .services import templates
    site = graph["site"]
    installed = load(release / "site.snapshot.json", release / "definitions")
    managed_site = Path(site["storage"]["data_root"]) / "deployment/site.json"
    profile = build_profile(installed, managed_site, release, release / "runtime.json")
    validated, revision = validate(profile)
    write_json(release / "runtime.json", validated)
    for mode in validated["units"][0]["launch_modes"]:
        effective(load(release / "site.snapshot.json", release / "definitions"), release, mode["id"])
    write_json(release / "profile.identity.json", dict(config_revision=revision, structure_sha256=structure_identity(installed)))
    services = release / "services"
    services.mkdir()
    for name, text in templates(site).items():
        (services / name).write_text(text)
    checks = release / "build/service-check"
    checks.mkdir()
    for path in services.glob("*.service"):
        (checks / path.name).write_text(path.read_text().replace(str(Path(site["storage"]["installation_root"]) / "current"), str(release)))
    command(["systemd-analyze", "--user", "verify", *checks.glob("*.service")])
    # This imports/inspects factories only; it never creates a pipeline or camera.
    env = dict(os.environ, GST_PLUGIN_PATH=str(release / "av-native/gstreamer"),
        GST_REGISTRY=str(release / "build/check-gst-registry.bin"), ROBOT_AV_GI_OVERRIDES=str(release / "av-native/gi"))
    encoder = "nvv4l2h264enc" if graph["platform"]["encoder"] == "hardware" else "x264enc"
    command([release / "venv/bin/python", "-c",
        "from robot_runtime.av.gst_runtime import Gst; "
        "names=['webrtcsink','rtpgccbwe','nicesink','appsrc','videoconvert','h264parse','splitmuxsink','mp4mux','filesink'," + repr(encoder) + "]; "
        "missing=[name for name in names if Gst.ElementFactory.find(name) is None]; "
        "assert not missing, missing; print(names)"], env=env)
    command([release / "venv/bin/python", "-m", "robot_runtime.cli", "catalog", "--profile", release / "runtime.json"])


def locate_wheel(explicit=None):
    if explicit:
        return Path(explicit).resolve()
    candidates = sorted((Path(sys.prefix).parent / "wheels").glob("robot_deployment-*.whl"))
    require(len(candidates) == 1, "Provide --deployment-wheel from the bootstrap build, or invoke the installed release's command")
    return candidates[0]


def wheel_identity(wheel, sources):
    with zipfile.ZipFile(wheel) as archive:
        try:
            identity = json.loads(archive.read("robot_deployment/_build_identity.json"))
        except KeyError as exc:
            raise ValueError("Build the selected deployment wheel through tools/bootstrap.py so its Git identity is recorded") from exc
    import re
    require(identity.get("schema_version") == 1 and re.fullmatch(r"[0-9a-f]{40}", identity.get("deployment_commit", "")),
            "Deployment wheel has no supported source identity")
    require(identity.get("runtime_commit") == sources["components"]["robot_runtime"]["commit"],
            "Deployment wheel and selected runtime revision differ; bootstrap the selected release together")
    return identity


def install(site_path, *, definitions=None, deployment_wheel=None, source_cache=None, release_id=None,
            stage_only=False, service_directory=None):
    identity = release_id or ("r" + time.strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:12])
    identifier(identity, "release ID")
    # A failed validation still leaves an attempt record without echoing input contents.
    attempt_directory = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "robot_deployment/attempts"
    attempt_directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    audit_path = attempt_directory / (identity + "-" + uuid.uuid4().hex[:8] + ".json")
    audit = dict(schema_version=1, release_id=identity, result="in_progress", started_at=time.time(),
                 application_workloads_started=False)
    write_json(audit_path, audit)
    attempt = None
    try:
        graph = load(site_path, definitions)
        parameters(graph)
        require(pwd.getpwnam(graph["site"]["runtime_account"]).pw_uid == os.geteuid(),
                "Run user-space installation as the declared runtime account; prepare account/directories separately")
        wheel = locate_wheel(deployment_wheel)
        require(wheel.is_file(), "Deployment wheel is unavailable")
        deployment_identity = wheel_identity(wheel, graph["sources"])
        running_identity = Path(__file__).with_name("_build_identity.json")
        require(running_identity.is_file() and json.loads(running_identity.read_text()) == deployment_identity,
                "Run installation from the bootstrap environment built with this deployment wheel")
        host = package_plan(graph)
        require(not host["missing"], "Install the generated host prerequisite plan before building: " + ", ".join(host["missing"]))
        root = claim(Path(graph["site"]["storage"]["installation_root"]), purpose="installation")
        data = Path(graph["site"]["storage"]["data_root"])
        records = claim(data / "deployment", purpose="records")
        (data / "work").mkdir(parents=True, exist_ok=True, mode=0o700)
        (data / "runtime").mkdir(parents=True, exist_ok=True, mode=0o700)
        (root / "releases").mkdir(exist_ok=True)
        (root / "cache").mkdir(exist_ok=True)
        (records / "installations").mkdir(exist_ok=True)
        with locked(root):
            selected_identity = dict(structure=structure_identity(graph), site_sha256=digest(encoded(graph["site"])),
                sources_sha256=digest(encoded(graph["sources"])), deployment_wheel_sha256=file_digest(wheel),
                deployment=deployment_identity,
                host_packages=host["packages"], kernel=host["host"]["kernel"], platform=graph["platform"]["id"])
            release = root / "releases" / identity
            record = records / "installations" / (identity + ".json")
            if not record.exists():
                require(shutil.disk_usage(root).free >= 20 * 1024**3, "At least 20 GiB free space is required for isolated source builds")
            attempt = Attempt(release, record, selected_identity)
            selected = components.sources(graph, root / "cache/git", source_cache)
            command = components.Commands(release)
            frozen_wheel = release / "bootstrap" / wheel.name
            def freeze_selection():
                write_json(release / "sources.json", graph["sources"])
                write_json(release / "host.json", host)
                write_json(release / "site.snapshot.json", graph["site"])
                copy_definitions(graph, release / "definitions")
                frozen_wheel.parent.mkdir()
                shutil.copyfile(wheel, frozen_wheel)
                require(file_digest(frozen_wheel) == selected_identity["deployment_wheel_sha256"], "Deployment wheel changed during preparation")
            attempt.stage("sources", ["sources.json", "host.json", "site.snapshot.json", "definitions", "bootstrap"], freeze_selection)
            graph = load(release / "site.snapshot.json", release / "definitions")
            for name in ("depthai", "realsense"):
                print(json.dumps(dict(event="stage", stage="sdk-" + name)), flush=True)
                attempt.stage("sdk-" + name, ["sdk/" + name],
                    lambda name=name: components.sdk(name, selected["rgbd_camera"], release, command))
            attempt.stage("ros", ["ros/install"], lambda: components.ros_build(selected, release, command))
            attempt.stage("python", ["venv", "wheels"], lambda: components.python_environment(graph, selected, release, frozen_wheel, command))
            if graph["composition"].get("firmware"):
                from .firmware import provision
                attempt.stage("firmware-tools", ["firmware"], lambda: provision(graph, release, root / "cache/git", command, source_cache=source_cache))
            attempt.stage("model-inputs", ["model-inputs"], lambda: components.model_inputs(graph, selected, release, root / "cache/downloads", command))
            attempt.stage("engines", ["models"], lambda: components.engines(release, command))
            attempt.stage("native-video", ["av-native"], lambda: components.native(selected, release, root / "cache/downloads", command))
            attempt.stage("configuration", ["runtime.json", "profile.identity.json", "services"],
                          lambda: configure(graph, release, command))
            attempt.verify()
            attempt.value.pop("selected", None)  # Live selection belongs to selection.json/events.
            attempt.value.update(result="succeeded", completed_at=time.time(), state_schema=1,
                                 camera_and_viewer_acceptance="not_run")
            attempt.save()
        if not stage_only:
            from .maintenance import activate
            activate(graph["site"], identity, service_directory=service_directory)
        audit.update(result="succeeded", installation_record=str(record), release=str(release), selected=not stage_only)
        write_json(audit_path, audit)
        return dict(release=str(release), record=str(record), selected=not stage_only, application_workloads_started=False)
    except BaseException as exc:
        audit.update(result="failed", error=type(exc).__name__ + ": " + str(exc), completed_at=time.time())
        write_json(audit_path, audit)
        if attempt is not None and attempt.value["result"] != "succeeded":
            attempt.value.update(result="failed", error=audit["error"])
            attempt.save()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--definitions", type=Path)
    parser.add_argument("--deployment-wheel", type=Path)
    parser.add_argument("--source-cache", type=Path)
    parser.add_argument("--release-id")
    parser.add_argument("--stage-only", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(install(args.site, definitions=args.definitions, deployment_wheel=args.deployment_wheel,
                             source_cache=args.source_cache, release_id=args.release_id, stage_only=args.stage_only)))


if __name__ == "__main__":
    main()
