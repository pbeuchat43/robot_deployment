# Selectable RGB-D perception and video

This composition runs one camera and one or both TensorRT models in a ROS component
container. Camera selection and model selection are independent. The detector
retains each atomic RGB-D frame through inference; a separate bounded presentation
worker draws on a copy of that exact frame. The media process subscribes to the
annotated ROS image and encodes it with the existing runtime WebRTC path.

## Build and configure

Use the revisions in `sources.json`, their repository build instructions, and
`config/cameras.json`. Build camera support for both DepthAI and librealsense,
then build the detector and interfaces in the same isolated ROS workspace.
The detector's `docs/model-profiles.md` describes the pinned COCO export,
reference comparison, engine builder and artifact manifests. Build both engines
on the target Jetson. Model profile and engine hashes must agree; changing only
an engine path cannot change the model contract.

Install `robot-runtime[web]` with its native hardware-video dependencies. Copy
`config/deployment.example.json` to a private site file and fill in absolute paths,
exact SDK device IDs, a dedicated ROS domain/namespace, work/state directories,
media address/port and model files. Keep this file and credentials outside Git.
The D455 SDK serial may differ from its USB descriptor serial; use
`rgbd_camera` discovery to select the SDK device. USB write permission is required.

The ROS install must contain `rgbd_camera`, `rgbd_object_detector`, both interface
packages and `vision_msgs`. `with_ros.sh` sources Jazzy before the selected install;
a relocated install can use its `local_setup.bash`. SDK libraries must be available
through the site's declared library paths. No global shell environment is changed.

From the selected runtime virtual environment:

```bash
python tools/render_profile.py --site /absolute/site.json \
  --output /absolute/profile.json
robot-runtime-manager --profile /absolute/profile.json --state /absolute/state
```

The renderer validates the runtime schema and refuses to overwrite a profile.
The default is D455 30 Hz plus cones. It declares all six camera/model combinations
as fixed launch arguments. Higher-rate trials use a new profile while stopped:

```bash
python tools/render_profile.py --site /absolute/site.json \
  --output /absolute/profile-60-40.json --d455 d455-60 --oak oak-40
```

Use the runtime operator guide to configure authenticated HTTPS access. This
repository deliberately contains no general installer or credential management.
A persistent replacement requires stopped workloads and a rollback copy of the
matching runtime, service definitions, profile and state. Management-service
startup does not start camera or inference workloads.

## Reference viewer

Open `/video` and unlock commands. Start the video service, choose Camera and
Models independently (Cones, COCO 80, or Cones + COCO 80), then select **Start source**. Wait for streaming acquisition
and processing observations, then **Connect video**. The requested selection and
current run are displayed separately; provider observations report actual model
and engine identity, processing counters, ages and overlay state.

For a change, select the new combination and use **Restart with selection**.
The browser validates the declared launch, disconnects video, stops the exact
old run, waits for confirmed empty ownership, and starts the selected mode.
A cancelled, uncertain or failed stop cannot trigger a new start. Refresh/reload
does not resume the sequence. Connect video explicitly after the new source is
ready; its admission is bound to that new source run.

A stopped/lost camera is unavailable, not an empty detection result. Empty results
still publish their matching image with no boxes. Invalid spatial estimates retain
2D boxes and show `2D only`. The status/batch contract exposes truncation explicitly.
A disconnected viewer releases rendering demand; a slow viewer cannot hold the
inference worker. The overlay queue retains at most one pending frame plus the
frame being rendered.

The default video canvas is 640×480 at a maximum 30 fps and 2.5 Mbit/s. Square OAK
images are fitted to 480×480 with side bars. This preserves proportions. Higher
camera rates improve the availability of recent results, not the declared video
frame-rate ceiling. Observer freshness monitors arrival and camera availability;
it does not claim measured capture-to-display age in the normal UI.

## Measurement and limits

`tools/integration_probe` is a finite diagnostic subscriber: it can compare a
received atomic overlay against a fresh render of the matching original RGB and
batch, then drop full-image subscriptions and record only bounded metadata.
Build it against the installed component packages using CMake. Enable the private
site's `measurement_marker` only for measurement: the image carries acquisition
time and sequence protected by a CRC, allowing browser presentation callbacks to
be correlated with native batches. It is not a browser-side detection join.

Reported browser latency uses Chromium's estimated presentation time and an HTTP
clock estimate. It is not a measurement of physical screen scanout or photons.
SDK clock mapping uncertainty, physical motion, newly arranged empty scenes and
physical USB recovery require separate observation. Read the integration evidence
before interpreting the named camera profiles as performance guarantees.

## Dual detectors and overlay selection

Runtime 0.1.0.dev21 or later is required. Both detector components receive the
same immutable RGB-D capture in one process, using ROS intra-process sharing.
Each retains its own bounded inference queue and TensorRT context. Camera
acquisition and alignment happen once; model preprocessing and GPU transfers
remain separate. There is no priority or rate cap between the detectors.

The cone component is named `detector_cones`; COCO is `detector_coco`, in both
single and dual modes. Under the configured namespace, each exposes its own
`batches`, `status`, `overlay/frame` and `overlay/image` topics. This replaces
the earlier composition's single `detector` node path. Downstream data consumers
must select the appropriate model path and use the batch capture/model identity.

The processing panel shows separate inference and presentation observations for
each model. A model absent from a single-model launch is explicitly **Not selected
in this run**. In dual mode, choose Cones, COCO 80 or Combined under **Video source**, then
Connect video. Switching the overlay changes only the video subscription: both
inference workers, the camera, and their run/generation identities continue.
The video service has one shared selection, so other viewers must reconnect too.
Only the selected overlay normally has media demand; disconnected overlays skip
rendering. A diagnostic subscriber can independently create rendering demand.

Each detector node owns its optional presentation worker. It draws
boxes on a separate copy of the exact RGB image retained for that inference.
Dual mode also starts `combined_overlay`, a separate ROS node in that same
component container. It subscribes to `camera/frames`, `detector_cones/batches`
and `detector_coco/batches`, sharing the original immutable input storage. It
joins both results with their exact source capture and copies RGB once for
drawing. The cone model is amber, COCO cyan, with separate model/count legends.
Both models must have completed the same capture; missing or expired partners
are skipped, and a valid empty result clears that model's boxes.

The combined join retains at most eight unmatched captures, plus one active and
one pending render. Source generation changes invalidate old work. Its dedicated
render thread keeps inference independent of drawing and video delivery.
`combined_overlay/overlay/image` feeds video; `combined_overlay/overlay/frame`
contains the two original batches and image for capture-aware consumers. The
processing panel adds **Combined presentation** with join/render counters and
occupancy. It is inactive in single-model modes and idle without subscribers.

`combined_probe`, built alongside `integration_probe`, compares a finite set of
combined images against the original RGB, both independently received batches,
and a fresh reference render. It releases full-image subscriptions after the
requested sample count. This check establishes exact association and pixels,
not detection accuracy or physical display latency.
