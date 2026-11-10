# Deployment configuration and prepared perception

The installed `robot_deployment` package includes definitions under
`<environment>/share/robot_deployment`. An explicit definition root can be used
for a reviewed custom composition. References inside definitions are relative
to that root, with symlink resolution checked against it. Formats are version 1;
unknown keys, duplicate YAML keys, aliases and unsupported versions are rejected.

- `platforms/` declares the selected host family and video encoder. The Nano
  software encoder and fresh Nano/NX installs still need hardware qualification.
- `robot_models/` owns geometry, supported roles and the mounting/optical frame
  tree. The supplied example dimensions and transforms are **illustrative**,
  not a calibration of the existing car. Axes are x forward, y left, z up;
  the camera optical frame is x right, y down, z forward.
- `compositions/` selects the source lock, hardware variants, model descriptors,
  installed integrations and explicitly delegated parameters.
- `parameters/` supplies startup values for named nodes. A parameter has one
  default authority. Component bounds apply after workload requests are admitted.
- [site.example.yaml](../config/site.example.yaml) is a private host example.
  It contains account, paths, credential references, networking and allowed
  choices. It cannot override component revisions or individual engine paths.

The composition provides eight camera/model modes, including camera-only modes,
both individual overlays and the combined overlay. The selected site camera determines the default mode;
both models are enabled by default. A missing camera device ID requests exactly
one compatible device from the chosen provider. Ambiguity remains a provider
error; enumeration order is never a selector. An explicit session identity can
be declared under `hardware.front_camera.device_ids`, keyed by variant. An OAK
identity does not constrain D455 mode. Serial observations never update this file.
Camera replacement requires a new perception run; reconnect is not automatic.

The site `recording` mapping owns output location, managed history budget,
filesystem reserve, FPS ceiling, bitrates, segment duration and fixed depth
visualization range. Defaults and lifecycle semantics are in [recording.md](recording.md).
The sample site selects the explicit 720p30 camera profiles; existing profiles
remain available. Recording never changes the shared acquisition configuration.

An optional student workspace can provide `config/requests.yaml`. For the
supplied composition the only allowed key is `cones_score_threshold`, numeric
0.30–0.90, targeting the namespaced cone detector at startup. Missing requests
retain 0.50; unknown keys, booleans, nonfinite numbers and out-of-range values
fail preparation. To delegate another parameter, edit the trusted composition
and provide a default. Student-owned algorithm configuration stays in that
project. No policy implementation or recursive override merging is supplied.

Start and Restart call the deployment preparer through runtime's profile-owned
preparation interface. It reads each source once, validates final values, checks
installed model hashes, then writes effective node parameters, ROS parameter
JSON (also valid YAML), geometry and input provenance into a private candidate.
Runtime copies and verifies the candidate before changing lifecycle state. The
launcher reads only this accepted snapshot, supplied through neutral runtime run
context. Editing a request afterward cannot change the in-progress run. Runtime
associates the frozen reference with the run ID; credential contents are never
read by this path.

Student request and camera session identity changes may be prepared at the next
start/restart. Edit the managed site at `<data_root>/deployment/site.json` for
session identity changes; it is the live preparation input after selection.
Installed baseline parameter files are part of the verified release. Change those
defaults in the trusted definition source and stage a new release; do not edit
files under `releases/` in place. Changes to the site network, runtime structure,
definitions or source lock require a new release and stopped maintenance. Profile
generation derives SDK, ROS, Python, native video and model paths from one
release root, and validates through `robot_runtime.profile`.

The old JSON deployment example and historical evidence describe the preceding
integration. New tools use the YAML site schema. The tools under `tools/` are
thin adapters to the installed package, and no longer launch directly from
mutable legacy site JSON. Install the package into the intended Python
environment before using them.
