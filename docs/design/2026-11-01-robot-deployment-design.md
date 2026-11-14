# Robot deployment design draft

Date: 1 November 2026
Updated: 6 November 2026

Status: Core implementation completed and verified on the existing Jah NX host;
the permanent installation was selected on 4 November. Scope, evidence and
deferred qualification are recorded in the
[implementation plan](../plans/2026-11-03-robot-deployment.md).

Copyright (c) 2026 Paul N. Beuchat. MIT License.

## Purpose and agreed direction

robot_deployment will describe a robot system and provide the tools to install,
build, configure and maintain it. Composition and installation belong in this
one repository, with separate internal responsibilities. robot_runtime remains
an independently installable repository for operating the installed system.

The primary installation use case is a fresh Jetson Orin Nano or Orin NX running
JetPack 7.2.1 / Jetson Linux 39.2.1. This is the selected initial base platform;
the complete robot installation still needs fresh-host qualification on each
declared module/carrier profile. Flashing the Jetson base image and initial
storage provisioning are outside the installer scope.

Composition describes vehicle geometry, permitted component makes/models,
component roles, software selections, runtime units, YAML wiring and the
configuration changes a student workload may request. Like-for-like hardware
replacement must not require editing a serial-number whitelist.

The public command is lucid_conduct: lucid_conduct install, lucid_conduct runtime,
lucid_conduct build, lucid_conduct flash and lucid_conduct info. Installation can
optionally add lucid as a Bash alias. These names identify only the shell-facing
CLI; repositories, Python packages, configuration, services and default UI labels
retain neutral robot terminology. Renaming the CLI must not require a data,
configuration or runtime-protocol migration.

Video recording remains an early, separate milestone: manual RC driving,
laptop viewing, and simultaneous plain and annotated video. Its implementation
does not wait for completion of this deployment design. Observer design,
MCAP/CSV, replay, viewer-stall investigation and adaptation of ai4r_policy are
outside this work.

robot_deployment evolves the existing robot_composition Git repository,
preserving its history, source selections and integration evidence. The local
checkout was renamed at the start of authorized implementation on 3 November
2026. Update its README, repository guidance and affected current path references
on implementation branches. No remote is configured; future publication should
use robot_deployment. Remote publication and promotion of main remain separate
actions. Historical evidence retains its original repository identity.

## Baseline inspected before implementation

This section records the pre-implementation baseline. The additions proposed
against it are now implemented where covered by the
[3 November verification](../evidence/2026-11-03-deployment/README.md) and
[4 November permanent deployment](../evidence/2026-11-04-everyday/README.md).
The old CLI limitations and explicit camera-ID configuration below describe
that baseline, not the current implementation.

The inspected baseline is composition b7f48b0, selecting camera 0f4b829,
detector 61219c6 and runtime 3ab1cd8 through [sources.json](../../sources.json).
The recorded persistent release uses runtime 0.1.0.dev22. This is a recorded
deployment identity, not a fresh inspection of the running host.

| Area | Implemented at the baseline | Additions designed in this document |
| --- | --- | --- |
| Composition | Camera configurations, six camera/model combinations, launch topology, runtime profile generation and integration evidence. | Vehicle descriptions, explicit parameter-source/delegation contracts, replacement-friendly selection and a complete installation input contract. |
| Installation | Component-owned SDK builders, ROS builds, detector export/engine tools and runtime wheel installation. | Coordinated fresh-host preparation, artifact acquisition, installation records, upgrade and recovery tooling. |
| Runtime CLI | Python commands for status, watch, start, stop, resolve, logs, operation lookup, inspect, resources, validation, credentials and ROS operations. | Unified lucid_conduct routing, completion, catalog, convenient stop/log addressing, identical log/logs aliases and coordinated restart. |
| Runtime compatibility | Runtime profile validation, guarded run operations and persistent state. | Explicit compatibility between deployment definitions and selected runtime features. |
| Hardware | Finite OAK-D/D455 integration and exact-overlay evidence. | A verified fresh-install matrix for Nano/NX and replacement acceptance. |

The runtime CLI is real, but it is not a verbatim replacement for the old
dream runtime CLI. In particular, restart, catalog and recover are not current
top-level CLI verbs; logs currently addresses a run ID, and stop requires an
expected run ID. The existing resolve command has specific missing-ownership
semantics and must not simply be relabeled as general recovery. These are current
implementation facts, not requirements to retain inconvenient operator syntax;
the desired runtime behavior is specified below.

The camera already permits an empty device_id and requires one available device
within its selected backend before validating compatibility. The current
composition instead supplies explicit IDs from its site file. Default
replacement-friendly selection therefore requires composition changes and an
audit of permissions and any registry checks, not a new camera owner.

The historical research architecture names separate composition and installer
repositories. This design replaces that repository split, while retaining the
logical ownership boundaries. Existing evidence and historical provenance remain
intact.

## Repository and execution boundaries

| Owner | Responsibility |
| --- | --- |
| robot_deployment composition | Robot designs and geometry, supported hardware variants, exact software/model selections, launch wiring, parameter sources, delegated overrides and integration acceptance. |
| robot_deployment installation | Host prerequisites, selected source/artifact acquisition, build orchestration, configuration materialization, maintenance, installation records and rollback coordination. |
| robot_deployment command entry point | Common command routing, deployment context and presentation of results from the owning implementation. |
| robot_runtime | Runtime profile schema, process ownership, lifecycle, command policy, runtime state, observations, browser/API behavior and media coordination. |
| Components | Algorithms, drivers, public parameter contracts, validation, discovery, build/install interfaces, diagnostics and firmware procedures. |
| Student/workload project | Workload code, its own tuning, and requested values for explicitly delegated system parameters. |

Deployment depends on supported component/runtime interfaces. Runtime must not
import vehicle-specific deployment configuration or require robot_deployment to
operate independently. A deployment launcher can run under runtime supervision
just as another declared workload does.

Routine pin or configuration changes should not require installer logic changes.
A genuinely new build interface, host capability or configuration feature may
require coordinated changes within robot_deployment. A new runtime feature is
implemented in robot_runtime and deliberately selected by deployment.

The neutral architecture document should ultimately live with robot_deployment,
with component documents linking to it instead of maintaining competing ownership
tables.

## Configuration ownership

These are conceptual responsibilities, not a requirement for an elaborate stack
of files or a generic recursive YAML merge engine.

