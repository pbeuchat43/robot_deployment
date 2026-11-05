"""Small adapters from public routes to their explicit implementation owners."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import json
import os
from pathlib import Path

from .configuration import Inputs, load, parameters, require, structure_identity


def context_path():
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "robot_deployment/context.json"


def resolve_site(explicit=None, *, optional=False):
    if explicit:
        return Path(explicit).resolve()
    if os.environ.get("ROBOT_DEPLOYMENT_SITE"):
        return Path(os.environ["ROBOT_DEPLOYMENT_SITE"]).resolve()
    context = context_path()
    if context.is_file():
        value = Inputs().read(context)
        require(value.get("schema_version") == 1 and set(value) == {"schema_version", "site"}, "Unsupported installation context")
        return Path(value["site"])
    require(optional, "Provide --site for the first installation, or load the installed shell context")
    return None


def graph_for(explicit=None, definitions=None):
    path = resolve_site(explicit)
    if definitions is None:
        value = Inputs().read(path)
        current = Path(value["storage"]["installation_root"]) / "current/definitions"
        definitions = current if current.is_dir() else None
    return load(path, definitions)


def runtime_argv(argv, explicit=None):
    if any(arg == "--state" or arg.startswith("--state=") for arg in argv):
        return argv
    path = resolve_site(explicit, optional=True)
    if path is None:
        return argv  # Standalone runtime defaults still work independently.
    site = Inputs().read(path)
    return ["--state", str(Path(site["storage"]["data_root"]) / "runtime"), *argv]


def local_catalog(explicit=None):
    path = resolve_site(explicit)
    site = Inputs().read(path)
    from robot_runtime.profile import validate
    profile = Path(site["storage"]["installation_root"]) / "current/runtime.json"
    return validate(json.loads(profile.read_text()), check_paths=False)[0]["units"]


def config(site_path=None, definitions=None, *, action, release=None, output=None):
    graph = graph_for(site_path, definitions)
    nodes, requests = parameters(graph)
    if action == "show":
        return dict(site=graph["site"], effective_parameters=nodes, admitted_requests=requests)
    if action == "render":
        from .profile import render
        return dict(config_revision=render(resolve_site(site_path), release, output, root=graph["root"]), output=str(output))
    from .preparation import effective
    for camera in ("oak", "d455"):
        effective(graph, Path("/not-installed"), camera + "-both", check_artifacts=False)
    return dict(valid=True, composition=graph["composition"]["id"], platform=graph["platform"]["id"],
                structure_sha256=structure_identity(graph), admitted_requests=requests)


def install(site_path=None, definitions=None, *, no_shell=False, **kwargs):
    from .installation import install as perform
    result = perform(resolve_site(site_path), definitions=definitions, **kwargs)
    if result["selected"]:
        graph = graph_for(site_path, definitions)
        from .records import write_json
        context = context_path()
        context.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        managed = Path(graph["site"]["storage"]["data_root"]) / "deployment/site.json"
        write_json(context, dict(schema_version=1, site=str(managed)))
        if not no_shell:
            from .shell import install as install_shell
            result["shell"] = install_shell(graph["site"], alias=graph["site"]["shell"]["alias"])
    return result


def host(site_path=None, definitions=None, *, action, output):
    from .platform import package_plan, prerequisite_script, repository_script
    output = Path(output)
    if action == "repositories":
        with output.open("x") as stream:
            stream.write(repository_script())
        return dict(script=str(output), applied=False)
    graph = graph_for(site_path, definitions)
    if action == "setup":
        from .host_setup import script
        with output.open("x") as stream:
            stream.write(script(graph["site"]))
        return dict(script=str(output), applied=False)
    plan = package_plan(graph)
    with output.open("x") as stream:
        json.dump(plan, stream, indent=2)
    with output.with_suffix(".sh").open("x") as stream:
        stream.write(prerequisite_script(plan))
    return dict(plan=str(output), script=str(output.with_suffix(".sh")), missing=plan["missing"], applied=False)


def info(site_path=None, definitions=None, *, action, target=None):
    if action == "host":
        from .platform import inspect
        return inspect()
    graph = graph_for(site_path, definitions)
    if action == "mcu":
        from .firmware import info as firmware_info
        return firmware_info(site_path, definitions, target=target)
    from .maintenance import current, release_record
    selected = current(graph["site"])
    return dict(selected=selected, installation=release_record(graph["site"], selected)[0] if selected else None)


def doctor(site_path=None, definitions=None):
    graph = graph_for(site_path, definitions)
    parameters(graph)
    from .maintenance import current, verify_release
    from .services import active
    selected = current(graph["site"])
    require(selected is not None, "No completed release is selected")
    verify_release(graph["site"], selected)
    # Unlike maintenance, a doctor may find live workloads; report their status.
    from robot_runtime.ipc import request
    from robot_runtime.common import Fault
    state = Path(graph["site"]["storage"]["data_root"]) / "runtime"
    try:
        status = request(state, "status", fresh=True)
    except Fault as exc:
        if exc.code != "transport_unknown":
            raise
        status = dict(available=False, reason="Management is not responding", service_active=active(graph["site"]))
    return dict(installed_integrity="passed", release=selected, runtime=status, camera_probe="not_run")


def rollback(site_path=None, definitions=None, *, release_id=None):
    from .maintenance import rollback as perform
    return perform(graph_for(site_path, definitions)["site"], release_id)


def shell(site_path=None, definitions=None, *, action, alias=False):
    from .shell import install, remove
    site = graph_for(site_path, definitions)["site"]
    return install(site, alias=alias) if action == "install" else remove(site)
