# Selectable RGB-D perception and video

This composition runs one camera with optional TensorRT models in a ROS component
container. Camera selection and model selection are independent. The detector
retains each atomic RGB-D frame through inference; a separate bounded presentation
worker draws on a copy of that exact frame. The media process subscribes to the
selected unannotated or annotated ROS image and encodes it through runtime WebRTC.

The current coordinated interfaces add exposure midpoint/duration to
`CaptureReference` schema 2, `Frame` and `CaptureDetections` schema 2, including
recorded frame-index metadata. Rebuild camera, detector, recorder and odometry
bindings together. Legacy acquisition-event timestamps retain their meanings.

The preceding detector 0.2.1 with interface 0.2.0 transition made these changes: `CaptureDetections` replaces
`Batch`, `capture_detections` replaces `batches`, and both atomic overlay messages
use a `capture_detections` field (a fixed two-element array for the combined
overlay). Rebuild the interfaces, detector, presentation components and probes
together in a clean prefix. Old ROS bindings and recordings need their original
types; topic remapping alone cannot make them compatible. External capture-result
and atomic-overlay subscribers must update their bindings and field access.
Standard image/status consumers, including `robot_runtime`, need no code change.
The earlier evidence and everyday installation retain their original revisions;
the source rename does not update that installed deployment.

## Install and select a mode

Follow [installation and maintenance](operations.md) to bootstrap the selected
operator environment, prepare host prerequisites and install a complete release.
Use the private YAML [site example](../config/site.example.yaml). Source pins,
SDKs, ROS packages, native video dependencies and model artifacts are recorded
by installation; individual engine and library paths are derived from the release.
The default selects the site's camera at 30 Hz with both detectors. A camera ID
is normally absent: the provider must find exactly one compatible device.

After explicitly starting management, these commands operate the installed site:

```bash
lucid_conduct runtime catalog
lucid_conduct runtime status --fresh
lucid_conduct runtime start perception
lucid_conduct runtime start video
lucid_conduct runtime restart perception --mode d455-both
lucid_conduct runtime log perception --follow
lucid_conduct runtime stop video
lucid_conduct runtime stop perception
```

The eight modes are `oak-camera`, `oak-cones`, `oak-coco`, `oak-both`,
`d455-camera`, `d455-cones`, `d455-coco` and `d455-both`.
Camera-only modes disable inference. [Recording](recording.md) is a separate
runtime unit with explicit output choices. `log` and `logs` are identical. Restart validates and freezes
permitted startup inputs before stopping the current run. It waits for confirmed
empty ownership before starting the replacement. Invalid input leaves the old
run intact; uncertain stop prevents replacement. Management startup alone never
starts perception or video.

For student parameter changes, use the declared workspace's `config/requests.yaml`
and restart explicitly; see [configuration ownership](configuration.md).
Changing camera rate profiles or network/topology requires stopped maintenance.
`config render --release /absolute/release --output /absolute/profile.json`
can inspect a new profile without selecting it. It refuses to overwrite a file.

## Reference viewer

Open `/video` and unlock commands. Start the video service, choose Camera and
Models independently (Camera only, Cones, COCO 80, or Cones + COCO 80), then select **Start source**. Wait for streaming acquisition
and processing observations, then **Connect video**. The requested selection and
current run are displayed separately; provider observations report actual model
and engine identity, processing counters, ages and overlay state.

For a change, select the new combination and use **Restart with selection**.
The browser requests the declared restart; runtime prepares the candidate, stops
the exact old run, waits for confirmed empty ownership, and starts the selected mode.
A failed or uncertain stop cannot trigger a new start. An accepted Restart is a
durable manager operation; browser disconnection does not cancel it. Refresh/reload
does not submit another command. Connect video explicitly after the new source is
ready; its admission is bound to that new source run.

A stopped/lost camera is unavailable, not an empty detection result. Empty results
still publish their matching image with no boxes. Invalid spatial estimates retain
2D boxes and show `2D only`. The status/result contract exposes truncation explicitly.
A disconnected viewer releases its rendering demand. An active annotated
recording retains its independent demand. A slow viewer cannot hold the
inference worker. The overlay queue retains at most one pending frame plus the
frame being rendered.

The default video canvas is 640×480 at a maximum 30 fps and 2.5 Mbit/s. Square OAK
images are fitted to 480×480 with side bars. This preserves proportions. Higher
camera rates improve the availability of recent results, not the declared video
frame-rate ceiling. Observer freshness monitors arrival and camera availability;
it does not claim measured capture-to-display age in the normal UI.

