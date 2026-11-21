# Everyday installation on Jah

Jah runs `r20261116-cli-output-v2` for the `poi` account. On 21 November 2026,
the `current` symlink and the selection record both identified this release,
and the manager and HTTPS services were active. The installed deployment is
`0.1.0.dev9` at `570e63e`, paired with runtime `0.1.0.dev30` at `ea91a1d`.
The [16 November activation record](evidence/2026-11-16-cli-output/README.md)
contains the full source identities and software checks. The
[15 November OAK investigation](evidence/2026-11-15-everyday-vio-oak/README.md)
records the camera trials on the preceding release.

Both camera profiles are 720p30. The installed odometry backend is Docker,
with Off / VO / VIO available across 24 camera/model/odometry modes. Odometry
defaults to Off unless explicitly selected. Physical calibration, accuracy under
motion and vehicle acceptance remain separate work.
The [USB-only RP2040-Zero check](evidence/2026-11-15-rc-bare-pico/README.md)
verified its existing RC firmware and retained the exact identities privately.
The everyday vehicle unit remains unprovisioned; the bench profile still needs
vehicle-specific wiring and physical qualification.

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

`info installation` shows the selected release and build identities.
`lucid_conduct` prints readable output by default. Add `--json` for scripts.

To start OAK-D with both detectors, VIO and video:

```bash
lucid_conduct runtime start perception --mode oak-both-vio
lucid_conduct runtime start video
```

Open [the viewer](https://192.168.0.34:8443/video), unlock with the existing
passphrase and connect video after the source reports streaming. The certificate
and passphrase are preserved. Cones, COCO and Combined are selectable overlays;
reconnect video after changing the overlay. The current reference viewer uses a
640 by 480 video rendition; this does not change the 720p capture profile.
To change the camera, use
`lucid_conduct runtime restart perception --mode d455-both-vio` after stopping
recording and video. Use the catalog for other combinations; for example,
`oak-both` selects Off and `oak-both-vo` selects VO.

Record an event explicitly while perception is running:

```bash
lucid_conduct runtime start recording --outputs rgb annotated depth --overlay combined
lucid_conduct runtime stop recording
```

Wait for recording finalization before stopping perception. Recording produces
segmented MP4 files with frame indexes in the managed data root; see
[recording](recording.md) for retention and export commands. The selected site
uses a 10 GB recording budget, a 4 GB free-space reserve and 30-second segments.

Lifecycle commands return an accepted operation. Check
`lucid_conduct runtime operation REQUEST_ID` and fresh status for completion.
When finished, disconnect the viewer and stop the workloads:

```bash
lucid_conduct runtime stop recording
lucid_conduct runtime stop video
lucid_conduct runtime stop perception
lucid_conduct runtime status --fresh
```

After a successful stop, status can retain the previous run as `exited`, with
`stop_phase: complete`, an inactive supervisor and an empty process list.
The management services are `robot-manager-jah.service` and
`robot-web-jah.service`, under the user systemd manager. They are enabled and active;
management startup does not start application workloads. Inspect service logs
with `journalctl --user -u robot-manager-jah.service -u robot-web-jah.service`.
At activation on 16 November, application workloads were stopped for operator testing.

## Permanent paths

All paths below are relative to `/home/poi` on Jah.

| Purpose | Path |
| --- | --- |
| Selected release | `.local/share/robot_deployment/current` |
| Release directory | `.local/share/robot_deployment/releases/r20261116-cli-output-v2` |
| Installation cache | `.local/share/robot_deployment/cache` |
| Installation records and managed site | `.local/state/robot_deployment/deployment` |
| Runtime state and run history | `.local/state/robot_deployment/runtime` |
| Private site, CLI context, shell integration and secrets | `.config/robot_deployment` |
| Student workspace | `robot_ws` |
| Matching bootstrap | `.local/share/robot_bootstrap/570e63e` |

The normal command resolves through `current`. Release artifacts contain absolute
paths and must not be moved. Use [installation and maintenance](operations.md)
for upgrades and new builds. Keep credentials and site configuration private.
Exact source inputs and activation records are retained in the private experiment
directory named in the evidence record, as well as the installation cache.

## Recovery and historical installations

The everyday selection records `r20261115-dev` as the previous release.
With workloads stopped, `lucid_conduct rollback` selects that release if needed.
It occupies disk space while inactive. For rebuilding and shared cache
dependencies, see [installation and storage retention](operations.md#storage-retention).

The 15 November experiments used separate private installation and state roots.
Their source identities and measurements are recorded in the
[OAK follow-up](evidence/2026-11-15-everyday-vio-oak/README.md).

The [4 November installation](evidence/2026-11-04-everyday/README.md) was
retired on 15 November. Shared ROS/CUDA/JetPack
packages and independent source repositories remain outside this application
release. The cone ONNX weights still use the pinned `oakd_gpu_cone_detector`
artifact source; that legacy detector is not built or installed.
