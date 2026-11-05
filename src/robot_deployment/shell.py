"""Owned Bash integration; public command spelling is isolated in this adapter."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from .configuration import digest, require
from .records import write_json

COMMAND = "lucid_conduct"
ALIAS = "lucid"
BEGIN = "# BEGIN robot_deployment shell"
END = "# END robot_deployment shell"


def paths(home=None):
    home = Path(home or Path.home())
    config = home / ".config/robot_deployment"
    return dict(home=home, record=config / "shell.json", snippet=config / "shell.bash",
                executable=home / ".local/bin" / COMMAND, startup=home / ".bashrc")


def resolution(name, home):
    env = dict(os.environ, HOME=str(home))
    def query(expression):
        marker = "__ROBOT_DEPLOYMENT_LOOKUP__"
        script = "robot_lookup_value=$(" + expression + "); printf '\\n" + marker + "%s\\n' \"$robot_lookup_value\""
        result = subprocess.run(["bash", "--noprofile", "-ic", script], env=env,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
        lines = [line[len(marker):] for line in result.stdout.splitlines() if line.startswith(marker)]
        require(len(lines) == 1, "Interactive Bash did not complete command lookup; inspect its startup files")
        return lines[0]
    kind = query("type -t -- " + shlex.quote(name))
    value = query(("alias -- " if kind == "alias" else "type -P -- ") + shlex.quote(name)) if kind in ("alias", "file") else ""
    return dict(kind=kind, value=value)


def previous_record(locations, root):
    record = locations["record"]
    previous = json.loads(record.read_text()) if record.exists() else {}
    require(not previous or (previous.get("schema_version") == 1 and previous.get("installation_root") == str(root)),
            "Shell integration belongs to another installation; remove it through its owner first")
    for key in ("snippet", "executable"):
        path = locations[key]
        if path.exists() or path.is_symlink():
            require(not path.is_symlink() and previous.get(key + "_sha256") == digest(path.read_bytes()),
                    "Unowned or edited shell file: " + str(path))
    return previous


def hook_parts(startup, previous):
    text = startup.read_text() if startup.exists() else ""
    require(text.count(BEGIN) <= 1 and text.count(END) <= 1 and text.count(BEGIN) == text.count(END), "Ambiguous managed Bash startup block")
    if BEGIN not in text:
        require(not previous.get("hook"), "Recorded Bash hook was removed; inspect it before updating shell integration")
        return text, ""
    start = text.index(BEGIN)
    finish = text.index(END, start) + len(END)
    if text[finish:finish + 1] == "\n":
        finish += 1
    block = text[start:finish]
    require(block == previous.get("hook"), "Managed Bash hook was edited; preserving it")
    return text[:start], text[finish:]


def install(site, *, alias=False, home=None, probe=resolution):
    root = Path(site["storage"]["installation_root"])
    locations = paths(home)
    previous = previous_record(locations, root)
    before, after = hook_parts(locations["startup"], previous)
    full = probe(COMMAND, locations["home"])
    owned_commands = {str(locations["executable"]), str(root / "current/venv/bin" / COMMAND), str(Path(sys.executable).parent / COMMAND)}
    if full["kind"] and not (full["kind"] == "file" and full["value"] in owned_commands):
        return dict(installed=False, conflict=COMMAND, resolution=full, module_entry=str(root / "current/venv/bin/python") + " -m robot_deployment.cli")
    alias_conflict = None
    if alias:
        short = probe(ALIAS, locations["home"])
        if short["kind"] and not (short["kind"] == "alias" and short["value"] in (f"alias {ALIAS}='{COMMAND}'", f"alias {ALIAS}=\"{COMMAND}\"")):
            alias_conflict = short
            alias = False
    python = root / "current/venv/bin/python"
    wrapper = "#!/bin/bash\n# Managed by robot_deployment\nexec " + shlex.quote(str(python)) + " -m robot_deployment.cli \"$@\"\n"
    snippet = ("# Managed robot deployment completion and optional interactive convenience.\n"
        f"case \":$PATH:\" in *{shlex.quote(':' + str(locations['executable'].parent) + ':')}*) ;; *) export PATH={shlex.quote(str(locations['executable'].parent))}:$PATH ;; esac\n"
        "_robot_deployment_complete() {\n"
        "  mapfile -t COMPREPLY < <(" + shlex.quote(str(python)) + " -m robot_deployment.cli _complete -- \"${COMP_WORDS[@]:1:$COMP_CWORD}\")\n"
        "}\n" + f"complete -o bashdefault -o default -F _robot_deployment_complete {COMMAND}\n")
    if alias:
        snippet += f"alias {ALIAS}={shlex.quote(COMMAND)}\ncomplete -o bashdefault -o default -F _robot_deployment_complete {ALIAS}\n"
    hook = BEGIN + "\n[ ! -r " + shlex.quote(str(locations["snippet"])) + " ] || . " + shlex.quote(str(locations["snippet"])) + "\n" + END + "\n"
    if before and not before.endswith("\n"):
        before += "\n"
    for key, content in (("snippet", snippet), ("executable", wrapper)):
        path = locations[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    locations["executable"].chmod(0o755)
    locations["startup"].write_text(before + hook + after)
    record = dict(schema_version=1, installation_root=str(root), alias=alias, hook=hook,
        snippet_sha256=digest(snippet.encode()), executable_sha256=digest(wrapper.encode()))
    write_json(locations["record"], record)
    return dict(installed=True, alias=alias, alias_conflict=alias_conflict,
                load_in_current_shell="source " + shlex.quote(str(locations["snippet"])))


def remove(site, *, home=None):
    locations = paths(home)
    previous = previous_record(locations, Path(site["storage"]["installation_root"]))
    if not previous:
        return dict(removed=False, reason="No owned shell integration")
    before, after = hook_parts(locations["startup"], previous)
    locations["startup"].write_text(before + after)
    for key in ("snippet", "executable", "record"):
        locations[key].unlink(missing_ok=True)
    return dict(removed=True, current_shell="Open a new Bash session to clear previously loaded aliases/completion")
