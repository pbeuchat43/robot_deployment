# robot_deployment

Reproducible composition, installation and integration for the research robot
repositories. This repository continues the Git history of robot_composition.
The [deployment design](docs/design/2026-11-01-robot-deployment-design.md) and
[implementation plan](docs/plans/2026-11-03-robot-deployment.md) describe the
authorized work. The earlier installer/operator checks and six D455/OAK-D modes
passed on the existing Jah host. Fresh-host qualification remains separate. Historical
perception evidence below does not qualify a fresh installation.
The current development pins use `CaptureDetections` and the renamed capture-result
topics. Their [6 November software verification](docs/evidence/2026-11-06-capture-detections/README.md)
is separate from the earlier hardware/installation records, which retain their
original interfaces and revisions. The installed everyday release is unchanged.
The composition connects one selected D455 or OAK-D to the cone detector,
COCO 80 detector, or both TensorRT detectors, renders overlays on exact retained RGB captures, and uses
`robot_runtime`'s ROS-image/WebRTC reference viewer.

Camera and model choices are independent. Eight fixed combinations are declared:
camera only, cones, COCO 80, or both for each camera. Camera/model changes use a controlled
stop/start. In dual mode, the displayed overlay can switch between models or show both while
both detectors continue running. Changing the overlay requires video reconnection.
Each model has separate inference and presentation status.
Combined presentation is a separate ROS node with a bounded exact-capture join.
Acquisition, inference, presentation and media keep their component boundaries.

[Event recording](docs/recording.md) adds independent RGB, annotated and colourized
depth H.264/MP4 outputs, explicit 720p30 profiles, shared CLI/browser controls and
bounded managed history. Its [recording verification](docs/evidence/2026-11-07-recording/README.md)
is separate from the historical six-mode checks and the preserved everyday release.

The [recording and RC consolidation](docs/evidence/2026-11-11-consolidation/README.md)
records the combined development sources, installed software checks and native
builds. Optional [RC vehicle integration](docs/rc-car.md) retains recording support
without enabling vehicle hardware in the default composition.

- [Integration evidence and supported configurations](docs/evidence/2026-10-27-integration/README.md)
- [Shared-camera dual-detector performance experiment](docs/evidence/2026-10-28-dual-detectors/README.md)
- [Dual-mode viewer and uninterrupted overlay-switch checks](docs/evidence/2026-10-28-dual-viewer/README.md)
- [Combined overlay and both-camera switching checks](docs/evidence/2026-10-28-combined-overlay/README.md)
- [Viewer renewal recovery and OAK empty-scene follow-up](docs/evidence/2026-10-28-viewer-acceptance/README.md)
- [Deployment implementation verification on Jah](docs/evidence/2026-11-03-deployment/README.md)
- [CaptureDetections rename and software verification](docs/evidence/2026-11-06-capture-detections/README.md)
- [Launch and configuration](docs/launch.md)
- [Installation, CLI and maintenance](docs/operations.md)
- [Jah everyday installation and commands](docs/everyday-jah.md)
- [Historical Jah deployment and rollback](docs/deployment-jah.md)
- [Component and dependency pins](sources.json)
- [Named camera configurations](config/cameras.json)
- [Configuration and immutable launch preparation](docs/configuration.md)
- [Private site configuration example](config/site.example.yaml)

The default camera rate is 30 Hz and the default video ceiling is 30 fps.
Higher camera rates are evaluated separately. Observed rates, exact-overlay
checks, synthetic cases and unobserved physical checks are reported separately.

Development uses feature branches and `dev` in the canonical
[GitHub repository](https://github.com/pbeuchat43/robot_deployment). The published
default branch is `dev`; creating or promoting `main` is a separate milestone.
The [current consolidation record](docs/evidence/2026-11-11-consolidation/README.md)
maps the selected commits to their tested sources. Device identities,
authentication material and private imagery are excluded from source control.
