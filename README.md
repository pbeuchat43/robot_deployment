# robot_composition

Reproducible selections and integration for the research robot repositories.
The current feature branch connects one selected D455 or OAK-D to one selected
TensorRT detector, renders overlays on the exact retained RGB capture, and uses
`robot_runtime`'s ROS-image/WebRTC reference viewer.

Camera and model choices are independent. Four fixed combinations are declared:
D455/cones, D455/COCO 80, OAK-D/cones, and OAK-D/COCO 80. Selection changes use a
controlled stop/start and require explicit video reconnection to the new source.
Acquisition, inference, presentation and media keep their component boundaries.

- [Launch and configuration](docs/launch.md)
- [Component and dependency pins](sources.json)
- [Named camera configurations](config/cameras.json)
- [Private deployment configuration example](config/deployment.example.json)

The default camera rate is 30 Hz and the default video ceiling is 30 fps.
Higher camera rates are evaluated separately. Observed rates, exact-overlay
checks, synthetic cases and unobserved physical checks are reported separately.

This is a minimal local composition repository on `feature/rgbd-integration`.
No remote has been created; no installer framework or `main` promotion is part
of this milestone. Device identities, authentication material and private imagery
are excluded from source control.