| Information | Authority and persistence |
| --- | --- |
| Component parameter definitions | Component-owned types, units, validation and generic defaults. |
| Robot model | Versioned dimensions, coordinate conventions, nominal mounting transforms and supported component roles/variants. |
| Composition | Versioned selection of robot model, software, capabilities, units, parameter sources, permissions and defaults. |
| Private site configuration | Host account, robot identity, storage, networking, credential references and explicitly permitted installation-specific choices. |
| Calibration | Values from the authority that measured that device or relationship, with subject and provenance. |
| Workload-requested configuration | Student/workload-owned tuning and requests within composition's explicit delegation. |
| Installation record | Generated historical record of an installation attempt and its resulting artifacts. |
| Run record | Runtime identity plus effective per-run parameter provenance and observed device identities. |

Private site configuration is not an unrestricted override layer. It can select
declared hardware variants and profiles; it cannot silently replace component
revisions, model contracts or invariant limits. Credentials are referenced and
managed separately, rather than embedded in these records.

An installation root is an operator choice. Individual SDK, Python, ROS and
engine paths are derived from the selected release layout. Operators should not
need to copy a list of build-directory paths from a previous machine.

Robot geometry has one source for each fact. For example, wheelbase is defined
once and mapped to any relevant consumer; it is not separately maintained in
several node YAML files. Device-internal calibration remains component-owned.
Mount geometry belongs to the robot configuration or selected mount calibration.

### Device selection, replacement and reconnection

Composition names a role, supported variants and required capabilities. The
chosen variant selects its adapter. Launch-time discovery binds the actual
attached device:

- One compatible, unambiguous candidate can be used without a configured serial.
- No candidate produces a specific unavailable/incompatible result.
- Multiple indistinguishable candidates require a role distinction, such as
  supported physical-port mapping; enumeration order is never the tie-breaker.
- Actual identities are reported and may be used for session exclusivity. They
  do not become persistent launch whitelists merely because they were observed.
- Component firmware/protocol requirements remain applicable to replacements.
- Device-specific calibration is reloaded or re-established for the replacement.

The normal robot has one camera. That case needs no identity configuration or
general device registry. Preserve existing multiple-camera and multiple-gamepad
capability and useful tests. Where several matching devices serve different
roles, require explicit role binding through a supported physical-port mapping
or an explicit session selection; do not bind by enumeration order. The first
implementation uses each provider's discovery/selection interfaces and reports
unsupported mappings rather than claiming a general role selector.

Replacement means stopping/replacing/restarting the affected ownership group.
It does not promise uninterrupted hot-swapping. The current detector binds a
source identity for its run, so replacing its camera requires restarting the
shared perception run, not just changing a serial in a live process.

Loss and reconnection are separate from role selection. The current camera
contract reports terminal device loss and requires an explicit restart; it does
not automatically reconnect. The initial behavior must:

- Report device loss clearly, and stop presenting old frames, detections or
  control samples as fresh.
- Rediscover the selected role after replug or like-for-like replacement on an
  explicit restart; ambiguity still fails rather than choosing another device.
- Create a new camera/perception session, reload that device's calibration and
  rebind dependent processing to the new source identity.
- Define gamepad loss and reconnection in the gamepad/control owner: discard old
  inputs and require explicit re-establishment of control before actuation can
  resume. Preserve any more restrictive existing control contract.

Automatic camera reconnection can be added deliberately later, with the same
identity, freshness and calibration requirements. Multiple-device support and
clear unplug/replug behavior are requirements; a general registry redesign is
not a prerequisite for the single-camera installation.

For MCU flashing, one actual target must be identified and its board/firmware
compatibility checked for that operation. That transactional selection does not
imply a permanent serial requirement for normal robot operation. A blank MCU is
not yet a compatible, programmed replacement.

### YAML sources and student permissions

Composition explicitly maps named YAML sources to runtime units and ROS nodes.
The mapping identifies allowed keys or groups, types, units, bounds or referenced
component validators, defaults, and whether changes are startup-only or live.

Student-owned node tuning belongs to the student project. A request affecting a
system-owned node is admitted only through the composition's declared mapping.
Missing optional requests use the declared default. Unknown, malformed or
out-of-contract requests fail specifically; they are not silently ignored.
Related fields are validated together where their relationship matters.

Component invariants apply to the final values regardless of the source.
Composition may narrow a permissible range but cannot relax component/firmware
invariants. This admission policy governs the supported launch path; it is not
an operating-system sandbox for arbitrary programs.

Preparing a run reads each authorized source once, validates it, and produces an
immutable effective parameter snapshot. The nodes consume that snapshot, so an
edit during launch cannot give different nodes different interpretations.
Source identities/hashes and the resulting parameter identity are associated
with the run. Secret contents are excluded.

This work occurs on explicit launch preparation, not only during installation.
Editing a permitted startup parameter therefore needs a restart, not a software
rebuild or reinstall. Changing the runtime unit/profile structure remains a
stopped maintenance operation under runtime's existing contract.

A deployment-owned launch entry point can perform this preparation before opening
hardware. The existing supervisor already supplies ROBOT_RUNTIME_RUN, which can
associate the preparation record with the actual runtime run. Preparation
failure exits visibly without starting the component graph. Supervisor start
acceptance still does not establish application readiness. For restart, prepare
before stopping the old run and pass the accepted snapshot through the handoff
below; the replacement must not re-read the editable request files.

## Installation and maintenance

Installation starts from the selected, already-flashed JetPack 7.2.1 image.
Each platform profile identifies the module/carrier, base image, driver/BSP and
accelerator stack. The existing source file's Ubuntu/ROS/CUDA/TensorRT
observations are evidence inputs, not fresh-image qualification.

### Selected base platform: JetPack 7.2.1

The following is the NVIDIA-published baseline checked on 3 November 2026, not
an observation of a newly installed robot. BSP means board support package:
the board-specific kernel, boot support, drivers and firmware.

