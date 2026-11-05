"""Exact sources and content-addressed downloads; no implicit substitution."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import os
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request
import uuid

from .configuration import require, file_digest


def run(argv, *, cwd=None, env=None, capture=False):
    result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def download(url, checksum, cache):
    require(re.fullmatch(r"[0-9a-f]{64}", checksum) is not None, "Declare a complete SHA-256")
    require(url.startswith("https://") and "@" not in url.split("/", 3)[2], "Use a credential-free HTTPS artifact URL")
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / checksum
    if destination.exists():
        require(destination.is_file() and file_digest(destination) == checksum, f"Corrupt cached artifact: {destination}")
        return destination
    temporary = cache / (".download-" + uuid.uuid4().hex)
    try:
        with urllib.request.urlopen(url, timeout=90) as response, temporary.open("xb") as output:
            shutil.copyfileobj(response, output)
            output.flush()
            os.fsync(output.fileno())
        require(file_digest(temporary) == checksum, f"Artifact hash mismatch: {url}")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def verify_source(path, commit):
    require(run(["git", "rev-parse", "HEAD"], cwd=path, capture=True) == commit, f"Source HEAD mismatch: {path}")
    require(not run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=path, capture=True), f"Modified source cache: {path}")


def acquire_git(name, selection, cache, *, source_cache=None):
    commit, url = selection["commit"], selection["url"]
    require(re.fullmatch(r"[a-z][a-z0-9_-]*", name) is not None, "Invalid component name")
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, f"{name}: declare a full Git commit")
    require(url.startswith("https://") and "@" not in url.split("/", 3)[2], "Source URL must be credential-free HTTPS")
    root = Path(cache)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / (name + "-" + commit)
    if destination.exists():
        verify_source(destination, commit)
        return destination
    temporary = root / (".source-" + uuid.uuid4().hex)
    try:
        local = Path(source_cache) / name if source_cache else None
        bundle = Path(source_cache) / (name + ".bundle") if source_cache else None
        if local and local.exists():
            run(["git", "clone", "--no-hardlinks", "--no-checkout", local, temporary])
        elif bundle and bundle.exists():
            run(["git", "clone", "--no-checkout", bundle, temporary])
        else:
            run(["git", "init", temporary])
            run(["git", "remote", "add", "origin", url], cwd=temporary)
            run(["git", "fetch", "--depth", "1", "origin", commit], cwd=temporary)
        run(["git", "checkout", "--detach", commit], cwd=temporary)
        verify_source(temporary, commit)
        temporary.rename(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return destination
