# robot_composition

Reproducible selections and integration for the research robot repositories.
The composition connects one selected D455 or OAK-D to the cone detector,
COCO 80 detector, or both TensorRT detectors, renders overlays on exact retained RGB captures, and uses
`robot_runtime`'s ROS-image/WebRTC reference viewer.

Camera and model choices are independent. Six fixed combinations are declared:
cones, COCO 80, or both for each camera. Camera/model changes use a controlled
stop/start. In dual mode, the displayed overlay can switch between models or show both while
both detectors continue running. Changing the overlay requires video reconnection.
Each model has separate inference and presentation status.
Combined presentation is a separate ROS node with a bounded exact-capture join.
Acquisition, inference, presentation and media keep their component boundaries.

- [Integration evidence and supported configurations](docs/evidence/2026-10-27-integration/README.md)
- [Shared-camera dual-detector performance experiment](docs/evidence/2026-10-28-dual-detectors/README.md)
- [Dual-mode viewer and uninterrupted overlay-switch checks](docs/evidence/2026-10-28-dual-viewer/README.md)
- [Combined overlay and both-camera switching checks](docs/evidence/2026-10-28-combined-overlay/README.md)
- [Launch and configuration](docs/launch.md)
- [Jah deployment and rollback](docs/deployment-jah.md)
- [Component and dependency pins](sources.json)
- [Named camera configurations](config/cameras.json)
- [Private deployment configuration example](config/deployment.example.json)

The default camera rate is 30 Hz and the default video ceiling is 30 fps.
Higher camera rates are evaluated separately. Observed rates, exact-overlay
checks, synthetic cases and unobserved physical checks are reported separately.

This is a minimal local composition repository using feature branches and `dev`.
No remote has been created; no installer framework or `main` promotion is part
of this milestone. Device identities, authentication material and private imagery
are excluded from source control.
