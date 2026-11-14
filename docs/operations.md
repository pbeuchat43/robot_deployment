# Installation and operation

The earlier installer/operator checks and six D455/OAK-D modes passed on Jah Orin NX;
see that [verification record](evidence/2026-11-03-deployment/README.md).
The eight-mode recording candidate has its own
[verification record](evidence/2026-11-07-recording/README.md) and exact build identities.
Fresh Nano/NX installations, custom carriers, physical camera replacement and
vehicle operation are not established by the software checks. Historical camera
evidence remains linked from the [README](../README.md).
The [15 November VO/VIO qualification](evidence/2026-11-15-vio-release-qualification/README.md)
passed the standard application/Docker rebuild, installer rerun and full workloads
on the existing host. The old 4 November installation was removed with operator
authorization; its [everyday guide](everyday-jah.md) now records retired paths.
The new qualified candidate remains private and has not been activated for daily use.

## Bootstrap on the selected target

Start from JetPack 7.2.1 / L4T 39.2.1, Ubuntu 24.04 arm64, Python 3.12 and the
declared reference module/carrier. Base-image flashing is a separate operation.
Use an existing intended runtime account with a working user systemd manager.
The minimal bootstrap prerequisites are Git, CA certificates and Python 3.12
with `venv`/ensurepip (`git ca-certificates python3-venv` on the target).

