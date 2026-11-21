# Deployment verification

Run execution checks only on reserved Jah. Use an isolated bootstrap/installed
environment, private directories, ROS domain, ports and runtime namespace.
Inspect existing workloads before any hardware operation. Do not run these
against an active persistent deployment.

## CLI output checks

`test_output.py` and `test_cli_shell.py` cover all deployment families, nested
human output, `--json` at each command level, runtime forwarding, replayable
`--show-call`, progress separation, errors/exit codes, Pico watch and uncertain
mode results. `test_output.py` also exercises a real harmless child process to
check stdout/stderr separation. Runtime's `test_output.py` covers all standalone
command families, legacy JSON defaults, explicit modes, all five streaming
paths, log gaps/empty polls, parser errors and pre-submit recovery IDs.

Run both installed unit suites on Jah after building the paired wheels. Use
runtime `integration_runtime.py` for real IPC/status/watch/error/lifecycle checks
and deployment `integration_maintenance.py` for the `--json` consumer and stopped
selection/rollback checks. Preserve their cleanup reports. These are synthetic
software checks; no camera, Pico, ESC or persistent deployment is operated.
`integration_cli_output.py /tmp/robot-cli-output-native-UNIQUE` adds actual
human/JSON subprocess reads, finite status/resource/log streams, SIGINT exit
codes, runtime/parser faults and recovery IDs against its own manager and idle
workload. Require `passed: true`, empty `cleanup_errors`, zero
`resource_consumers`, and an unblocked final status with no member processes.
`integration_installed.py` now captures stderr separately and parses the entire
stdout document, so mixed progress fails instead of being skipped. It still
requires a separately admitted completed release and real build prerequisites.

## Other deployment checks

When integrating a new camera, use the component-owned
[camera-adapter qualification checklist](https://github.com/pbeuchat43/rgbd_camera/blob/dev/docs/adapter-qualification.md)
alongside these installed checks. It covers profile capabilities, geometry,
clock/VO/VIO recovery, full workloads and physical acceptance. Extend the current
OAK/D455 fixture selections for each admitted adapter; existing hardware evidence
does not qualify the planned ZED 2i or Orbbec integration.

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

It evaluates actual composable-node descriptions for all 24 admitted modes on
both installed backends and resolves
the detector output and combined inputs in a non-default namespace. The launch
service is intercepted before execution; no component, camera or GPU is started.
The detector's native `combined_overlay` test separately exercises these remaps
through actual ROS callbacks with synthetic captures.

`integration_odometry.py --site PRIVATE_SITE --release PRIVATE_CANDIDATE --output
NEW_PRIVATE_OUTPUT --mode oak-cones-vio --warmup 15 --seconds 60` runs a finite
stationary camera/estimator fixture through the installed runtime. It retains
capture/pose latency samples, same-epoch previous/current RGB pose coverage,
with an actual pose-bracket width of at most 50 ms, per-minute peaks and explicit
cleanup. Camera errors, expired health observations and premature run exit fail
the fixture even if it produced samples earlier. `passed` denotes fixture completion;
compare the recorded metrics separately with the fixed feasibility gates.
Status freshness is evaluated at the timestamp captured immediately after the
final ROS spin, before summary computation; the report retains that timestamp
and the camera/odometry ages. Report-generation time does not age the frozen
measurement snapshot, and the original expiry limits remain in force.
The private report retains camera/session/calibration identities; redact them
before publishing a summary.
`--record` adds RGB/depth/annotated recording; `--wait-video` waits for an external
finite viewer to confirm decoded frames via `OUTPUT/video-ready` before timing.
The viewer must use the fixture's runtime state and stop when
`OUTPUT/measurement-complete` appears. Never use a personal browser profile.

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
