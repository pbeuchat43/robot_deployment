# Retired everyday installation on Jah

On 15 November 2026, the operator-authorized cleanup removed this application
and disabled its management services. The
[VO/VIO release qualification](evidence/2026-11-15-vio-release-qualification/README.md)
passed in a separate private installation; it has not been activated for daily
use. The commands, service states and paths below describe the retired
4 November installation and are not current operating instructions.

That permanent installation used the `poi` account and the `lucid_conduct` CLI.
Its source identity is `7a682acafc52fc93d2b8cc02018c35842c4fdc4f`, with the
component selections in that commit's `sources.json`. Subsequent documentation
commits do not change the installed package identity.

Selected and verified on 4 November 2026 as release `r20261104-everyday`.
Both management units were enabled and active; existing account lingering was
enabled. Perception and video were stopped after verification and stayed stopped
through a management restart. No physical reboot was performed. See the
[verification and cleanup record](evidence/2026-11-04-everyday/README.md).

## Daily use

Open a new Bash/SSH session. The normal command and Bash completion are installed;
the optional `lucid` alias is not enabled. Inspect the installation without
starting a camera:

```bash
lucid_conduct info installation
lucid_conduct doctor
lucid_conduct runtime catalog
lucid_conduct runtime status --fresh
```

To start OAK-D with both detectors and video:

```bash
lucid_conduct runtime start perception --mode oak-both
lucid_conduct runtime start video
```

Open [the viewer](https://192.168.0.34:8443/video), unlock with the existing
passphrase and connect video after the source reports streaming. The certificate
and passphrase are preserved. Cones, COCO and Combined are selectable overlays;
reconnect video after changing the overlay. To change the camera, use
`lucid_conduct runtime restart perception --mode d455-both`. The other declared
modes are listed by `runtime catalog`.

Lifecycle commands return an accepted operation. Check
`lucid_conduct runtime operation REQUEST_ID` and fresh status for completion.
After a successful stop, status retains the previous run as `exited`, with
`stop_phase: complete`, an inactive supervisor and an empty process list.
When finished, disconnect the viewer, then stop video and perception:

```bash
lucid_conduct runtime stop video
lucid_conduct runtime stop perception
lucid_conduct runtime status --fresh
```

The management services are `robot-manager-jah.service` and
`robot-web-jah.service`. They run under the user systemd manager. Camera,
inference and video are explicitly started workloads; management startup does
not start them. Inspect service logs with
`journalctl --user -u robot-manager-jah.service -u robot-web-jah.service`.

## Permanent paths

All paths below are under `/home/poi` on Jah, not the Windows source workspace.

| Purpose | Path |
| --- | --- |
| Selected release | `.local/share/robot_deployment/current` |
| Release directory | `.local/share/robot_deployment/releases/r20261104-everyday` |
| Installation cache | `.local/share/robot_deployment/cache` |
| Installation records and managed site | `.local/state/robot_deployment/deployment` |
| Runtime state and run history | `.local/state/robot_deployment/runtime` |
| Original private site, CLI context, shell integration and secrets | `.config/robot_deployment` |
| Student workspace | `robot_ws` |
| Deployment source and exact source bundles | `.local/share/robot_sources/{deployment,cache}` |
| Matching bootstrap | `.local/share/robot_bootstrap/7a682ac` |

The normal command resolves through `current`. Release artifacts contain absolute
paths and must not be moved. Use [installation and maintenance](operations.md)
for upgrades and new builds. Keep credentials and site configuration private.

## Legacy removal and recovery

The Jah `dream_system` checkout, its shell startup hook, legacy DREAM config,
data and environment directories, and superseded management units were removed.
The three old global ROS environment assignments and DREAM camera/lidar udev
rules were removed. A robot deployment rule grants the runtime account access
to compatible OAK and D455 cameras. Independent repositories, shared ROS/CUDA/
JetPack packages and the Windows checkouts were preserved.

Old DREAM test/build trees were removed using a one-week cutoff and active
reference checks. Some historical evidence therefore refers to retired private
raw directories; the committed summaries remain available. Recent qualification
artifacts were retained. This does not establish an automatic cleanup policy.
The campaign removed 35 old test/build trees and eight legacy installation
directories. Root filesystem usage fell from 82% to 51% after the permanent
build, leaving approximately 55 GiB available.

The new pipeline has no dependency on the deleted installation. The selected
cone ONNX weights still come from the agreed pinned `oakd_gpu_cone_detector`
artifact source. That legacy detector is not built or installed; changing the
model's source is separate work.

A useful independent RGB-D rollback release remains at
`.local/share/robot-runtime-dev/current`, with its own retained configuration and
state. Backup metadata and `restore-management.sh` are under
`.local/state/robot_deployment/deployment/backups/previous-rgbd-20261104`.
This is a manual fallback to the earlier independent runtime, not a release
managed by the new `lucid_conduct rollback` command. The helper requires fresh,
unblocked, stopped workloads, then switches management services only. Its
syntax and paths were checked; a restoration round trip was not performed.
After fallback, use the explicit command recorded in its manifest; the normal
CLI context still points at the new deployment.
