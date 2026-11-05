# Deployment verification

Run execution checks only on reserved Jah. Use an isolated bootstrap/installed
environment, private directories, ROS domain, ports and runtime namespace.
Inspect existing workloads before any hardware operation. Do not run these
against an active persistent deployment.

From outside the source checkout, with the selected wheel installed:

```bash
env -u PYTHONPATH /absolute/venv/bin/python -m unittest discover \
  -s /absolute/robot_deployment/tests -v
env -u PYTHONPATH /absolute/venv/bin/python \
  /absolute/robot_deployment/tests/integration_maintenance.py \
  /absolute/new-private-maintenance-output
```

The maintenance check needs systemd user services, D-Bus/GLib bindings, OpenSSL
and the admitted Jetson host. Use a venv with system site packages for this
native check, as the installed release does. It creates synthetic releases and
unique management services, proves live-workload refusal and stopped upgrade/
rollback, and removes only its own service files. Retained records include
private credentials and state; publish only the redacted result report.
Require `passed: true`, empty `cleanup_errors` and final unblocked/empty workload
ownership. It is synthetic lifecycle evidence, not fresh-host or camera acceptance.

For a perception topic/remapping change, use a test venv with system site
packages so ROS's native Python dependencies are available, and install the
selected deployment/runtime wheels there. Source ROS Jazzy and the rebuilt
component workspace, then run the installed deployment package's launch check:

```bash
/absolute/venv/bin/python /absolute/robot_deployment/tests/integration_launch.py -v
```

It evaluates actual composable-node descriptions for all six modes and resolves
the detector output and combined inputs in a non-default namespace. The launch
service is intercepted before execution; no component, camera or GPU is started.
The detector's native `combined_overlay` test separately exercises these remaps
through actual ROS callbacks with synthetic captures.

Bootstrap must also be run from the selected clean Git commit on Jah. Check its
receipt, wheel/source distributions, installed source/assets, dependency consistency
and console help. The real installer exercises pinned acquisition, SDK/ROS builds,
model export/engines, native video and profile validation. Test a verified rerun
before selecting the candidate. Preserve failed attempts and their logs.

`integration_installed.py --site PRIVATE_SITE --release-id STAGED_RELEASE
--source-cache EXACT_CACHE --output NEW_PRIVATE_OUTPUT` exercises the completed
installer's selection/rerun, local CLI context and real system/student colcon
builds. Run it with the matching bootstrap interpreter. The site must use a
unique test namespace, stopped management, storage and an empty student workspace
under the output directory's parent. It installs only that namespace's management
unit files, leaves them stopped, and keeps command context under the test output.
Selection calls the neutral installation adapter in the matching bootstrap.
`--operator-python /absolute/venv/bin/python` can check a separately installed
CLI against that release; record both identities and preserve the release's
original build provenance. Other checks use the same interpreter by default.

For hardware acceptance, reuse `tools/integration_probe`, remapping its legacy
`detector` topics to `detector_cones` or `detector_coco`; use `combined_probe` in
both-model modes. Normal profiles need `marker:=false`. Probes release image
demand after their sample limit but still need SIGINT and process wait. Installed
camera and browser checks must record exact source/engine/profile identities,
separate measured results from software assertions, and finish with explicit
video/perception stop and fresh ownership inspection. Private imagery stays out
of source control.
