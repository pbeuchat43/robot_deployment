# Robot deployment implementation plan

Date: 3 November 2026

Current status (6 November): core implementation and prepared-host acceptance
are complete; Jah's permanent installation is recorded in
[the everyday deployment evidence](../evidence/2026-11-04-everyday/README.md).
The progress entries below are chronological and retain intermediate outcomes.
Fresh-image NX qualification remains open, Nano waits for available hardware,
and further operational robustness testing is deferred until more of the system
is complete. Revisit MCU recipes with the planned new Traxxas/IMU Pico firmware.
Consolidation into `dev` is authorized; publication and `main` promotion remain
later steps. See the design's
[current follow-ups](../design/2026-11-01-robot-deployment-design.md#acceptance-boundaries-and-remaining-decisions).

Local consolidation on 6 November preserves the intermediate histories in
`archive/2026-11-06-deployment-runtime` (runtime) and
`archive/2026-11-06-robot-deployment` (deployment). Runtime's consolidated `dev`
commit is `36249160ead1f4f9bf67ad7f6ccf8497f883b651`; the current source lock
selects it. Its only file differences from the verified `753ba24` selection are
README and verification-status documentation. The squash trees match their
archived feature tips; executable content and prior test evidence are preserved.

Jah remains on deployment `7a682ac` with runtime `753ba24`. Its installation
records and historical evidence retain those exact identities. This source
consolidation does not rebuild or redeploy that installation. Documentation links,
whitespace, source-pin identity and tree equivalence are checked; unchanged
execution tests are not repeated. No remote publication or `main` promotion is
part of this consolidation.

Implement the [agreed design](../design/2026-11-01-robot-deployment-design.md) in
the existing repository history, with shared runtime extensions in
robot_runtime. The user selected Solo: the primary agent implements, reviews
and integrates; bounded explorers supply read-only interface information.
Implementation and Jah software changes are authorized. Publication and main
promotion are outside this work. Video recording remains a separate milestone.

## Boundaries and baseline

- Deployment owns composition, host installation, launch preparation and the
  lucid_conduct CLI. Runtime owns lifecycle, policy and persistent state; it
  remains independently installable with neutral Python interfaces.
- JetPack 7.2.1 / L4T 39.2.1, Ubuntu 24.04 arm64, Python 3.12, ROS Jazzy,
  CUDA 13.2 and TensorRT 10.16.2 are the initial target. Actual package versions
  and module/carrier identities are recorded, not inferred from branding.
- Fetch exact source revisions and verified models. The accepted COCO path is
  pinned Ultralytics .pt -> isolated component-owned export -> verified ONNX ->
  target TensorRT engine. No model binaries are added to either repository.
- Installation never flashes the base image or starts application workloads.
  Firmware flashing is explicit and invokes component-owned target checks.
- Config formats are strict/versioned, student requests are explicitly mapped,
  and prepared snapshots are immutable for the lifetime of their run.
- CLI names stay in entry points, shell integration, help/examples and related
  checks. Services, state, configuration and Python implementation stay neutral.
- Preserve local unrelated work. Execution checks run on reserved Jah, with
  isolated files, ports, ROS domains and units. The user permits replacing or
  adjusting Jah's installed software; avoid unrelated changes without need.

Local starting identities: deployment b7f48b0, camera 0f4b829, detector 61219c6,
runtime 3ab1cd8. The deployment checkout was renamed from robot_composition to
robot_deployment on branch feat/robot-deployment; runtime work uses
feat/deployment-runtime. Keep meaningful intermediate commits.

Jah inspection: Orin NX 16GB reference module P3767-0000, L4T
39.2.1-20260806224157, Ubuntu 24.04.4, kernel 6.8.12-1021-tegra, Python 3.12.3,
CUDA cudart 13.2.86-1, TensorRT 10.16.2.10-1+cuda13.2. It already has a working
Jazzy installation and the prior runtime management services. An OAK-D and D455
are attached. Noninteractive sudo is unavailable; prepare concrete root actions
only if needed, while continuing user-space development. This is an existing
host, so success here alone cannot establish fresh Nano/NX qualification.

## Implementation tasks

### 1. Shared runtime operator interface

Files: robot_runtime/src/robot_runtime/cli.py, profile.py, pyproject.toml,
resources and current operator documentation; focused tests/test_cli.py.

- [x] Extract side-effect-free build_parser() and main(argv=None) with a reusable
  dispatch function. Keep existing standalone JSON/error semantics.
- [x] Provide underscore console entry points. Keep temporary legacy spellings
  for the currently supported installed release and document their status.
- [x] Add local profile catalog, identical log/logs aliases, unit or explicit-run
  log selection/follow, and convenient stop resolving one expected run.
- [x] Verify parser/help without IPC; log alias equivalence, historical/current
  selection, pinned follow and stale-stop rejection. Run existing relevant CLI,
  journal and profile checks on Jah.

### 2. Prepared start and coordinated restart

Files: robot_runtime/src/robot_runtime/prepared.py, core.py, supervisor.py,
manager.py, profile.py; tests/test_prepared.py, test_core.py and
integration_runtime.py; runtime integration/operator contracts.

- [x] Define a versioned prepared reference containing target unit, profile
  revision, selected mode and immutable input path/hash. The runtime treats
  component data as opaque, validates identity, persists acceptance and supplies
  the reference through neutral run context. Deployment is never imported.
- [x] Extend Core.command and its progress/reconciliation loop with restart.
  Persist old/new run IDs and stages; reserve the unit across completed stop and
  replacement dispatch. Reject concurrent mutations and stale run/profile
  identities. Do not replay uncertain dispatch after management recovery.
- [x] Keep invalid candidate failure before stopping. Revalidate immutable input
  identity before replacement; an uncertain/failed stop never permits a start.
  Report startup failure distinctly from supervisor acceptance/readiness.
- [x] Test candidate corruption/retargeting, source-file edits after preparation,
  stale run, concurrent operations, stop timeout, lost reply, manager recovery
  between stages and replacement failure. Run unit and native runtime suites;
  use existing browser checks for touched shared command semantics.

### 3. Deployment configuration and launch integration

Files: pyproject.toml; src/robot_deployment/{configuration,preparation,launch,
profile}.py; platforms/, robot_models/, compositions/, parameters/;
tools/{render_profile,launch_perception}.py; config/site.example.yaml;
tests/test_configuration.py and tests/test_preparation.py.

- [x] Install a neutral Python package with bundled versioned example data and
  explicit schema validation. Robot model owns geometry/roles; composition
  selects sources, named camera/model modes, parameter mappings and permissions;
  private site supplies allowed host choices and workspace bindings.
- [x] Resolve paths from declared roots, derive release SDK/model/runtime paths,
  reject unknown keys and unsupported schema versions. Validate finite typed
  values and grouped requirements; do not implement generic recursive merging.
- [x] Materialize immutable effective ROS configuration and provenance by reading
  each authorized input once. Admit only mapped workload keys/types/ranges.
  Supply snapshots for ordinary start and restart; no live source reread.
- [x] Preserve all six perception modes and overlays. Default device identity is
  empty for unique discovery; explicit role/session identity handles ambiguity
  without turning observed serials into a whitelist. Preserve source/calibration
  restart semantics and existing multiple-device runtime capabilities.
- [x] Test defaults, allowed requests, invalid/unknown keys, path boundaries,
  immutable snapshots, mount mapping, default unique discovery, explicit role
  selection and generated profile validation with the selected runtime.

### 4. Reproducible installation and component dependencies

Files: src/robot_deployment/{platform,artifacts,installation,components}.py,
sources.json, platform package data; component-owned build interface additions
only where needed; tests/test_artifacts.py and tests/test_installation.py.

- [x] Inspect/admit the declared platform and produce a concrete prerequisite
  package plan. Separate privileged host preparation from user-space builds;
  check package availability/version and do not silently upgrade the BSP.
- [x] Acquire exact Git commits and verify artifact hashes. Allow an explicitly
  supplied local source cache containing the same commits for unpublished work
  and private repositories; never change selected identities to make fetch pass.
- [x] Invoke camera SDK builders, pinned vision_msgs and the ROS/native build,
  runtime wheel installation, and model acquisition/export/target engine tools.
  Record inputs, commands, package identities, output hashes and failed stages.
- [x] Add a real component-owned native-video preparation path: obtain/build the
  pinned gst-plugins-rs WebRTC/Rust RTP plugins and matching GI/libnice support,
  validate plugins, and install an independent native prefix. The existing
  copy helper alone is insufficient. Select a supported encoder per platform.
- [x] Make reruns verify/reuse compatible completed stages and reject partial or
  corrupt outputs. Build in a staged release, validate installed artifacts and
  profile, then atomically select it. Write failed-attempt records as well.
- [x] Generate neutral management-service definitions and replacement-friendly
  USB permissions. Configure accounts/paths and optional management startup
  explicitly; leave camera/video/application workloads stopped.
- [x] Test wrong/missing hashes, unavailable sources, corrupt cache, interrupted
  stages, failed profile validation, ownership checks and release-selection
  atomicity. On Jah execute the real acquisition/export/build/install path using
  existing compatible host prerequisites and independent output directories.

### 5. Common CLI, completion and shell integration

Files: src/robot_deployment/{cli,shell,commands}.py, __main__.py, package entry
points; tests/test_cli.py and tests/test_shell.py; operator documentation.

- [x] Route install/config/info/doctor/build/flash/runtime/upgrade/rollback to
  owning Python functions. Runtime embeds the same parser and dispatch contract.
  Provide useful per-command help, machine output and propagated exit/signal
  behavior. Context resolves from explicit site/state or installation records.
- [x] Implement --show-call using actual route metadata, with no execution,
  device probing, build/network activity or credential contents.
- [x] Deliver Bash completion from the parser and installed local metadata.
  Optional lucid alias is opt-in, idempotent and conflict-aware; keep user shell
  content intact. Internal services/scripts use neutral module interfaces.
- [x] Test root/subcommand help, all routes, no-side-effect explanation/completion,
  both log spellings, context resolution, alias install/remove/rerun/conflict and
  executable-name isolation. Verify packaged entry points outside the source tree.

### 6. Maintenance and explicit auxiliary workflows

Files: src/robot_deployment/{maintenance,build,firmware}.py, selected component
recipes, tests/test_maintenance.py and tests/test_build.py; maintenance docs.

- [x] Upgrade stages an explicit selection and checks stopped workload ownership
  before switching management/profile/state. Rollback verifies host/runtime/state
  compatibility and restores only its declared release/configuration scope.
- [x] Provide explicit system/student colcon builds using configured underlays
  and workspace bindings, without using or adapting ai4r_policy.
- [x] Route selected firmware build/info/flash to component-owned interfaces with
  an exact target and manifest; preserve their board/protocol checks and prompts.
  Installation/build never invokes flashing. Unselected firmware reports how to
  declare a supported recipe rather than guessing a board or repository.
- [x] Test stale ownership, incompatible rollback, unowned files, changed inputs,
  failure records and workload-stopped state; exercise an isolated upgrade and
  rollback round trip on Jah. Firmware dispatch tests use stubs; no physical
  flash is required to establish correct orchestration.

### 7. Integration, records and handoff

- [x] Inspect the complete diff for spec coverage, stale ownership tables and
  unnecessary abstractions. Update current architecture links and guidance for
  the repository transition; retain historical evidence unchanged.
- [x] Build source distributions/wheels and execute applicable tests on reserved
  Jah, including installed CLI/native lifecycle and browser regression checks.
- [x] Exercise installed D455 perception/video with selected models,
  singleton discovery and an allowed parameter restart. Record measured results
  separately from synthetic checks and unobserved unplug/physical behavior.
- [x] Exercise installed OAK-D cones/COCO/both modes and viewer selections.
  After the operator reconnected OAK-D, all three modes and a further controlled
  D455-to-OAK selection change passed with both cameras attached.
- [x] Commit verified component changes, update deployment's exact pins and
  artifact identities, and record qualification limits. No remote publication or
  main promotion. Release the test reservation and leave workloads stopped.

## Verification focus and stop conditions

Highest-risk boundaries are immutable preparation versus concurrent lifecycle
operations; partial install versus release selection; source/package/model
identity versus mutable caches; path/managed-file ownership; and runtime/native
dependency relocation. Each has explicit checks in its owning task. Run required
applicable checks once for the relevant state; repeat only after new edits or
failures. A software pass does not establish physical reconnect, vehicle control,
fresh Nano qualification or observed laptop display performance.

If Jah requires root packages, prepare the exact script and explanation before
requesting the user's authentication step. If native builds expose incompatible
versions or resource limits, report evidence and resolve the smallest supported
change; do not replace JetPack or relax model/interface contracts silently.

## Progress and evidence

- Tasks 1–2 implemented in robot_runtime on feat/deployment-runtime. On reserved
  Jah, the installed wheel passed 169 unit tests; an additional restart API
  authorization case passed with all 17 web-unit tests. Native lifecycle passed
  10 checks, browser regression passed 6, and prepared restart passed its four
  integration checks. Each native report has empty cleanup_errors and stopped,
  empty workload state. Existing persistent management services were untouched.
- The preparation interface includes a profile-owned finite command, executed on
  an IPC worker, so CLI and browser Start/Restart use the same admission path.
  This closes the source-validation gap without making runtime import deployment.
- Jah's device-tree compatibility confirms reference carrier P3768-0000 with NX
  P3767-0000. GStreamer 1.24.2 is present, while several native-video build/runtime
  prerequisites are missing. Git access to the cone repository succeeds; exact
  commit/artifact acquisition is still part of the installer stage.
- Task 3's installed wheel passes 14 configuration/preparation checks on Jah,
  including all six generated modes through runtime validation, immutable
  snapshot/source edits, variant-scoped session identities, request bounds,
  symlink boundaries, grouped camera limits, corrupt model identity, and the
  real finite preparation subprocess. These are software checks, without cameras.
- Installer source/cache/stage/ownership checks subsequently passed with the
  configuration checks: 21 installed software tests in total. The reviewed host
  prerequisite script was applied by the operator; the missing GStreamer/native
  development and Python packages were verified. Exact component/cone sources
  were fetched and the isolated DepthAI build started. SSH then disconnected
  when the laptop slept. Jah was still unreachable after the reported reset;
  the outcome was unknown at that point. Later inspection confirmed completion
  of all nine stages, as recorded below.
- Tasks 4–6 have implementations for staging/selection, source and
  artifact identity, package plans, services, CLI/shell, workspace builds and
  optional firmware dispatch. The bootstrap builds committed deployment/runtime
  sources into a separate environment and embeds the deployment Git identity.
  No local execution-test substitute was used while Jah was unreachable.
- Current documentation describes the new layout, labels historical deployment
  evidence, and records the combined deployment ownership. Relative file links
  resolve in the nine edited/current documents and Git whitespace checks pass.
  Runtime documentation commit `753ba24` changed no runtime code and was selected
  for the verified installations. It retained the prior code evidence; native
  builder and end-to-end installer acceptance were established subsequently.
- After the operator restarted both machines, Jah was reachable and a new
  reservation was acquired. The retained first installation had completed all
  nine stages before reboot, including both SDKs, ROS, model export/engines,
  native video and configuration. Its records and artifacts were preserved.
- Bootstrap of deployment `edb8aac` succeeds on Jah and the installed package
  passes all 36 unit checks. A real interactive Bash check exposed an Ubuntu
  welcome-banner ambiguity; marked command-resolution output fixes it and the
  alias/completion check passes. Generated host scripts pass Bash syntax checks;
  the current prerequisite plan reports no missing packages. These generated
  account/repository scripts were not applied to this already prepared host.
- Real systemd maintenance passes four synthetic checks: management-only
  selection, live-workload refusal, stopped upgrade/rollback with history, and
  idempotent reselection/incompatible-state rejection. The native WebRTC browser
  suite passes 16 checks. Both reports have empty cleanup errors. Their code
  paths are unchanged by the shell lookup correction.
- The corrected full release began building in a new directory. The interrupted
  earlier candidate is retained with its logs. At that point the remaining gates
  were the final
  completed-release rerun/selection and system/student builds, followed by
  installed OAK-D/D455/video and parameter-restart acceptance. At that USB
  inspection only the D455 was attached; OAK-D needed reconnection.
- Final CLI contract completion adds detailed operational help, explicit JSON
  output, interpreter/context-aware call explanation and correct Bash filename
  fallback. The installed `3c73d66` package passes all 38 deployment checks and
  real terminal filename completion for the full command and alias. Runtime's
  two added maintenance unit checks also pass. The native build stays frozen at
  `edb8aac`; installation, preparation and launch code are unchanged. Subsequent
  operator checks use the final CLI against that release and record both source
  identities instead of rewriting provenance or repeating unchanged native builds.
- The corrected release completes all nine stages. Installed acceptance passes
  selection/rerun, final CLI metadata/integrity, real system build and student
  build/clean. Its first preflight exposed only a harness reader-size mistake,
  corrected before the passing run. Model export is reused from a verified cache;
  the first retained complete installation executed the original export.
- D455 cones, COCO and both modes pass with 100 individual exact-overlay samples,
  25 combined samples and six four-second browser windows (101–115 presentation
  callbacks). Dual selections preserve runs/generations and both inference paths.
  Invalid restart preserves the old process; valid restart applies frozen 0.6
  despite a later request edit to 0.7. Cleanup is fresh, empty and unblocked, with
  no task processes and no changes to earlier persistent workloads. Reservation
  released. OAK-D was unavailable during this first camera campaign.
  See the [verification record](../evidence/2026-11-03-deployment/README.md) and its
  redacted summary for exact identities and qualification limits.
- The operator then reconnected OAK-D. After acquiring a new reservation,
  OAK-D cones/COCO/both modes passed, followed by a D455-to-OAK both-model
  restart preserving the video run. All six modes are covered. Totals are 300
  individual exact samples, 100 combined samples and 20 viewer windows, with
  92–115 presentation callbacks per four-second window after source readiness.
  Each campaign passes frozen-parameter restart and cleanup. Final audit finds
  no remaining task process or workload ownership; request inputs are restored,
  earlier persistent workloads are unchanged and the new reservation is released.
