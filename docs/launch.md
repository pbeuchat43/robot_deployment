# Selectable RGB-D perception and video

This composition runs one camera and one or both TensorRT models in a ROS component
container. Camera selection and model selection are independent. The detector
retains each atomic RGB-D frame through inference; a separate bounded presentation
worker draws on a copy of that exact frame. The media process subscribes to the
annotated ROS image and encodes it with the existing runtime WebRTC path.

The current pins select detector/interface 0.2.0: `CaptureDetections` replaces
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

The six modes are `oak-cones`, `oak-coco`, `oak-both`, `d455-cones`, `d455-coco`
and `d455-both`. `log` and `logs` are identical. Restart validates and freezes
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
Models independently (Cones, COCO 80, or Cones + COCO 80), then select **Start source**. Wait for streaming acquisition
and processing observations, then **Connect video**. The requested selection and
current run are displayed separately; provider observations report actual model
and engine identity, processing counters, ages and overlay state.

For a change, select the new combination and use **Restart with selection**.
The browser requests the declared restart; runtime prepares the candidate, stops
the exact old run, waits for confirmed empty ownership, and starts the selected mode.
A cancelled, uncertain or failed stop cannot trigger a new start. Refresh/reload
does not resume the sequence. Connect video explicitly after the new source is
ready; its admission is bound to that new source run.

A stopped/lost camera is unavailable, not an empty detection result. Empty results
still publish their matching image with no boxes. Invalid spatial estimates retain
2D boxes and show `2D only`. The status/result contract exposes truncation explicitly.
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
