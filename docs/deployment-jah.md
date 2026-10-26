# Jah development deployment

The selected persistent release is `rgbd-20261027-dev20` under
`~/.local/share/robot-runtime-dev/releases/`; `current` points to it. It contains
the tested runtime wheel/venv, native video support, ROS install, both SDKs,
model descriptors/engines and this minimal composition. The private configuration
is in `~/.config/robot-runtime-dev`, with separate work and manager-state
directories. No running process depends on the temporary package build directory.

`robot-runtime-dev-manager.service` and `robot-runtime-dev-web.service` are enabled
user services. They replace the selected dev17 management pair on the existing
HTTPS origin and port 8443. Existing credential and TLS files are reused. Only
management services start automatically; camera/inference/video workloads were
left stopped. User lingering was already enabled and was preserved. A reboot
was not performed.

The relocated candidate passed D455/cones and OAK-D/COCO with measurement markers
disabled, including 25 exact overlays per case and live WebRTC. The selected
persistent manager subsequently passed an OAK/cones run with another 25 exact
overlays, live media configuration bound to that run, HTTPS viewer availability,
locked unauthenticated commands and clean workload stop. See
[the deployment audit](evidence/2026-10-27-integration/deployment.json).

## D455 USB access

The overnight verification used the explicitly started temporary root helper.
Its original USB ACL was verified restored when the hardware reservation ended. Permanent
D455 access therefore needs this one local step on Jah:

```bash
sudo bash ~/.config/robot-runtime-dev/enable-d455-usb.sh
```

The prepared helper installs one rule for the selected D455's exact USB identity,
grants access to the local operator, and refuses to overwrite a different rule.
It has not been executed with root privileges or verified after installation.
The SDK selection serial is recorded separately in the private site file. OAK-D
does not need this step. The temporary helper's node/ACL identity checks must
complete before applying the permanent rule.

## Rollback

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
