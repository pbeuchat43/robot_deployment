# Recording and RC development consolidation

11 November 2026, Australia/Sydney. Consolidation began on 10 November.

The user approved combining the completed recording and RC work, squash-merging
and publishing `dev`, then removing the completed feature branches and worktrees.
Existing `main` branches, Jah's permanent installation, and repository locations
remain unchanged. This is development integration, not a release promotion or
new vehicle acceptance.

## Source identities

| Repository | Original feature revision(s) | Consolidated `dev` |
| --- | --- | --- |
| `rc_car_firmware` | `0358ca1c94506dd531519615aba0be38f4956fc4` | `f25b331810f56f4ca61dfe201e129046b4ed557b` |
| `rc_car_interface` | `d01c748aba3308c2918405c5ebeabf0f5633e730` | `1903b9524a82255b2a230cdc26cb5bf255487210` |
| `rgbd_camera` | `564fa6a021783beb87f5518a4b98c13c28293d22` | `ad078edc1081118fe1677b0b47b349eb3b89bcf1` |
| `rgbd_object_detector` | `32781ed100b8891e02f0d9a853196f363517b9b4` | `7175b4f61cc8bc6348d01a7a1b191ee7cb80bac7` |
| `robot_runtime` | Recording `1b4459e1b45d84a0076147e9fbfc644f35579d69`; ROSIDL `4139185c26d0e1bed942496ea2bd9207ee73142b` | `d228ed03d43e2e505e732b0f618d1dad83e6b55c` |
| `robot_deployment` | Recording `e9acc8ba946780e284a0b311bf3c944984efdb66`; RC `984694843163f4a5166f41e2f00eb0ad114c448a` | The commit introducing this record |

Resolve the deployment squash with:

```sh
git log --diff-filter=A --format=%H -- docs/evidence/2026-11-11-consolidation/README.md
```

The firmware, interface, camera and detector squash trees exactly match their
original feature tips. Runtime `0.1.0.dev27` combines the unchanged recording
implementation with the generated ROSIDL bounded-string fix; its other changes
are version metadata and the README.

Deployment `0.1.0.dev5` depends on that runtime version. Its source lock selects
the consolidated camera, detector and runtime commits above. The RC firmware and
interface remain opt-in composition selections; their compatible RCPv1 commits
are listed here without enabling vehicle hardware in the default composition.
The two deployment features now retain both recorder and optional vehicle
packages in installation and system rebuilds, and both units in generated
profiles. Regression checks cover both vehicle-disabled and vehicle-enabled
compositions.

## Verification

[The machine-readable record](summary.json) identifies the exact sources, trees,
package hashes, firmware manifests and log hashes. Deployment execution checks
used clean integration commit `946aa7b0eb8db76ca3d368906f90054fbdf874bf`.
The final deployment squash differs from it only in this evidence directory and
the README evidence links. Installed wheels retain the tested integration
identity; they are not relabelled as artifacts built from the final squash.

All new execution checks ran on reserved Jah in a private temporary directory:

- Fresh official bootstrap, wheel/source-distribution builds and a clean
  bootstrap dependency check passed. Installed assets, all 11 definition files,
  native recorder sources in the source distribution and five CLI entry points
  were verified against the selected source snapshots.
- The installed runtime passed 179 unit tests; installed deployment passed 51.
- The production ROS builder compiled eight packages, including the recorder
  and optional RC interface. Both RC transport/ROS CTests and both recorder
  CTests passed. The ROS vehicle test uses a fake Pico and a localhost domain.
- Installed launch inspection passed all eight perception modes without
  starting a component container or opening a camera.
- Default and opt-in vehicle profiles passed actual native path, catalog,
  GStreamer factory and service-template checks. Their units are respectively
  perception/video/recording and perception/video/recording/vehicle. The combined
  runtime accepted actual generated `SetRuntimeMode` and `VehicleStatus` fields.
- The firmware native CTest passed. Both Waveshare RP2040-Zero and RP2350-Zero
  bundles built and their UF2 hashes matched their manifests. Firmware/interface
  wire headers and literal fixtures matched byte for byte.

The native build reused SDKs from the earlier private recording installation.
Profile inspection referenced that installation's model artifacts and media
plugins read-only. These checks did not repeat a complete fresh-host installer,
engine rebuild, hardware recording campaign, or physical vehicle tests.

Jah's permanent release remained `r20261104-everyday`. Its current target,
runtime-profile hash and manager/web process identities were unchanged, with
fresh status showing no conflicts, blocked units or application members. No
physical device was opened or flashed by this consolidation.

## Evidence limits and cleanup

The [recording verification](../2026-11-07-recording/README.md) retains its
original identities and limits, including the deferred viewer reconnection issue
and unqualified laptop/Wi-Fi/driving/power-loss behavior. Earlier RC bench results
remain bare-Pico observations; receiver transitions, physical PWM measurements,
actuators and powered ESC acceptance remain separate.

Only `dev` is published. Cleanup follows successful verification of the published
heads and source pins, and removes only these completed branches/worktrees plus
the temporary consolidation branches. Unrelated branches and existing archives
are preserved. No archive branches or tags are created to retain intermediate
history; transport bundles are used only for the approved verification transfer.
The source identities above remain provenance without requiring intermediate
commits to remain reachable.
