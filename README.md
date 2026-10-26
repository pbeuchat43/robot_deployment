# robot_composition

Reproducible selections and integration for the research robot repositories.
The current development push connects one selected D455 or OAK-D to one selected
TensorRT detector, draws on its exact retained RGB capture, and uses
`robot_runtime`'s existing ROS-image/WebRTC reference viewer.

Camera and model choices are independent. Changes require a controlled restart
of the perception workload, clearing retained frames/results and renewing the
viewer binding. Camera ownership, detection, presentation and media retain their
component boundaries.

`sources.json` pins the verified starting points; it does not claim that the new
integration is already verified. `config/cameras.json` declares reproducible
camera trials. The default measurement rate is 30 Hz; higher rates remain trials
until complete pipeline measurements support them.

Development stays on feature branches and then `dev`; `main` is not promoted as
part of this push. Hardware, reference-inference and viewer evidence will state
their tested revisions and limits separately.
