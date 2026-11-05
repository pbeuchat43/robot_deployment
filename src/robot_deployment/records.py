"""Owned installation records and verified stage outputs."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import time
import uuid

from .configuration import encoded, file_digest, require


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name("." + path.name + "-" + uuid.uuid4().hex)
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded(value))
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def claim(root, *, purpose):
    root = Path(root)
    marker = root / ".robot-deployment.json"
    require(not root.is_symlink(), "Managed directory must not be a symlink: " + str(root))
    expected = dict(schema_version=1, purpose=purpose, root=str(root.resolve()), uid=os.geteuid())
    if marker.exists():
        require(json.loads(marker.read_text()) == expected, "Managed directory ownership mismatch: " + str(root))
    else:
        require(not root.exists() or not any(root.iterdir()), "Refusing to claim nonempty unowned directory: " + str(root))
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with marker.open("xb") as stream:
            stream.write(encoded(expected))
    require(root.stat().st_uid == os.geteuid(), "Managed directory belongs to another account")
    return root


@contextmanager
def locked(root):
    with (Path(root) / ".installation.lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another installation/maintenance operation owns this root") from exc
        yield


def inventory(root, outputs):
    root = Path(root).resolve()
    entries = {}
    for output in outputs:
        require(not Path(output).is_absolute() and ".." not in Path(output).parts, "Stage outputs must stay under the release")
        path = root / output
        require(path.exists() or path.is_symlink(), "Missing stage output: " + str(path))
        paths = [path, *path.rglob("*")] if path.is_dir() and not path.is_symlink() else [path]
        for item in paths:
            if "__pycache__" in item.parts or item.suffix == ".pyc":
                continue
            name = str(item.relative_to(root))
            if item.is_symlink():
                require(item.exists(), "Broken installed symlink: " + str(item))
                entries[name] = dict(kind="symlink", target=os.readlink(item))
            elif item.is_file():
                entries[name] = dict(kind="file", sha256=file_digest(item), size=item.stat().st_size,
                                     mode=item.stat().st_mode & 0o777)
            elif item.is_dir():
                entries[name] = dict(kind="directory")
            else:
                raise ValueError("Unsupported installed file type: " + str(item))
    return entries


class Attempt:
    def __init__(self, release, record, identity):
        self.release, self.record = Path(release), Path(record)
        self.identity = identity
        if self.record.exists():
            self.value = json.loads(self.record.read_text())
            require(self.value["identity"] == identity, "Attempt inputs changed; choose a new release ID")
        else:
            require(not self.release.exists(), "Unrecorded release directory exists; choose a new release ID")
            self.release.mkdir(parents=True, mode=0o700)
            self.value = dict(schema_version=1, release=str(self.release), identity=identity,
                              created_at=time.time(), result="in_progress", stages=[], application_workloads_started=False)
            self.save()

    def save(self):
        write_json(self.record, self.value)

    def stage(self, name, outputs, action):
        previous = next((stage for stage in self.value["stages"] if stage["name"] == name), None)
        if previous:
            require(previous["result"] == "succeeded", f"Stage {name} is partial/failed; choose a new release ID; retained record: {self.record}")
            require(inventory(self.release, outputs) == previous["artifacts"], f"Stage {name} outputs changed; refusing reuse")
            return
        stage = dict(name=name, result="in_progress", outputs=outputs, started_at=time.time())
        self.value["stages"].append(stage)
        self.save()
        try:
            action()
            stage.update(result="succeeded", artifacts=inventory(self.release, outputs), completed_at=time.time())
            self.save()
        except BaseException as exc:
            stage.update(result="failed", error=type(exc).__name__ + ": " + str(exc), completed_at=time.time())
            self.value["result"] = "failed"
            self.save()
            raise

    def verify(self):
        for stage in self.value["stages"]:
            require(stage["result"] == "succeeded" and inventory(self.release, stage["outputs"]) == stage["artifacts"],
                    "Release stage is incomplete or changed: " + stage["name"])