| Item | Selected baseline and evidence boundary |
| --- | --- |
| JetPack / BSP | JetPack 7.2.1 with Jetson Linux / L4T 39.2.1 GA. |
| Operating system | Ubuntu 24.04 rootfs, aarch64 / Debian arm64, Linux kernel 6.8. Record the installed kernel build and package revisions. |
| Accelerator stack | CUDA 13.2.2, cuDNN 9.20.0 and TensorRT 10.16.2. Record exact installed package/runtime versions and GPU identity. |
| Python | Python 3.12 is the expected Ubuntu 24.04 environment; its exact installed patch/build must be observed during qualification. |
| ROS | Retain the selected ROS 2 Jazzy stack as an installer dependency. It is not supplied merely by choosing JetPack. |
| Camera dependencies | Retain DepthAI 3.9.0 and librealsense 2.56.5 with the RSUSB backend from sources.json; qualify their component-owned builders on this fresh platform. |

NVIDIA's [release notes](https://docs.nvidia.com/jetson/archives/r39.2.1/ReleaseNotes/Jetson_Linux_Release_Notes_r39.2.1.pdf)
establish the OS/BSP/architecture, and its
[JetPack version table](https://developer.nvidia.com/embedded/jetpack/downloads)
establishes the compute versions. This aligns with the recorded CUDA 13.2 and
TensorRT 10.16.2.10 family, but does not prove that all installed packages match.
Do not infer generic SBSA package compatibility for Orin from the Thor-specific
SBSA guidance. Isaac ROS is listed as coming soon for this JetPack release; it
is not an installation prerequisite for the existing ROS pipeline.

NVIDIA documents these Nano/NX module combinations with its P3768-0000 reference
carrier in the [module/configuration table](https://docs.nvidia.com/jetson/archives/r39.2.1/DeveloperGuide/IN/QuickStart.html#jetson-modules-and-configurations):

| Module | NVIDIA identifier | Documented target storage |
| --- | --- | --- |
| Orin Nano 8GB developer module | P3767-0005 | microSD, USB or NVMe |
| Orin Nano 8GB / 4GB production modules | P3767-0003 / P3767-0004 | USB or NVMe |
| Orin NX 16GB / 8GB production modules | P3767-0000 / P3767-0001 | USB or NVMe |

The listed BSP configurations are jetson-orin-nano-devkit and its super variant,
including for NX. This vendor support table does not declare every combination
qualified for our robot workloads. A custom carrier needs its vendor's compatible
BSP/configuration and separate qualification; module name alone is insufficient.

Base-image preparation is an external prerequisite. The
[Nano quick start](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/quick_start.html)
uses the Jetson ISO written to a USB installer, which installs onto the target
storage. JetPack 7.2+ has no Nano SD-card image. The developer kit requires the
JetPack 6.x-generation UEFI/QSPI preparation path before using the ISO; follow
the release-specific firmware prerequisites and capsule-update prompts. The
release notes exclude a direct capsule update from BSP 36.2, so a generic 36.x
version check alone is insufficient for that older image. The ISO
defaults Nano to the Super flashing configuration. Record the chosen flash
configuration and observed power mode; the robot installer does not change them.
Other modules/carriers use the corresponding supported SDK Manager or BSP/initrd
flashing procedure. Preserve the exact image URL/checksum and flashing record
when preparing a qualification host; no image was downloaded or flashed here.

Package acquisition uses the release-matched NVIDIA repositories and Ubuntu
24.04 arm64 sources. NVIDIA's
[package guide](https://docs.nvidia.com/jetson/archives/r39.2.1/DeveloperGuide/SD/SoftwarePackagesAndTheUpdateMechanism.html)
lists repo.download.nvidia.com/jetson/common and /jetson/som with suite r39.2.
That suite can advance to a newer point release, so its name is not an exact
package lock. The installation recipe must resolve and record selected versions
and reject unavailable or incompatible selections instead of silently upgrading
the BSP. A bootable BSP-only install may still need compute/development packages;
check installed capabilities rather than assuming the image contains every SDK.
Use the current version table and target package metadata where older examples
in the package guide disagree. ROS packages, OpenCV, build tools and component
dependencies need their own declared sources and compatible versions.

Fresh-host qualification must capture module/carrier and firmware identities,
OS/L4T/kernel/Python, GPU/driver/CUDA/TensorRT package identities, package sources,
required disk space and the actual build/install results. Verify the selected
camera SDKs, ROS/native ABI combination and target engine builder on Nano and NX.
Do not substitute a different JetPack release or upgrade the working robot to
resolve a qualification gap. Camera/viewer performance and video recording remain
separate hardware acceptance; Nano and NX must not be assumed to have identical
encoding capabilities or throughput.

### Installation flow

The installer:

1. Validates composition, site settings, platform and required artifact sources.
2. Checks existing workloads and managed-file ownership before changes.
3. Prepares declared host packages, accounts, permissions and directories.
4. Fetches verified selections and invokes supported component build/install
   interfaces, reusing compatible artifacts where available.
5. Generates concrete launch/runtime configuration and validates it through the
   owning components/runtime.
6. Records results and selects the completed release. Application workloads
   remain stopped; management-service startup follows the declared policy.

The source lock selects exact revisions. Baseline/history fields are provenance,
not alternative revision selectors. Model inputs are acquired from the selected
external repositories with full content hashes, as described below.

Model descriptors and export/engine validation remain detector-owned. Deployment
selects them and invokes those interfaces. Target-built engines have recorded
hashes and compatibility manifests; identical source selection does not imply
identical binary engines on different GPUs. Launch never downloads or builds.

Installation does not silently upgrade the base image, flash devices, select
newer components or change the robot's power/network policy. Firmware flashing
is a separate explicit command, even when its tools are installed by installation.

Upgrades stage a coherent replacement and perform changes requiring stopped
workloads only after ownership is resolved. Old release files and compatible
configuration/state recovery information are retained. Runtime owns state
compatibility and migration rules.

Rollback must describe its scope. Switching an application release does not undo
arbitrary apt transactions, firmware writes or a base-image change. A release
whose host prerequisites or state cannot support reversal must report that
limitation before replacement. Retrying installation preserves unrelated work and
data and verifies reusable outputs instead of assuming their presence proves
validity.

### Model acquisition and provenance

The agreed distribution policy is to retrieve the cone ONNX and the Ultralytics
YOLOv8n checkpoint from external sources with exact identities and SHA-256
verification, then export the checkpoint through rgbd_object_detector. Do not add model
binaries to robot_deployment or rgbd_object_detector as part of this work. A
release/tag or Git commit locates an artifact; its content hash verifies the
bytes. Store source URL/revision/path, content hash, detector descriptor identity
and relevant licence/provenance references in the selection and installation
record. Do not use mutable branch heads, latest releases or an interchangeable
model merely because it predicts the same classes.

| Selected input | Source identity | SHA-256 |
| --- | --- | --- |
| Cone ONNX | oakd_gpu_cone_detector, commit 5907560cb7a3c5f5df43a9a792243bdee1ce010f, models/cones.onnx | dcf4d911dee975944a3cca895d92803c3181d8dba670759276c4d71901c8040d |
| YOLOv8n COCO80 upstream checkpoint | ultralytics/assets, release v8.3.0, yolov8n.pt | f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36 |
| Selected normalized COCO80 ONNX | Output of the pinned detector-owned export procedure | 3bd80055fc88933446e2d6d4a7ed346caf65f35bd881fd8b2452924d521bf71d |

The cone repository's configured remote is
https://gitlab.unimelb.edu.au/dream/oakd_gpu_cone_detector.git. Fetch the pinned
revision and retrieve only the required model/provenance inputs; installing the
legacy detector is unnecessary. The local ONNX hash was verified for this draft.
The detector NOTICE also cites a GitHub location for this repository, but remote
retrieval from either location was not verified here. Qualification must confirm
the selected revision is available to the intended installer account and record
one working exact source. If authentication is required, use existing credential
handling without putting credentials in tracked URLs or records. Do not silently
substitute another mirror or revision.

The [Ultralytics v8.3.0 assets](https://github.com/ultralytics/assets/releases/expanded_assets/v8.3.0)
provide the selected yolov8n.pt checkpoint. Downloading that checkpoint and
performing the required export is the accepted installation path. No external
ONNX hosting or further search for an ONNX download is required.

The existing reproducible preparation route downloads the
[official checkpoint](https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt),
verifies it, then invokes the detector's
[controlled export](../../../rgbd_object_detector/docs/model-profiles.md#pinned-general-baseline-and-export).
It uses isolated Python 3.12 with the component's locked environment: Ultralytics
8.3.0, PyTorch 2.5.1, torchvision 0.20.1 and ONNX 1.17.0; opset 17, static
640x640 batch-one FP32 input, no simplification and no NMS. The exporter normalizes
date metadata and metadata ordering, validates the tensor contract and records
the output hash. Artifact preparation must additionally compare that hash with
the selected ONNX hash above. The installer creates an isolated build environment
for this export and caches the verified result for reuse. Export dependencies
are build-time requirements; ordinary robot execution does not require the
checkpoint/export environment. A compatible, hash-verified cached ONNX can avoid
repeating the export. The installer then invokes the detector's target engine
builder using the selected descriptor and records the complete conversion chain.

Downloaded or cached bytes must pass the same hash and component validation
before use. A missing artifact or hash mismatch fails with its source and remedy,
without starting workloads or selecting a partial release. TensorRT engines are
built for the target through the detector-owned builder; their recorded hashes
need not match across Nano and NX.

Retain the [detector NOTICE](../../../rgbd_object_detector/NOTICE.md) and upstream
model-specific terms. External acquisition does not resolve the cone record's
conflicting AGPL-3.0 checkpoint metadata and historical MIT attribution. It does
not assign either repository's MIT licence to the weights or derived engines.
Clarifying that provenance remains separate from selecting the acquisition path;
this design neither relocates nor newly republishes the models.

## Command interface and name isolation

The common lucid_conduct entry point belongs to robot_deployment. Its runtime
branch delegates to robot_runtime. The optional lucid alias expands to this same
entry point; it has no separate parser or behavior. The standalone command will
be named robot_runtime, using the user's underscore convention. It remains
available without deployment, and uses the same runtime parsing and application
logic. Management-service entry points remain independently packageable.

The currently shipped command is robot-runtime, declared in pyproject.toml as
the console entry point robot_runtime.cli:main. The repository and Python import
package already use robot_runtime. This draft proposes renaming the executable,
not the Python implementation. Related entry points should use the same
convention: robot_runtime_manager, robot_runtime_web and robot_runtime_av.
Affected service definitions and scripts must be updated coherently during
implementation; a temporary legacy alias is appropriate only if an existing
supported installation still requires it. No executable has been renamed by
editing this specification.

Use underscore spellings in project-owned package declarations and paths where
practical. Python packaging normalizes hyphens and underscores in distribution
names, so package indexes or tooling may still display robot-runtime. That
normalization does not rename console commands: robot_runtime and robot-runtime
are distinct executable names, even though they identify the same normalized
distribution name for package lookup.

| Public command | Intended purpose | Implementation owner |
| --- | --- | --- |
| lucid_conduct install | Prepare a fresh supported host and install the selected system. | Deployment installation |
| lucid_conduct config show / validate | Explain and validate selected/effective configuration without launching it. | Deployment composition |
| lucid_conduct info | Inspect selected software, installation records, declared hardware or explicitly requested device information. | Deployment routing to records/components/runtime |
| lucid_conduct doctor | Diagnose prerequisite, managed-file, configuration and compatibility problems; report the scope of checks. | Deployment with component/runtime diagnostics |
| lucid_conduct build | Explicit system, student-workspace or firmware builds. | Deployment orchestration and component build tools |
| lucid_conduct flash | Identify one target and perform an explicit firmware operation. | Deployment selection and firmware-owned tools |
| lucid_conduct runtime | Operate declared units and inspect runtime state. | robot_runtime |
| lucid_conduct upgrade | Stage and select an explicitly chosen replacement. | Deployment and component migration interfaces |
| lucid_conduct rollback | Restore an eligible previous application release/configuration/state set. | Deployment and component recovery interfaces |
| lucid_conduct completion | Provide shell-completion integration. | Shared Python command metadata and shell adapter |

The command family and identical runtime log/logs spellings are agreed; other
argument details in this draft are proposed. Uninstall is deferred until
managed-file removal and retained-data semantics are specified. Completion
support is part of the first CLI delivery.
Info and doctor must distinguish recorded information, read-only host inspection
and explicit device probes. Help and completion perform none of those probes.

### Runtime operator behavior and prepared restart

This specification sets the desired behavior. A focused comparison with the old
dream runtime can inform detailed design in robot_runtime, but is not permission
to port every legacy feature. Detailed runtime work may occur in another chat;
it remains one component workstream and does not delay video recording.

| Operation | Required behavior in the shared runtime interface |
| --- | --- |
| catalog | List installed units and supported launch modes with descriptions, using local metadata without starting a manager or probing hardware. |
| stop | Permit unit-based addressing; resolve the intended current run and retain the exact expected-run guard internally. Explicit run identity remains available. |
| log and logs | Identical aliases for one operation, with the same arguments, defaults, output, exit status and follow behavior. Support a unit's current/latest run and an explicit run ID. |
| restart | Prepare and validate candidate configuration, then coordinate stopping the intended run and starting its replacement through runtime's lifecycle owner. |
| resolve / recovery | Preserve resolve's specific missing-ownership operation and absent-supervisor requirement. Define concrete recovery cases before adding a general recover command. |

log and logs must share parsing/dispatch and appear in help and completion for
both lucid_conduct runtime and standalone robot_runtime. For unit-based logging,
choose the current run, or the latest recorded run if none is current; report the
chosen run ID. Following logs remains bound to that run rather than silently
switching to a replacement. Explicit run-ID access retains historical logs.

Convenience addressing does not weaken run ownership. If stop discovers run A
and run B replaces it before the request is applied, reject the stale request
rather than stopping B. Deployment must not recreate lifecycle policy with shell
stop/start sequences or duplicate recovery code.

Deployment owns preparation of vehicle/workload configuration; runtime owns the
lifecycle transition. The handoff is a versioned, opaque prepared-candidate
reference containing the target unit/profile revision, immutable resolved input
locations and their identity/hash. Runtime need not parse vehicle YAML. Trusted
launch integration consumes that candidate and associates its identity with the
replacement run. Exact API/schema details belong to the runtime implementation,
with these required semantics:

1. Read and validate candidate inputs while the current run remains active. A
   bad request leaves it running; accepted values are frozen for this attempt.
2. Submit the candidate with the expected old run ID. Runtime coordinates the
   transition so a concurrent stop/start/profile change cannot retarget it or
   interleave another owner. A stale identity fails explicitly.
3. Establish completed graceful stop of that specific run before starting its
   replacement. A failed or uncertain stop prevents a new start.
4. Start using the prepared snapshot without rereading editable source YAML.
   Record the old/new run IDs and candidate identity in the operation result.
5. Report replacement startup failure and resulting state clearly. Stop/start
   acceptance is not application readiness; this operation does not promise
   automatic restoration of the previous run after a startup failure.

For example, a valid threshold change from 0.50 to 0.60 is prepared before stop.
An invalid value does not interrupt the old run. A subsequent file edit to 0.70
does not alter the accepted 0.60 candidate. Standalone runtime remains usable
with its own supported preparation/input contract, without a deployment import.

### CLI names are presentation only

lucid_conduct and lucid are replaceable shell-facing names, not repository or
system branding. Their permitted uses are CLI registration and naming metadata,
generated command wrappers, alias/completion setup, CLI help and examples, and
checks of those interfaces. Component documentation may show a public command,
but component implementation must not depend on its spelling.

In particular, neither name is used for Python distributions, import packages,
modules, functions or classes; configuration keys, schemas or environment
variables; installation/data/configuration directories; service/unit names;
ROS names, API endpoints, runtime identities, log categories or UI titles.
Keep robot_deployment and robot_runtime as the implementation namespaces.
Literal command lines in diagnostic or historical records may naturally contain
the name; they are explanatory text, never machine identity or a lookup key.

A proposed package registration illustrates the entire routing boundary:

~~~toml
[project.scripts]
lucid_conduct = "robot_deployment.cli:main"
~~~

Keep the canonical spelling in this deployment-owned registration and the
optional alias spelling in adjacent CLI installation metadata. Installer and
completion generation consume that metadata; help uses the invoked executable
or an explicitly supplied display name. Do not scatter independent name literals
through parsers or application code, or add a generic branding framework.

Provide a neutral module invocation, proposed as python -m robot_deployment,
using the same dispatch implementation. Internal automation, service definitions
and component integrations call shared Python interfaces or neutral module/tool
entry points with the selected interpreter and resolved paths. They do not shell
out through lucid_conduct or lucid. The existing ROBOT_RUNTIME_RUN environment
contract and neutral filesystem examples below remain unchanged.

A future rename changes CLI naming metadata and regenerates wrappers and shell
integration, with corresponding help/example and CLI-check updates. User-owned
scripts invoking the public command need migration or a temporary compatible
entry point. It does not rename repositories, change runtime behavior or require
rewriting stored configuration and records. Historical command text can remain.

### Python owns behavior

The command structure, argument parsing, help, validation, dispatch and operation
logic live in Python packages. Console entry points are thin generated wrappers.
The CLI itself is an adapter over shared application functions, so browser and
CLI behavior do not diverge. Component tools can continue using their appropriate
languages; invoking CMake, colcon or a component shell script does not require
reimplementing them in Python.

The common entry point must reuse the runtime's parser/dispatch interface rather
than copy its argument definitions. The existing argparse parser is currently
built inside main; exposing side-effect-free parser construction and an
argv-taking entry point is a likely small implementation change, not a reason
to replace the CLI framework.

Arguments cross subprocess boundaries as arrays, not concatenated shell text.
Errors, exit status, request IDs and signal behavior survive delegation.
Human output is useful by default where introduced; machine output is explicit.
Existing standalone runtime JSON behavior is preserved unless deliberately
versioned.

### Help is part of the contract

Every command and subcommand has useful --help, not just the root. It describes
purpose, usage, required inputs, defaults, examples, output/exit behavior,
side effects, relevant prerequisites and common failures with next steps.
Startup-only versus live changes and restart/rebuild requirements are explicit
where relevant.

Help must work before installation is complete and without a manager, ROS
environment, network or attached hardware. Invalid command use points to the
relevant help. Root help groups the command families; detailed subcommand help
contains the operational detail.

### Show the selected call without executing it

All operation commands support a trailing --show-call flag. For example:

~~~sh
lucid_conduct runtime start perception --show-call
lucid_conduct build ros system --show-call
lucid_conduct flash mcu steering --show-call
~~~

The result identifies the owning package, Python entry point or callable,
selected interpreter, and equivalent argv including resolved local context.
If the actual handoff is an external component tool, that tool's invocation is
shown. Shell-rendered commands use proper argument quoting; a machine-readable
form retains the argv array. Credential values are redacted and labeled as such.
Redaction follows explicitly declared credential fields, not heuristic scanning
of arbitrary arguments or output. Ordinary configuration and file paths remain
visible; the command does not open credential files just to describe dispatch.

The flag parses the request and may read local configuration needed to explain
dispatch. It never performs manager requests, hardware discovery, package
installation, builds, flashing or launch. If required local context is missing,
it reports what cannot be resolved rather than obtaining it through side effects.

The output describes the immediate dispatch. A runtime start can be a client
request followed by later manager work; a build can invoke several tools. The
output must not invent a single Python command that reproduces an entire
stateful workflow. A Python module/callable is shown instead of a filesystem
script when that is the actual entry point.

This is distinct from a future install action preview: --show-call explains
dispatch, not every filesystem or system effect. Derive it from the same routing
data used for execution, not a parallel simulator or maintained command string.
It should add little code and no extra process, hardware or network work to
ordinary commands. No numerical timing claim is made before measurement.

### Completion and optional alias installation

Deliver Bash completion with the first usable CLI. Complete verbs, flags,
declared composition/unit names and appropriate file paths. Use local installed
metadata for dynamic names, with graceful fallback if it is absent. Tab must
never start services, open devices, build, flash, request credentials or wait for
network responses.

Keep one Python command definition for parsing, help and completion. An
argparse-compatible library such as argcomplete is a candidate; Bash registration
is a small shell adapter. Completion executes the command's early parser path,
so side-effect-free imports and early completion exit are requirements. Register
completion for lucid_conduct and, when enabled, lucid using the same parser and
completion implementation. Other shells can be added without changing command
semantics.

Installation provides an explicit opt-in to add the following alias for the
intended operator's interactive Bash environment:

~~~sh
alias lucid=lucid_conduct
~~~

The default is to install the full command without the alias. The option must
also be expressible in an unattended installation; no repeated prompt is needed
once the preference is supplied. Alias/completion setup belongs to the installer,
not composition or runtime configuration. Persist it in a small managed shell
snippet under a neutral deployment path, with an idempotent startup-file hook.
Preserve unrelated shell customizations; adding or removing this convenience
must not require reinstalling components or changing the runtime configuration.
Explain how to load the snippet in the current shell or open a new shell.

Neither spelling is guaranteed globally unused. Before exposing the full command
or alias, inspect the applicable installation path and intended operator's command
resolution, including aliases, functions, builtins and PATH executables.
Installation must not silently replace or shadow an unrelated command. If lucid
is occupied, report the conflict and leave the optional alias uninstalled while
continuing the otherwise valid installation. Keep the full command and neutral
module invocation available. Report any unresolved full-command conflict rather
than overwriting it. Reruns may update only shell integration owned by this
installation. These checks do not promise to prevent later user PATH changes.

The lucid spelling has known uses in LucidLink and the Lucid Developer Platform;
sharing the name is a shell-resolution issue, not a runtime incompatibility.
The alias is an interactive convenience, not a second globally installed binary.
Bash does not normally expand aliases in non-interactive scripts. Public command
examples use the full spelling; internal scripts and services use the neutral
interfaces described above. Help reached through a Bash alias may show the full
command name because alias expansion happens before Python receives argv.

No new dream-branded commands, required directory names or runtime identifiers
are introduced. Historical evidence and attribution need not be rewritten.
Downstream wrappers must not duplicate permission, validation or lifecycle logic.

### Proportionate safeguards

Keep security handling simple and deterministic for these local research robots.
Reuse the existing runtime authentication and operating-system permissions.
Keep credential contents out of tracked examples and routine diagnostic output.
Do not introduce a custom vault, heuristic secret scanner, per-command policy
engine or repeated approval workflow.

Read-only inspection, help, completion and call explanation should be easy to
use. Validation should reject a concrete unsupported or ambiguous condition,
name it and explain the remedy. Device compatibility, single-target flashing,
parameter contracts and expected-run checks remain operational correctness
requirements. They are not a reason to add general security bureaucracy.

Defaults should handle ordinary cases without extra prompts. Explicit commands
and resolved targets establish the intended action; any required confirmation
should address a specific unresolved or destructive choice, not repeat consent
already expressed.

## Worked example

These examples show file responsibilities and references, not a finalized schema.
All geometry and local addresses are illustrative, not measurements of an
existing car. Platform profile IDs below name the selected JetPack baseline;
their module/carrier admission rules still need fresh-host qualification.
These snippets are not directly accepted by today's scripts.

A compact possible layout is:

~~~text
robot_deployment/
  sources.json
  platforms/orin-nano-jp721.yaml
  platforms/orin-nx-jp721.yaml
  robot_models/example-car.yaml
  compositions/rgbd-demo.yaml
  parameters/perception.yaml
  src/robot_deployment/
    cli.py
    composition/
    installation/
    launch/
  docs/

/etc/robot_deployment/site.yaml       # private host choices
/opt/robot/releases/<release-id>/     # installed immutable release
/var/lib/robot/deployment/           # installation records
/var/lib/robot/runtime/              # runtime state and run configuration
<student-workspace>/config/requests.yaml
~~~

This is an illustrative organization, not a requirement to create empty
directories or one module for every conceptual responsibility.

### Exact software selection

The source lock retains the full revisions already selected in sources.json:

| Component | Commit |
| --- | --- |
| rgbd_camera | 0f4b82958f0d7798f0bf911641d0aa67084cc927 |
| rgbd_object_detector | 61219c6c1a692d311383cede66f1fb45b20f36e0 |
| robot_runtime | 3ab1cd84330985d5b2aa0a6a06986d1a84c6f1a4 |

URLs, SDK/interface revisions and toolchain requirements remain explicit in the
lock and platform declarations. Production model inputs use complete hashes,
not the shortened or placeholder identities sometimes used in explanatory text.

### Robot model

~~~yaml
schema_version: 1
id: example-car
geometry:
  body_m: {length: 0.50, width: 0.30, height: 0.22}
  wheelbase_m: 0.32
  wheel_radius_m: 0.05
  base_frame: base_link
component_roles:
  front_camera:
    supported_variants: [oak_d_rvc2, realsense_d455]
    selection: unique_available_device
mounts:
  front_camera:
    parent_frame: base_link
    child_frame: front_camera_mount
    translation_m: [0.12, 0.0, 0.18]
    rotation_rpy_rad: [0.0, 0.0, 0.0]
~~~

The body frame uses explicitly documented axes; optical-frame conversion belongs
to the selected camera integration and must not assume the mount frame is an
optical frame. No serial is present. The two camera variants can have different
adapter and geometry requirements while occupying the same logical role.

### Composition and delegated parameters

~~~yaml
schema_version: 1
id: rgbd-demo
robot_model: ../robot_models/example-car.yaml
sources: ../sources.json
supported_platforms: [orin-nano-jp721, orin-nx-jp721]
hardware:
  front_camera:
    default_variant: oak_d_rvc2
    allowed_variants: [oak_d_rvc2, realsense_d455]
models:
  cones: {component: rgbd_object_detector, descriptor: models/cones.json}
  coco: {component: rgbd_object_detector, descriptor: models/yolov8n-coco80.json}
units:
  perception:
    launcher: rgbd_perception
    components: [front_camera, detector_cones, detector_coco, combined_overlay]
    parameter_files: [../parameters/perception.yaml]
  video:
    launcher: runtime_ros_video
    source_unit: perception
    choices: [cones, coco, combined]
    default_choice: combined
    maximum_fps: 30
workload_requests:
  student:
    workspace_binding: student
    file: config/requests.yaml
    optional: true
    mappings:
      cones_score_threshold:
        target: {unit: perception, node: /perception/detector_cones, parameter: score_threshold}
        type: double
        units: dimensionless
        minimum: 0.30
        maximum: 0.90
        apply: startup
~~~

Launcher names refer to trusted installed integrations, not arbitrary functions
or shell strings supplied by student YAML. The numeric delegation above is an
illustrative composition choice, not an existing agreed detector policy.

The baseline ROS YAML supplies the absent-request value:

~~~yaml
/perception/detector_cones:
  ros__parameters:
    score_threshold: 0.50
    max_detections: 20
/perception/detector_coco:
  ros__parameters:
    max_detections: 20
~~~

A student request file can contain:

~~~yaml
cones_score_threshold: 0.60
~~~

The resolver produces 0.60 for the cone detector while retaining max_detections
at 20. A missing request uses 0.50. An attempted max_detections override or a
threshold outside the delegated range fails with the source, key and reason.
The current detector parameters are startup-only, so this takes effect in the
next perception run. Student algorithm parameters can remain in their own
project's YAML; no student policy implementation is introduced here.

### Private site configuration

~~~yaml
schema_version: 1
composition: rgbd-demo
robot_id: car-02
runtime_account: robot
hardware:
  front_camera:
    variant: oak_d_rvc2
storage:
  installation_root: /opt/robot
  data_root: /var/lib/robot
network:
  hostname: car-02
  media_address: 192.0.2.22
workspaces:
  student: /home/robot/student_ws
credentials:
  web_secret_file: /etc/robot_deployment/secrets/web-secret
  tls_certificate_file: /etc/robot_deployment/tls/certificate.pem
  tls_private_key_file: /etc/robot_deployment/tls/private-key.pem
~~~

192.0.2.22 is an example address. There is no device ID and no per-engine path.
The same file can survive replacement of the OAK-D by a compatible OAK-D.
Changing to D455 selects the allowed variant and uses its declared dependencies
and configuration; it is not an automatic fallback between camera models.

Platform matching uses the actual host and the composition's supported profiles.
If a selected variant's dependencies are not installed, configuration reports
the required installation change rather than building at Start.

### Commands and generated outputs

Proposed interaction:

~~~sh
lucid_conduct config validate --site /etc/robot_deployment/site.yaml
lucid_conduct install --site /etc/robot_deployment/site.yaml
lucid_conduct info installation
lucid_conduct runtime status
lucid_conduct runtime start perception
lucid_conduct runtime start video
lucid_conduct runtime log perception
lucid_conduct runtime logs perception
lucid_conduct runtime start perception --show-call
~~~

The log and logs examples are equivalent spellings of the same operation.

After opting into alias installation and loading the managed shell snippet,
lucid runtime status invokes the same command as lucid_conduct runtime status.
No lucid-named configuration file, service or Python package is introduced.

The common CLI resolves its normal site/state context after installation.
Installation records are written even for failed attempts. Only an eligible
completed release becomes selected. A hypothetical successful first record is:

~~~yaml
schema_version: 1
installation_id: install-0001
result: succeeded
inputs:
  deployment_revision: "<full deployment Git commit>"
  composition: rgbd-demo
  sources_sha256: "<full source-lock hash>"
  effective_site_sha256: "<hash of non-secret settings and references>"
host:
  detected_module: Jetson Orin NX
  matched_platform: orin-nx-jp721
  base_image_identity: "<observed JetPack 7.2.1 / L4T 39.2.1 identity>"
outputs:
  release_directory: /opt/robot/releases/install-0001
  runtime_profile: /opt/robot/releases/install-0001/runtime.json
  artifact_manifest: /var/lib/robot/deployment/install-0001/artifacts.json
previous_installation: null
checks:
  installed_artifacts: passed
  runtime_profile: passed
  camera_and_viewer_acceptance: not_run
application_workloads_started: false
~~~

The artifact manifest records actual source/package/model/engine identities and
build compatibility. Referenced non-secret input snapshots are retained, so
later site edits do not make the record uninterpretable. It does not prove
current file integrity or current hardware health.

Runtime receives its own generated, validated profile, including concrete
executables, environments, modes and capabilities. Per-run effective ROS YAML
and source hashes are recorded separately under that run's identity. The actual
camera serial is an observation of the run, not an installation constraint.

For --show-call, a runtime example could display:

~~~text
Owner: robot_runtime
Entry point: robot_runtime.cli:main
Equivalent invocation:
  <release-python> -m robot_runtime.cli --state /var/lib/robot/runtime start perception
Execution skipped.
This is the client call; later manager and workload actions are not executed or expanded.
~~~

## Extensibility without a framework

Adding another robot design should normally add geometry and composition data.
Adding a supported component variant adds a declared adapter and compatibility
requirements where necessary. A new backend's implementation remains in its
component repository. Supporting another shell adds a completion adapter.

Version the composition, site and record formats independently of package
versions. Declare compatibility explicitly and reject unsupported fields and
versions. A single repository makes coordinated changes easier; it does not
remove the need to read older local records or migrate saved settings.

Start with explicit code paths and reviewed schemas. Avoid arbitrary Python
imports from YAML, recursive configuration inheritance, plugin discovery,
general dependency solving, and automatic schema migration until a concrete
use case justifies them. Small libraries can be extracted later if independent
consumers and release requirements actually appear.

## Acceptance boundaries and remaining decisions

Implementation acceptance should demonstrate:

- Fresh installation from JetPack 7.2.1 / L4T 39.2.1 on each declared Nano/NX
  module/carrier profile, with recorded prerequisites, exact selected package
  and artifact identities, verified downloads and usable installed paths.
- Reruns that reuse verified work, preserve unrelated files and report failures.
- Explicit upgrade and scoped rollback, with runtime/configuration/state
  compatibility checked and application workloads left stopped.
- Like-for-like replacement without config edits; ambiguous and incompatible
  devices reported clearly; multiple-device role selection preserved where
  supported; unplug/replug reported without stale data being treated as fresh;
  explicit restart/control re-establishment and correct replacement calibration.
- YAML mappings reaching the intended namespaced nodes, valid student requests
  applied, invalid requests rejected, and existing runs unaffected by later
  source edits.
- CLI and standalone runtime sharing behavior; help and completion working
  without hardware or a manager; --show-call matching actual dispatch without
  execution or secret disclosure.
- Identical log/logs parsing and behavior, current/latest and explicit-run log
  selection, catalog output and convenient stop retaining stale-run rejection.
- Restart rejecting invalid candidates before stop, freezing accepted inputs,
  rejecting stale run/profile identities, preventing a new start after uncertain
  stop, and reporting replacement startup failures without claiming readiness.
- Optional alias installation and completion working in interactive Bash;
  installation without the alias, reruns and unrelated-name conflicts preserving
  existing shell setup and leaving the full command usable where installed.
- CLI name isolation: review occurrences of both spellings against the permitted
  CLI uses above; demonstrate that changing the entry-point spelling leaves
  neutral module dispatch, service definitions and configuration/state identities
  unchanged. This is a focused interface check, not a second system build or
  hardware acceptance run.
- Installation success reported separately from observed camera/video/vehicle
  acceptance. RC driving and simultaneous recording need their own evidence.

The repository transition, JetPack 7.2.1 baseline, external model acquisition,
runtime conveniences and single-camera/multiple-device direction are selected.
The pinned cone artifact and complete checkpoint/export/engine path have been
verified. The prepared-candidate API and coordinated restart are implemented and
tested, including rejection before stop, frozen inputs and guarded replacement.
The qualification and follow-up decisions as of 5 November are:

1. Fresh-image NX installation remains to be qualified: the completed Jah runs
   used an already prepared host. Exercise account/storage/USB and ROS-repository
   preparation, prerequisites, bootstrap and installation from the documented
   image when a clean NX environment is available. Nano qualification waits for
   available hardware and includes its software-encoding behavior.
2. Defer further physical replacement, ambiguity, unplug/replug, calibration,
   endurance and laptop-display checks until more of the system is complete.
   Retain previous evidence with its original scope; it does not imply these
   checks passed for the permanent installation.
3. Revisit MCU orchestration and recipe selection alongside the planned new
   Traxxas and IMU Pico firmware. Existing optional dispatch remains available;
   no recipe is selected by default and no physical flash acceptance is claimed.
4. Keep the unresolved cone-model attribution in
   [the detector notice](../../../rgbd_object_detector/NOTICE.md) explicit.
   The pinned cone artifact source remains separate from the removed legacy
   installation. A deliberate build/release retention policy is also follow-up
   work; see [storage retention](../operations.md#storage-retention).
5. Add explicit role binding only for actual multi-device compositions, and
   define recovery from concrete cases. A general registry, new recover command
   or automatic camera reconnect is not required for this milestone.

Development is consolidated into `dev`, with intermediate history archived;
publication and promotion to `main` remain later steps. Recording remains a
separate early milestone.

Worked-example field names, directory layout and demonstration dimensions are
proposals to review, not additional agreed requirements. Completion library and
CLI formatting are engineering choices within the contracts above.

## Source references

- [Current composition source pins](../../sources.json), [launch composition](../../tools/launch_perception.py) and [runtime profile renderer](../../tools/render_profile.py).
- [Historical combined-overlay evidence](../evidence/2026-10-28-combined-overlay/README.md), [installer and six-mode acceptance](../evidence/2026-11-03-deployment/README.md), and [permanent installation verification](../evidence/2026-11-04-everyday/README.md).
- [Runtime CLI implementation](../../../robot_runtime/src/robot_runtime/cli.py), [package entry points](../../../robot_runtime/pyproject.toml), [supervisor run context](../../../robot_runtime/src/robot_runtime/supervisor.py), and [integration contract](../../../robot_runtime/docs/integration-contract.md).
- [Camera interface](../../../rgbd_camera/docs/interface-v1.md), [detector interface](../../../rgbd_object_detector/docs/interface-v1.md), and [model artifact contract](../../../rgbd_object_detector/docs/model-profiles.md).
- [Existing configuration ownership and static delegation](../../../../dream_repositories/dream_system/docs/development-guide/configuration-calibration-and-profiles.md) and [legacy command dispatch](../../../../dream_repositories/dream_system/bin/dream) inform the migration boundary; they do not impose the old repository structure.
- [Python packaging entry points](https://packaging.python.org/en/latest/specifications/entry-points/) explain generated console wrappers.
- [Python distribution name normalization](https://packaging.python.org/en/latest/specifications/name-normalization/) distinguishes package lookup from executable naming.
- [Bash command lookup](https://www.gnu.org/software/bash/manual/html_node/Command-Search-and-Execution.html) and [programmable completion](https://www.gnu.org/s/bash/manual/html_node/Programmable-Completion.html) describe shell behavior.
- [Bash aliases](https://www.gnu.org/software/bash/manual/html_node/Aliases.html) explain interactive alias expansion and its limits.
- [argcomplete documentation](https://kislyuk.github.io/argcomplete/) documents argparse integration and execution during completion.
- [LucidLink command-line use](https://support.lucidlink.com/hc/en-us/articles/31125495032461-Link-to-filespace-from-the-command-line) and [Lucid Developer Platform CLI](https://docs.lucidcomputing.ai/reference/cli-reference) establish existing uses of the optional lucid spelling.
