"""Neutral, owned user-management units; never start application units."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import json
import os
from pathlib import Path
import subprocess
import sys

from .configuration import digest, require
from .records import write_json


def quote(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%").replace("$", "$$") + '"'


def names(site):
    namespace = site["runtime_namespace"]
    return ("robot-manager-" + namespace + ".service", "robot-web-" + namespace + ".service")


def templates(site):
    root = Path(site["storage"]["installation_root"])
    data = Path(site["storage"]["data_root"])
    python = root / "current/venv/bin/python"
    manager, web = names(site)
    network, credentials = site["network"], site["credentials"]
    origin_host = network["hostname"]
    manager_argv = [python, "-m", "robot_runtime.manager", "--profile", root / "current/runtime.json", "--state", data / "runtime"]
    web_argv = [python, "-m", "robot_runtime.web", "--state", data / "runtime", "--origin",
        f"https://{origin_host}:{network['web_port']}", "--bind", network["web_host"], "--port", str(network["web_port"]),
        "--credential", credentials["web_secret_file"], "--cert", credentials["tls_certificate_file"], "--key", credentials["tls_private_key_file"]]
    result = {}
    for name, argv in ((manager, manager_argv), (web, web_argv)):
        order = f"After={manager}\nWants={manager}\n" if name == web else ""
        result[name] = ("# Managed by robot_deployment; recorded ownership is required for updates.\n"
            "[Unit]\nDescription=Robot runtime management\n" + order + "\n[Service]\nType=simple\n"
            "ExecStart=" + " ".join(map(quote, argv)) + "\nRestart=on-failure\nRestartSec=2\nUMask=0077\n"
            "KillMode=control-group\nSendSIGKILL=no\nTimeoutStopSec=20\n\n[Install]\nWantedBy=default.target\n")
    return result


def install(site, directory):
    """Update only files whose previous recorded content is unchanged."""
    directory = Path(directory)
    record = Path(site["storage"]["data_root"]) / "deployment/services.json"
    previous = json.loads(record.read_text()) if record.exists() else {}
    contents = templates(site)
    directory.mkdir(parents=True, exist_ok=True)
    for name in contents:
        path = directory / name
        if path.exists() or path.is_symlink():
            require(not path.is_symlink() and previous.get(str(path)) == digest(path.read_bytes()),
                    "Unowned or edited management unit: " + str(path))
    backups = {name: (directory / name).read_bytes() if (directory / name).exists() else None for name in contents}
    changed = []
    temporaries = []
    updated = dict(previous)
    try:
        for name, content in contents.items():
            path = directory / name
            temporary = path.with_suffix(".service.tmp")
            require(not temporary.exists(), "Unexpected pending management file: " + str(temporary))
            with temporary.open("x") as stream:
                stream.write(content)
            temporaries.append(temporary)
        for name, content in contents.items():
            path = directory / name
            path.with_suffix(".service.tmp").replace(path)
            changed.append(name)
            updated[str(path)] = digest(content.encode())
        write_json(record, updated)
    except BaseException:
        for name in changed:
            path = directory / name
            require(path.read_bytes() == contents[name].encode(), "Management file changed during recovery: " + str(path))
            if backups[name] is None:
                path.unlink()
            else:
                path.write_bytes(backups[name])
        raise
    finally:
        for temporary in temporaries:
            temporary.unlink(missing_ok=True)


def remove(site, directory):
    record = Path(site["storage"]["data_root"]) / "deployment/services.json"
    previous = json.loads(record.read_text()) if record.exists() else {}
    for name in names(site):
        path = Path(directory) / name
        require(path.is_file() and not path.is_symlink() and previous.get(str(path)) == digest(path.read_bytes()),
                "Cannot remove an unowned or changed management file: " + str(path))
    for name in names(site):
        path = Path(directory) / name
        path.unlink()
        previous.pop(str(path))
    write_json(record, previous)


def verify_owned(site, directory):
    record = Path(site["storage"]["data_root"]) / "deployment/services.json"
    previous = json.loads(record.read_text()) if record.exists() else {}
    for name in names(site):
        path = Path(directory) / name
        observed = subprocess.run(["systemctl", "--user", "show", "--property=FragmentPath", "--value", name],
                                  text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.strip()
        if observed:
            require(Path(observed) == path and str(path) in previous, "Management name resolves to an unowned unit: " + name)
        if path.exists() or path.is_symlink():
            require(not path.is_symlink() and previous.get(str(path)) == digest(path.read_bytes()), "Unowned or changed management unit: " + str(path))


def control(action, site):
    subprocess.run(["systemctl", "--user", action, *names(site)], check=True, stdout=sys.stderr)


def active(site):
    return any(subprocess.run(["systemctl", "--user", "is-active", "--quiet", name]).returncode == 0 for name in names(site))