## Measurement and limits

To install odometry capability, set `visual_odometry: {enabled: true, backend:
docker}` in the private site and stage a new release during maintenance. Select
`native` there for the private-prefix alternative. This is an installation choice;
there is no automatic fallback or launch-time download. Old site files retain
their eight Off modes. Enabled installations add an Off/VO/VIO selector and
`-vo`/`-vio` suffixes, such as `d455-both-vio`, for explicitly admitted 30 Hz stereo
profiles. The default remains Off. Unsupported combinations are absent.

The candidate profiles are OAK and D455 `360p30`/`720p30`. D455 VO/VIO uses native
640×480 depth/IR aligned to the chosen RGB grid and a single-threaded rectified
estimator. OAK uses raw 640×400 stereo, fixed 20 ms/ISO 800 mono exposure and a
200 Hz IMU request in VIO. See [settings and reasons](visual-odometry-troubleshooting.md).

The host camera owns acquisition in every mode. Docker owns only the estimator
and small output adapter. Initial readiness requires a fresh matched estimate
within 90 seconds; startup failure cleans up the whole run. Later tracking loss
is a health observation. Camera-body poses and explicit unknown visual support/
covariance prevent the health display from implying driving qualification.

`visual-odometry/manifest.json` records the source and interface revisions,
dependency lock, resolved package closure and immutable image or native-prefix
identity. Preparation checks the installed backend before stopping an old run.
The native installer rejects incompatible host libraries; it does not replace
OpenCV or CUDA. Software integration and stationary checks do not establish
physical mounting, timing calibration, IMU axes, moving-scene accuracy or cone
association performance.

`tools/integration_probe` is a finite diagnostic subscriber: it can compare a
received atomic overlay against a fresh render of the matching original RGB and
result, then drop full-image subscriptions and record only bounded metadata.
Build it against the installed component packages using CMake. Enable the private
diagnostic profile's `measurement_marker` only for measurement: the image carries acquisition
time and sequence protected by a CRC, allowing browser presentation callbacks to
be correlated with native results. It is not a browser-side detection join.

New probe metadata is written to `capture_detections.csv` instead of `batches.csv`.
Update external CSV readers for new runs; historical CSVs and evidence stay as recorded.

Reported browser latency uses Chromium's estimated presentation time and an HTTP
clock estimate. It is not a measurement of physical screen scanout or photons.
SDK clock mapping uncertainty, physical motion, newly arranged empty scenes and
physical USB recovery require separate observation. Read the integration evidence
before interpreting the named camera profiles as performance guarantees.

## Dual detectors and overlay selection

Use the runtime revision selected in `sources.json`. Both detector components receive the
same immutable RGB-D capture in one process, using ROS intra-process sharing.
Each retains its own bounded inference queue and TensorRT context. Camera
acquisition and alignment happen once; model preprocessing and GPU transfers
remain separate. There is no priority or rate cap between the detectors.

The cone component is named `detector_cones`; COCO is `detector_coco`, in both
single and dual modes. Under the configured namespace, each exposes its own
`capture_detections`, `status`, `overlay/frame` and `overlay/image` topics. This replaces
the earlier composition's single `detector` node path. Downstream data consumers
must select the appropriate model path and use the result capture/model identity.

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
component container. It subscribes to `camera/frames`, `detector_cones/capture_detections`
and `detector_coco/capture_detections`, sharing the original immutable input storage. It
joins both results with their exact source capture and copies RGB once for
drawing. The cone model is amber, COCO cyan, with separate model/count legends.
Both models must have completed the same capture; missing or expired partners
are skipped, and a valid empty result clears that model's boxes.

The combined join retains at most eight unmatched captures, plus one active and
one pending render. Source generation changes invalidate old work. Its dedicated
render thread keeps inference independent of drawing and video delivery.
`combined_overlay/overlay/image` feeds video; `combined_overlay/overlay/frame`
contains the two original results and image for capture-aware consumers. The
processing panel adds **Combined presentation** with join/render counters and
occupancy. It is inactive in single-model modes and idle without subscribers.

`combined_probe`, built alongside `integration_probe`, compares a finite set of
combined images against the original RGB, both independently received results,
and a fresh reference render. It releases full-image subscriptions after the
requested sample count. This check establishes exact association and pixels,
not detection accuracy or physical display latency.