Obtain a clean deployment Git checkout at the selected full commit from the
[canonical repository](https://github.com/pbeuchat43/robot_deployment), or transfer
that checkout through a Git bundle. Unpublished component commits can be supplied
as Git repositories or `NAME.bundle` files in a private source-cache directory. The recognized names
are `robot_runtime`, `rgbd_camera`, `rgbd_object_detector`, `vision_msgs` and
`cone_artifact`; optional firmware uses `pico-sdk`, `picotool`,
`firmware-bno08x` and `firmware-traxxas`.

From the clean checkout, as the runtime account:

```bash
python3 tools/bootstrap.py --destination "$HOME/robot-bootstrap/selected" \
  --source-cache "$HOME/robot-source-cache"
```

Omit `--source-cache` when every selected commit is available from its declared
remote. Bootstrap creates a new directory and refuses to overwrite an existing
one. It exports committed deployment/runtime content into separate build trees,
builds wheels with pinned Python tools, downloads the pinned execution dependencies
and installs an isolated environment. The receipt records source commits and
downloaded wheel hashes. Python lockfiles pin versions; they are not predeclared
wheel-hash locks. Network access is required for missing packages and artifacts.
Bootstrap does not apply root actions, select a release or start management.

The following examples use a Bash array for the bootstrapped module interface:

```bash
operator=("$HOME/robot-bootstrap/selected/venv/bin/python" -m robot_deployment.cli)
"${operator[@]}" --help
```

The environment also contains the public `lucid_conduct` console entry point.
Its package data includes the site example and definitions under
`<bootstrap>/venv/share/robot_deployment/`.

## Private site and host prerequisites

Copy [site.example.yaml](../config/site.example.yaml) outside the repository and
edit its account, robot/platform, storage, network, ROS namespace/domain and
credential references. The example's address and paths are placeholders.
`runtime_account` must match the user running installation. Keep
`management.start: false` while preparing credentials. The default camera
selection is OAK-D, with no serial constraint; D455 is another declared variant.

```bash
site="$HOME/robot-site.yaml"
"${operator[@]}" config validate --site "$site"
"${operator[@]}" info host
"${operator[@]}" host setup --site "$site" --output "$HOME/robot-host-setup.sh"
```

Inspect the generated script before applying it with `sudo bash`. It prepares
the declared account/storage and grants that account USB access to compatible
OAK vendor devices and D455 product devices. It refuses conflicting files or
nonempty storage owned by another account. Replug cameras to apply new USB rules.
It does not enable lingering, flash firmware or start workloads.

On a fresh host without the ROS repository, first generate and review:

```bash
"${operator[@]}" host repositories --output "$HOME/robot-ros-repositories.sh"
sudo bash "$HOME/robot-ros-repositories.sh"
"${operator[@]}" host plan --site "$site" --output "$HOME/robot-packages.json"
```

The repository script verifies the pinned `ros2-apt-source` bootstrap hash.
Ubuntu and NVIDIA package sources must match the selected image; this tool does
not select a replacement image or carrier BSP. Inspect both the JSON plan and
its sibling `.sh`, then apply the reviewed package script:

```bash
sudo bash "$HOME/robot-packages.sh"
```

Planning resolves exact apt versions, preserves compatible installed versions,
and simulates the missing-package transaction. The script checks that transaction
again before installation. Changed plans, package removals and BSP upgrades fail
closed. Generate a new plan after any intentional host change. Root actions are
separate from unprivileged source builds; installation never invokes sudo.

## Build, validate and select

Allow at least 20 GiB free space for an isolated source build. Additional releases
retain their own SDK/build outputs. Source builds may take substantial time.

```bash
"${operator[@]}" install --site "$site" --release-id r20261103-a \
  --source-cache "$HOME/robot-source-cache" --stage-only
```

Installation verifies exact Git selections and model hashes, builds both camera
SDKs and ROS components, exports the pinned COCO checkpoint using the detector's
locked exporter, builds both target TensorRT engines, builds the runtime's native
video dependencies, and validates the generated runtime profile. Component-owned
procedures retain their compatibility checks. The cone model's unresolved licence
attribution remains in the selected detector's `NOTICE.md`; installation does
not resolve it or redistribute model binaries through this repository.

Each stage writes its command logs and output inventory. Repeating the same
release ID reuses only successful, unchanged stages with identical selected
inputs. A partial/failed stage is retained and rejected; inspect its logs and use
a new release ID after correcting the cause. Do not remove the record or silently
adopt partial output. Completed releases are never relocated because compiled
dependencies and virtual environments can embed their paths.

Repeat the identical command without `--stage-only` to verify and select the
completed release. A normal install can also build and select in one invocation.
Selection requires stopped, unambiguous workload ownership. It saves state,
installs owned neutral management units, switches `current` atomically, and
records the previous release. It never starts application workloads. With
`management.start: false`, management remains stopped unless the existing owned
management services were running before maintenance.

The selected layout is:

```text
<installation_root>/current -> releases/<release-id>
<installation_root>/releases/<release-id>/venv, ros, sdk, models, av-native
<installation_root>/releases/<release-id>/build/logs/
<data_root>/deployment/installations/<release-id>.json
<data_root>/deployment/selections/
<data_root>/deployment/site.json
<data_root>/runtime/
```

Failed preflight attempts also have receipts under
`${XDG_STATE_HOME:-~/.local/state}/robot_deployment/attempts/`. A successful build
record explicitly says camera/viewer acceptance is `not_run`.

## Management and commands

Create the runtime credential at the path declared by `web_secret_file`, with
the parent directory already prepared:

```bash
"${operator[@]}" runtime credential --file /absolute/private/credential.json
```

It prompts without echo and stores a verifier. Provision TLS certificate/key
files for the declared hostname separately, following the
[runtime HTTPS guide](../../robot_runtime/docs/runtime-operator-guide.md#https-and-command-access).
The installer references credentials; it never copies their contents into records.

For the example `runtime_namespace: robot`, explicitly start management:

```bash
systemctl --user start robot-manager-robot.service robot-web-robot.service
```

To request management startup at login, enable those same user units. Boot before
login also needs an explicitly configured lingering account. Neither starts
perception or video. Inspect logs with `journalctl --user -u UNIT`; never assume
service-start acceptance establishes browser or camera readiness.

Normal selection records the local site context and installs an owned wrapper,
Bash completion and startup hook. Load the reported snippet or open a new Bash
session. Use `--no-shell` to leave shell integration alone. The optional short
alias is opt-in and conflicts are reported without replacing unrelated commands:

```bash
lucid_conduct shell install --alias
lucid_conduct runtime catalog
lucid_conduct runtime start perception --show-call
lucid_conduct info installation
lucid_conduct doctor
lucid_conduct shell remove
```

`--show-call` reports the actual owner, entry point and arguments without
dispatch, IPC, hardware probing, network or build activity. Help and completion
also work without a manager. `doctor` verifies release integrity and reports
fresh runtime ownership; it does not open a camera. Full-command conflicts leave
the explicit `<installation_root>/current/venv/bin/python -m robot_deployment.cli`
interface available. Shared runtime commands and exit codes remain owned by
`robot_runtime`; [launch](launch.md) shows perception/video use.

Deployment commands display readable fields by default; add `--json` for
structured output in scripts. Runtime retains its standalone JSON output.
Call explanations include the selected interpreter and equivalent invocation;
missing local context is identified without obtaining it through side effects.
Detailed subcommand help includes examples, prerequisites, side effects and
failure remedies. For example, `lucid_conduct install --help` works before a
site or manager exists.

## Upgrade, rollback and explicit builds

Bootstrap the new selected deployment commit in a new directory. Supply the
intended private site and definitions, then run its `upgrade` command with a new
release ID. Upgrade uses the same staged installer and stopped selection guard.
Use `--stage-only` to finish builds before the maintenance window. Stop video and
perception through runtime before selecting. Invalid ownership or an unresolved
transition blocks selection; it does not authorize process killing or adoption.

```bash
lucid_conduct runtime stop video
lucid_conduct runtime stop perception
lucid_conduct rollback
# Or select an explicitly retained, compatible completed release:
lucid_conduct rollback --release-id r20261103-a
```

Rollback verifies artifacts, exact required host package versions and runtime
state compatibility. It restores the chosen application release and its managed
site snapshot, while keeping run history. It does not reverse apt, base-image,
firmware or student-workspace changes. A failed selection attempts to restore
the previous pointer, site and owned management files; inspect the selection
receipt if recovery itself fails. Keep useful release/state backups until the
new deployment has been accepted.

```bash
lucid_conduct build ros system
lucid_conduct build ros student
lucid_conduct build ros student --clean
```

System builds use the pinned camera, detector and native recording sources into
`<data_root>/build/system/<release-id>`; student builds use
`<workspaces.student>/src` with outputs under its `.robot-deployment`.
`--clean` removes only recorded build/install/log directories. These are explicit
development outputs: they do not replace the immutable selected release, install
dependencies or restart workloads. No `ai4r_policy` implementation is used.

## Storage retention

Each new release ID gets its own installation and build directories. A verified
rerun of the same release reuses its completed stages; upgrading to a new release
does not automatically prune the previous one. Repeated experiments therefore
retain more than the files needed by a running camera or detector:

| Retained content | Why it remains |
| --- | --- |
| SDK/ROS install prefixes, Python environment, engines, native video and configuration | Needed to run the selected or retained rollback release. |
| SDK source/CMake trees, ROS build directories and logs, Python build/export environments, native-video source and Rust toolchain | Used to produce artifacts and diagnose failures; candidates for a future reviewed scratch-cleanup operation. |
| Shared Git/download caches, wheels, model inputs and installation records | Support exact-source rebuilds, verified reruns, integrity checking and rollback. Some are referenced or inventoried by releases. |

For example, a later release can reuse a verified model download but still build
another pair of SDKs and engines and another native-video prefix. Keep the
selected release, a known-good rollback and any candidate under evaluation.
Older failed/superseded experiments can be reviewed for removal once their
useful evidence is retained. That is a proposed retention approach, not an
automatic policy or a new deletion command.

Do not treat an entire installed release or its source cache as disposable
scratch: ROS source links can reference the cache, compiled artifacts can embed
paths, and the integrity inventory includes wheels and model inputs as well as
runtime files. A cleanup tool needs to check those dependencies and preserve
records. `build ros ... --clean` only cleans the separate workspace's recorded
build/install/log outputs before rebuilding; it does not prune releases or caches.

## Optional firmware

The opt-in [RC Car workflow](rc-car.md) documents the RCPv1 Pico commands, selected firmware build and flash, the optional live ROS unit, and Traxxas ESC calibration.

The default composition selects no MCU firmware. To enable one, declare a
`firmware.bno08x` or `firmware.traxxas` recipe in trusted composition data with
`source: {url: HTTPS_URL, commit: FULL_COMMIT}`, a repository-relative `path` and
`board: waveshare_rp2040_zero` or `waveshare_rp2350_zero`. Install that selection
to provision the pinned Pico SDK/picotool 2.3.1 and its declared host prerequisites.
Separate board/revision build directories prevent reuse of a different board or
source tree's CMake cache.

```bash
lucid_conduct info mcu bno08x
lucid_conduct build mcu bno08x
lucid_conduct flash mcu bno08x --device-id EXACT_DEVICE_ID \
  --manifest /absolute/bundle/bno08x_pico_firmware.manifest.json
```

Flashing is always explicit and delegates manifest, board, identity and
confirmation checks to the component-owned tool. BNO writes a report (a new
`--report` path can be supplied); Traxxas emits its result to stdout and accepts
no report-file option. There is no automatic recovery, target guessing or
flash during install/build. Firmware dispatch checks do not establish physical
flash or vehicle acceptance.
