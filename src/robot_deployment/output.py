"""Progress is separate from command results, including during foreground builds."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
from contextlib import contextmanager
from contextvars import ContextVar
import sys

from robot_runtime.output import emit as render

_structured = ContextVar("deployment_output_structured", default=True)


def emit(value, *, structured, **options):
    """Installation inventory stays in JSON; humans get provenance and stages."""
    if not structured and isinstance(value, dict) and isinstance(value.get("installation"), dict):
        record = value["installation"]
        identity = record.get("identity", {})
        value = dict(selected=value.get("selected"), installation=dict(
            recorded_result=record.get("result"), release=record.get("release"),
            deployment=identity.get("deployment"), platform=identity.get("platform"), kernel=identity.get("kernel"),
            application_workloads_started=record.get("application_workloads_started"),
            camera_and_viewer_acceptance=record.get("camera_and_viewer_acceptance"),
            stages=[dict(stage=stage["name"], result=stage["result"], artifacts=len(stage.get("artifacts", {})))
                    for stage in record.get("stages", [])]),
            details="Use --json for the complete provenance and artifact inventory; doctor checks current integrity")
    render(value, structured=structured, **options)


@contextmanager
def output_mode(*, structured):
    token = _structured.set(structured)
    try:
        yield
    finally:
        _structured.reset(token)


def progress(value):
    emit(value, structured=_structured.get(), compact=True, file=sys.stderr)
