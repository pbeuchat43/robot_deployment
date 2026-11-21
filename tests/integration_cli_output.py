"""Installed CLI output over real IPC/systemd; synthetic workload, no hardware."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

from robot_runtime.common import Fault
from robot_runtime.ipc import request


def wait_for(read, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if value := read():
                return value
        except Fault as error:
            if error.code != "transport_unknown":
                raise
        time.sleep(.05)
    raise AssertionError("Timed out waiting for isolated CLI fixture")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="New private directory under /tmp on reserved Jah")
    root = parser.parse_args().root.resolve()
    assert root.parent == Path("/tmp") and root.name.startswith("robot-cli-output-native-")
    root.mkdir(mode=0o700)
    token = uuid.uuid4().hex[:10]
    state, profile = root / "state", root / "profile.json"
    profile.write_text(json.dumps(dict(schema_version=1, robot_id="output-fixture", namespace="o" + token,
        units=[dict(id="fixture", label="CLI output fixture", argv=[sys.executable, "-u", "-c",
            "import time; print('cli-output-fixture', flush=True); time.sleep(300)"],
            working_directory=str(root), environment={}, stop=dict(signal="SIGTERM", timeout_seconds=3), public_logs=True)])))
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    base = [sys.executable, "-m", "robot_deployment.cli", "runtime", "--state", str(state)]
    report = dict(passed=False, checks=[], cleanup_errors=[], namespace="o" + token)
    sequence = 0

    def invoke(arguments, *, structured=False, code=0):
        nonlocal sequence
        sequence += 1
        result = subprocess.run([*base, *arguments, *(["--json"] if structured else [])],
                                env=env, cwd=root, text=True, capture_output=True, timeout=15)
        (root / f"{sequence:02d}.stdout").write_text(result.stdout)
        (root / f"{sequence:02d}.stderr").write_text(result.stderr)
        assert result.returncode == code, (arguments, result.returncode, result.stderr)
        return result

    def status():
        return request(state, "status", fresh=True)

    def stream(arguments, *, structured):
        nonlocal sequence
        sequence += 1
        stdout, stderr = root / f"{sequence:02d}.stdout", root / f"{sequence:02d}.stderr"
        with stdout.open("w") as out, stderr.open("w") as err:
            child = subprocess.Popen([*base, *arguments, *(["--json"] if structured else [])],
                                     env=env, cwd=root, stdout=out, stderr=err)
            try:
                wait_for(lambda: stdout.stat().st_size > 0 or child.poll() is not None)
                assert child.poll() is None, stderr.read_text()
                time.sleep(.3)
                child.send_signal(signal.SIGINT)
                assert child.wait(timeout=5) == 0, stderr.read_text()
            finally:
                if child.poll() is None:
                    child.terminate()
                    child.wait(timeout=5)
        text = stdout.read_text()
        assert not stderr.read_text(), stderr.read_text()
        if structured:
            values = [json.loads(line) for line in text.splitlines()]
            assert values and all(isinstance(value, dict) for value in values)
        else:
            assert "--- Update ---" in text or "cli-output-fixture" in text
        report["checks"].append(" ".join(arguments) + (" JSON Lines" if structured else " human"))

    manager_log = (root / "manager.log").open("w")
    manager = subprocess.Popen([sys.executable, "-m", "robot_runtime.manager", "--profile", str(profile), "--state", str(state)],
                               env=env, cwd=root, stdout=manager_log, stderr=manager_log)
    try:
        wait_for(lambda: status()["fresh"])
        started = invoke(["start", "fixture"], structured=True)
        operation = json.loads(started.stdout)
        assert "Request ID: " + operation["request_id"] in started.stderr
        wait_for(lambda: status()["units"][0]["lifecycle"] == "running")
        wait_for(lambda: request(state, "logs", run_id=operation["run_id"], limit=10)["records"])
        for arguments, expected in ((["status", "--fresh"], "Unit id"),
                                    (["operation", operation["request_id"]], "Request id:"),
                                    (["inspect", operation["run_id"]], "Run id:"),
                                    (["catalog", "--profile", str(profile)], "Unit id"),
                                    (["logs", "fixture"], "cli-output-fixture"),
                                    (["resources"], "Fresh:")):
            assert expected in invoke(arguments).stdout
            assert isinstance(json.loads(invoke(arguments, structured=True).stdout), dict)
            report["checks"].append(" ".join(arguments[:1]) + " human and JSON")
        for arguments in (["watch"], ["resources", "--watch"], ["log", "fixture", "--follow"]):
            for structured in (False, True):
                stream(arguments, structured=structured)
        wait_for(lambda: request(state, "resource_status")["consumers"] == 0)
        for structured in (False, True):
            error = invoke(["inspect", "0" * 32], structured=structured, code=1)
            assert not error.stdout
            syntax = invoke(["start"], structured=structured, code=2)
            assert not syntax.stdout
            if structured:
                assert json.loads(error.stderr)["error"]["code"] == "not_found"
                assert json.loads(syntax.stderr)["error"]["code"] == "invalid_arguments"
            else:
                assert "Error [not_found]" in error.stderr
                assert "usage:" in syntax.stderr
        report["checks"].append("runtime and parser errors preserve stderr and exit codes")
        stopped = invoke(["stop", "fixture"])
        assert "Request ID:" in stopped.stderr and "Request id:" in stopped.stdout
        wait_for(lambda: not status()["units"][0]["blocked"])
        report["checks"].append("human stop retains lookup ID and exact owned run")
        report["passed"] = True
    except BaseException as error:
        report["error"] = repr(error)
        raise
    finally:
        try:
            if manager.poll() is None:
                for unit in status()["units"]:
                    if unit["blocked"]:
                        invoke(["stop", unit["unit_id"], "--expected-run", unit["run_id"]], structured=True)
                wait_for(lambda: not any(unit["blocked"] for unit in status()["units"]))
                report["final_status"] = status()
                report["resource_consumers"] = request(state, "resource_status")["consumers"]
                manager.terminate()
                manager.wait(timeout=8)
        except BaseException as error:
            report["cleanup_errors"].append(repr(error))
            report["passed"] = False
        finally:
            manager_log.close()
            (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        if report["cleanup_errors"]:
            raise RuntimeError("Inspect isolated CLI cleanup: " + str(root))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
