# Jah development deployment

The selected persistent release is `rgbd-20261028-dev21` under
`~/.local/share/robot-runtime-dev/releases/`; `current` points to it. It contains
the tested runtime wheel/venv, native video support, ROS install, both SDKs,
model descriptors/engines and this minimal composition. The private configuration
is in `~/.config/robot-runtime-dev`, with separate work and manager-state
directories. No running process depends on the temporary package build directory.

`robot-runtime-dev-manager.service` and `robot-runtime-dev-web.service` are enabled
user services. They replace the selected dev17 management pair on the existing
HTTPS origin and port 8443. Existing credential and TLS files are reused. Only
management services start automatically; camera/inference/video workloads were
left stopped at initial deployment. The subsequent operator-assisted physical
checks left the user's D455/COCO and video workloads running. The user later
stopped both; the dev21 upgrade preserved that stopped workload state. User lingering was
already enabled and was preserved. A reboot was not performed.

The relocated candidate passed D455/cones and OAK-D/COCO with measurement markers
disabled, including 25 exact overlays per case and live WebRTC. The selected
persistent manager subsequently passed an OAK/cones run with another 25 exact
overlays, live media configuration bound to that run, HTTPS viewer availability,
locked unauthenticated commands and clean workload stop. See
[the deployment audit](evidence/2026-10-27-integration/deployment.json).

## D455 USB access

The overnight verification used the explicitly started temporary root helper.
Its original USB ACL was verified restored when the hardware reservation ended.
The operator subsequently installed permanent D455 access using:

```bash
sudo bash ~/.config/robot-runtime-dev/enable-d455-usb.sh
```

The prepared helper installs one rule for the selected D455's exact USB identity,
grants access to the local operator, and refuses to overwrite a different rule.
Installation was verified, including after physical USB unplug/replug: the newly
enumerated device node belonged to the configured operator, had mode `0660`, and
passed a read/write open check. D455 acquisition and inference recovered at about
30 Hz after manual restart. No additional permission step is pending. The SDK
selection serial is recorded separately in the private site file. OAK-D does not
need this step. See [the physical-check follow-up](evidence/2026-10-27-integration/physical-checks.md)
for the observed recovery behavior and remaining viewer/empty-scene findings.

## Dual-mode update and dev20 rollback

The dev21 update adds six camera/model launches, separate model processing
observations, and live selection of a cone or COCO overlay. Both detectors keep
running in dual mode when the video source changes. Viewers reconnect explicitly.
The final release passed both-camera dual-mode checks before selection. After
selection, the manager/web services, HTTPS routes and installed browser assets
were verified with camera and video workloads stopped. See
[the dual-viewer evidence](evidence/2026-10-28-dual-viewer/README.md).

The dev20 release remains intact. Its configuration, service files and coherent
stopped manager state are retained under
`~/.local/state/rgbd-verification/dual-viewer-20261028/rollback-dev20`.
The current service files were not changed. To return to dev20 after stopping
all workloads and resolving any uncertain ownership:

```bash
~/.local/share/robot-runtime-dev/current/venv/bin/python \
  ~/.local/state/rgbd-verification/dual-viewer-20261028/rollback_dev20.py
```

The script checks stopped workloads and service identity, restores the previous
site/profile and release selection, and restarts the same management pair. Both
releases and runtime history remain available. It starts no camera/video workload.
The script was inspected; a rollback round trip was not performed.

## Historical dev17 rollback

The following is the older migration rollback, not the normal dev21-to-dev20
rollback above. Use it only when deliberately returning to the legacy dev17 pair.

The dev17 release, original service files, profile, credentials/TLS and original
state remain in place. A coherent stopped-state copy is retained under
`~/.local/state/rgbd-verification/integration-20261027/rollback-dev17`. New state
is separate; no legacy database was migrated or merged.

Stop both new workloads and confirm they are unblocked. The prepared local
rollback command checks this and verifies the retained original service files:

```bash
python3 ~/.local/state/rgbd-verification/integration-20261027/rollback_dev17.py
```

It disables/stops the new management pair and re-enables/starts the old pair.
It does not start workloads or remove new data. The script was inspected; a
rollback round trip was not performed. If either state has unresolved ownership,
inspect it before changing service selection. Keep only one management web service
selected on port 8443.
