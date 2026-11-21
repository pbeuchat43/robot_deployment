# robot_deployment

Reproducible composition, installation and integration for the research robot
repositories. This repository continues the Git history of robot_composition.
The `lucid_conduct` CLI uses readable summaries and tables across all families,
including runtime operations, errors and watches. Use `--json` for scripts;
see [output and compatibility](docs/operations.md#management-and-commands).
The [deployment design](docs/design/2026-11-01-robot-deployment-design.md) and
[implementation plan](docs/plans/2026-11-03-robot-deployment.md) describe the
authorized work. The earlier installer/operator checks and six D455/OAK-D modes
passed on the existing Jah host. Fresh-host qualification remains separate. Historical
perception evidence below does not qualify a fresh installation.
The current development pins use `CaptureDetections` and the renamed capture-result
topics. Their [6 November software verification](docs/evidence/2026-11-06-capture-detections/README.md)
is separate from the earlier hardware/installation records, which retain their
original interfaces and revisions. The old everyday release was retired during
the authorized 15 November cleanup. Jah now selects `r20261116-cli-output-v2`,
with management running and application workloads stopped for operator testing;
see the [16 November CLI and deployment verification](docs/evidence/2026-11-16-cli-output/README.md).
The composition connects one selected D455 or OAK-D to the cone detector,
COCO 80 detector, or both TensorRT detectors, renders overlays on exact retained RGB captures, and uses
`robot_runtime`'s ROS-image/WebRTC reference viewer.

Camera and model choices are independent. Eight default combinations are declared:
camera only, cones, COCO 80, or both for each camera. Camera/model changes use a controlled
stop/start. In dual mode, the displayed overlay can switch between models or show both while
both detectors continue running. Changing the overlay requires video reconnection.
Each model has separate inference and presentation status.
Combined presentation is a separate ROS node with a bounded exact-capture join.
Acquisition, inference, presentation and media keep their component boundaries.

Optional visual odometry adds Off / VO / VIO for the admitted 360p30 and 720p30
camera profiles, giving 24 combinations. Select the native or Docker estimator
backend when installing a release; each run keeps that choice and its prepared
settings. See the [launch contract](docs/launch.md),
[settings and troubleshooting](docs/visual-odometry-troubleshooting.md), and
[stationary integration evidence](docs/evidence/2026-11-13-visual-odometry/README.md).
The [DepthAI 3.12.1 upgrade and clock-mapper experiment](docs/evidence/2026-11-14-oak-sdk312/README.md)
records the newer SDK, retirement of direct Python OAK video, and the upstream
timestamp limitation. The mapper remains offline. Subsequent
[clock recovery and RealSense wrap checks](docs/evidence/2026-11-14-clock-recovery/README.md)
verify the default SDK drop-and-count policy and coordinated camera/VIO recovery;
strict termination remains selectable. RealSense production pins remain
2.56.5 / firmware 5.17.0.10 after the isolated beta comparison.
The [15 November release qualification](docs/evidence/2026-11-15-vio-release-qualification/README.md)
passed the standard fresh application/Docker build, installer rerun, and both-camera
full workloads with VIO, both detectors, video and recording, including controlled
clock recovery. Physical calibration and moving-car acceptance remain separate.
The [development consolidation](docs/evidence/2026-11-15-vio-consolidation/README.md)
records the squash commits, new-pin software checks and branch disposition.
Its short OAK comparisons exposed intermittent upstream tracking failures on both
the consolidated and previously qualified selection; that performance finding
remains open despite a passing repeat. D455 passed the new smoke gates.

[Event recording](docs/recording.md) adds independent RGB, annotated and colourized
depth H.264/MP4 outputs, explicit 720p30 profiles, shared CLI/browser controls and
bounded managed history. Its [recording verification](docs/evidence/2026-11-07-recording/README.md)
is separate from the historical six-mode checks and their installed release.

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
- [Visual odometry settings and troubleshooting](docs/visual-odometry-troubleshooting.md)
- [Private site configuration example](config/site.example.yaml)

The default camera rate is 30 Hz and the default video ceiling is 30 fps.
Higher camera rates are evaluated separately. Observed rates, exact-overlay
checks, synthetic cases and unobserved physical checks are reported separately.

Development uses feature branches and `dev` in the canonical
[GitHub repository](https://github.com/pbeuchat43/robot_deployment). The published
default branch is `dev`; creating or promoting `main` is a separate milestone.
The [odometry integration record](docs/evidence/2026-11-13-visual-odometry/README.md)
maps the feature's selected commits to their tested sources; the earlier
[consolidation record](docs/evidence/2026-11-11-consolidation/README.md) retains its
original scope. Device identities,
authentication material and private imagery are excluded from source control.
