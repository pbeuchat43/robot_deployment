#!/usr/bin/env python3
"""Build the selected operator environment using only Python, Git and venv."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile
import time
import urllib.parse


def run(argv, *, cwd=None, capture=False):
    result = subprocess.run(list(map(str, argv)), cwd=cwd, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def snapshot(repository, commit, destination):
    """Export only committed paths; ignored build products never enter a wheel."""
    archive = destination.with_suffix(".tar")
    run(["git", "archive", "--format=tar", "--output", archive, commit], cwd=repository)
    destination.mkdir()
    try:
        with tarfile.open(archive) as source:
            source.extractall(destination, filter="data")
    finally:
        archive.unlink(missing_ok=True)


def runtime_source(selection, destination, source_cache):
    commit = selection["commit"]
    url = urllib.parse.urlsplit(selection["url"])
    require(re.fullmatch(r"[0-9a-f]{40}", commit), "Runtime selection requires a full Git commit")
    require(url.scheme == "https" and url.hostname and not url.username and not url.password,
            "Runtime source must use credential-free HTTPS")
    repository = source_cache / "robot_runtime" if source_cache else None
    bundle = source_cache / "robot_runtime.bundle" if source_cache else None
    if repository and repository.exists():
        run(["git", "clone", "--no-hardlinks", "--no-checkout", repository, destination])
    elif bundle and bundle.is_file():
        run(["git", "clone", "--no-checkout", bundle, destination])
    else:
        run(["git", "init", destination])
        run(["git", "remote", "add", "origin", selection["url"]], cwd=destination)
        run(["git", "fetch", "--depth", "1", "origin", commit], cwd=destination)
    run(["git", "checkout", "--detach", commit], cwd=destination)
    require(run(["git", "rev-parse", "HEAD"], cwd=destination, capture=True) == commit, "Runtime HEAD mismatch")
    require(not run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=destination, capture=True),
            "Runtime snapshot is modified")
    return destination


def bootstrap(source, destination, source_cache=None):
    require(sys.platform == "linux" and sys.version_info[:2] == (3, 12), "Use Linux Python 3.12 on the selected target")
    require(os.geteuid() != 0, "Run bootstrap as the intended runtime account, without sudo")
    source, destination = Path(source).resolve(), Path(destination).resolve()
    source_cache = Path(source_cache).resolve() if source_cache else None
    require(Path(run(["git", "rev-parse", "--show-toplevel"], cwd=source, capture=True)).resolve() == source,
            "Source must be the deployment repository root")
    require(not run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=source, capture=True),
            "Commit the selected deployment changes before bootstrapping")
    commit = run(["git", "rev-parse", "HEAD"], cwd=source, capture=True)
    require(not destination.is_relative_to(source), "Keep bootstrap outputs outside the source checkout")
    destination.mkdir(parents=True, mode=0o700)  # Never reuse or remove an existing bootstrap.
    record = dict(schema_version=1, result="in_progress", started_at=time.time(),
                  deployment_commit=commit, source_cache=str(source_cache) if source_cache else None,
                  application_workloads_started=False)
    record_path = destination / "bootstrap.json"

    def save():
        temporary = record_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
        temporary.replace(record_path)

    save()
    try:
        build = destination / "build"
        build.mkdir()
        deployment = build / "deployment"
        snapshot(source, commit, deployment)
        lock = json.loads((deployment / "sources.json").read_text())
        runtime = runtime_source(lock["components"]["robot_runtime"], destination / "runtime-source", source_cache)
        runtime_tree = build / "runtime"
        snapshot(runtime, lock["components"]["robot_runtime"]["commit"], runtime_tree)
        identity = dict(schema_version=1, deployment_commit=commit,
                        runtime_commit=lock["components"]["robot_runtime"]["commit"],
                        sources_sha256=sha256(deployment / "sources.json"))
        (deployment / "src/robot_deployment/_build_identity.json").write_text(json.dumps(identity, sort_keys=True) + "\n")
        record["source_identity"] = identity
        save()
        builder = build / "venv"
        run([sys.executable, "-m", "venv", builder])
        python = builder / "bin/python"
        run([python, "-m", "pip", "install", "-r", deployment / "config/requirements-build.lock"])
        wheels = destination / "wheels"
        wheels.mkdir()
        for tree in (runtime_tree, deployment):
            run([python, "-m", "build", "--sdist", "--wheel", "--no-isolation", "--outdir", wheels, tree])
        run([python, "-m", "pip", "download", "--only-binary=:all:", "--dest", wheels,
             "-r", deployment / "config/requirements-runtime.lock"])
        environment = destination / "venv"
        run([sys.executable, "-m", "venv", environment])
        python = environment / "bin/python"
        run([python, "-m", "pip", "install", "--no-index", "--find-links", wheels,
             "-r", deployment / "config/requirements-runtime.lock",
             *sorted(wheels.glob("robot_runtime-*.whl")), *sorted(wheels.glob("robot_deployment-*.whl"))])
        run([python, "-m", "pip", "check"])
        run([python, "-m", "robot_deployment.cli", "--help"], cwd=destination)
        record.update(result="succeeded", completed_at=time.time(),
                      artifacts={path.name: sha256(path) for path in sorted(wheels.iterdir()) if path.is_file()},
                      operator_python=str(python))
        save()
        print(json.dumps(dict(record=str(record_path),
            command=shlex.join([str(python), "-m", "robot_deployment.cli"]),
            source_cache=str(source_cache) if source_cache else None,
            host_changes_applied=False, application_workloads_started=False), indent=2))
    except BaseException as exc:
        record.update(result="failed", completed_at=time.time(), error=type(exc).__name__ + ": " + str(exc))
        save()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--destination", type=Path, required=True, help="New private bootstrap directory outside the checkout")
    parser.add_argument("--source-cache", type=Path, help="Exact local robot_runtime repository or robot_runtime.bundle")
    args = parser.parse_args(argv)
    bootstrap(args.source, args.destination, args.source_cache)


if __name__ == "__main__":
    main()
