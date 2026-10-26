# RGB-D perception/viewer integration — 27 October 2026

Ten camera/model/rate cases completed on reserved Jah with zero cleanup errors.
Each case verified 25 exact original-RGB/batch/overlay matches before releasing
full-image diagnostic subscriptions. The finite measurement windows were about
45 seconds for the first three 30 Hz cases, 15 seconds for OAK/COCO at 30 Hz, and
30 seconds for each higher-rate case. These are observed short runs, not endurance
or model-quality acceptance.

## Rates and latency

| Camera profile | Model | Camera / inference Hz | Display captures/s | Result p50 / p95 ms | Presentation p50 / p95 ms |
| --- | --- | ---: | ---: | ---: | ---: |
| d455-30 | cones | 29.96 / 29.98 | 23.35 | 36.2 / 40.2 | 133.0 / 155.6 |
| d455-30 | coco | 29.96 / 29.98 | 23.26 | 38.7 / 42.9 | 135.1 / 157.6 |
| oak-30 | cones | 30.00 / 30.00 | 26.35 | 55.4 / 58.0 | 153.0 / 170.0 |
| oak-30 | coco | 30.00 / 30.00 | 23.08 | 59.7 / 63.8 | 162.3 / 179.7 |
| d455-60 | cones | 59.74 / 59.67 | 23.87 | 34.5 / 44.8 | 137.6 / 161.8 |
| d455-60 | coco | 59.77 / 59.74 | 25.17 | 37.0 / 47.0 | 138.1 / 160.2 |
| oak-40 | cones | 40.00 / 40.00 | 25.72 | 56.3 / 60.9 | 155.8 / 165.9 |
| oak-40 | coco | 40.00 / 40.00 | 26.75 | 59.2 / 63.8 | 154.6 / 170.8 |
| oak-35 | cones | 35.00 / 35.00 | 26.51 | 55.9 / 59.0 | 155.9 / 173.9 |
| oak-35 | coco | 35.00 / 35.00 | 26.57 | 59.3 / 62.4 | 158.0 / 172.4 |

Acquisition-to-result is the completed batch age in the host monotonic clock.
Acquisition-to-presentation uses a CRC-protected capture marker decoded from
the WebRTC image and joined to the native batch, with Chromium
`requestVideoFrameCallback.expectedDisplayTime`. The minimum-RTT HTTP clock
estimate contributed at most ±5.5–11.1 ms across these cases. SDK clock mapping
error, timestamp precision and physical scanout are additional unmeasured terms.
The browser was headless Chromium on Jah; this is not a remote laptop/Wi-Fi or
physical-screen measurement. No negative latency samples were observed.

Video was fixed at 640×480, at most 30 fps, 2.5 Mbit/s, hardware H.264. Square
OAK images were fitted into that canvas without distortion. Displayed unique
captures were about 23–27/s, below the 30 fps ceiling. An initial pacing rule
discarded frames around the 30 Hz boundary; the bounded phase-preserving update
improved the observed path, but a full 30 displayed fps target is not claimed.
Higher acquisition rates did not consistently reduce presentation latency, so
30 Hz remains the default. No further performance optimization was attempted.

D455 60 Hz recorded one camera sequence gap in the cone run and one replaced
pending inference frame in each model run. No camera pairing rejection, detector
failure/stale rejection, or overlay failure/replacement was observed during the
measurement windows. Reported receive/processed counter deltas can differ by one
at a sampling boundary. The observed pending queue never exceeded one.

The browser reported 0–22 dropped video frames per case. Marker decode rejected
2–8 callbacks per case; a further 0–10 decoded captures per case lacked a matching
received batch record and were excluded from latency. These are measurement/
transport losses, not proof of a wrong overlay association. The separate exact
pixel/capture comparison passed all 250 samples. Full counts, quantiles and
timestamps are in [integration-summary.json](integration-summary.json).

## Resource observations

CPU percentages below use 100% for one CPU core. RSS is the peak sum of process
RSS within the named cgroup, so shared pages can be counted more than once. The
JSON also records charged cgroup memory, host memory/swap, browser/manager/web
cost and the metadata probe. GPU values are whole-host GR3D utilization sampled
by `tegrastats` once per second, not isolated per-model kernel timing. Power mode
remained the existing 15 W setting.

| Camera profile | Model | Perception CPU % | Video CPU % | Perception / video peak RSS MiB | GPU p50 / max % |
| --- | --- | ---: | ---: | ---: | ---: |
| d455-30 | cones | 91 | 33 | 732 / 397 | 22 / 40 |
| d455-30 | coco | 91 | 34 | 737 / 400 | 18 / 39 |
| oak-30 | cones | 37 | 66 | 864 / 405 | 12 / 40 |
| oak-30 | coco | 49 | 57 | 870 / 398 | 20 / 38 |
| d455-60 | cones | 157 | 40 | 737 / 397 | 39 / 53 |
| d455-60 | coco | 154 | 43 | 741 / 400 | 38 / 57 |
| oak-40 | cones | 46 | 66 | 865 / 405 | 28 / 40 |
| oak-40 | coco | 58 | 66 | 869 / 410 | 29 / 38 |
| oak-35 | cones | 42 | 66 | 863 / 399 | 31 / 39 |
| oak-35 | coco | 53 | 64 | 867 / 403 | 31 / 39 |

## Behavior and evidence boundaries

The scene was the existing lit room with cones and ordinary objects. Cone batches
reported blue/yellow cones. COCO reported labels including keyboard, mouse, laptop,
TV and person; these are model predictions, not ground-truth annotations. All
reported spatial estimates in these short live windows were marked valid by the
algorithm. That does not establish metric accuracy or general-object spatial
quality. The previously observed D455 invalid-spatial cases remain relevant.

The final OAK/COCO recovery case established:

- An eight-second blocked browser main thread did not stop perception: 240 more
  batches were processed. Disconnection also left inference progressing and
  caused overlay no-consumer counters to increase in every case.
- Unloading the camera component made the detector unavailable and video stale.
  This is simulated provider loss, not a physical USB unplug.
- Controlled restart cleared the old run, produced a different capture generation,
  kept video disconnected, and succeeded after explicit reconnect.
- Camera/model changes used fixed declared modes and renewed the source run.
  Every case ended with no blocked workload/cgroup and no cleanup errors.

The native detector/core/adapter/overlay checks separately cover empty results,
invalid depth retaining 2D boxes, truncation, rectangular/square transforms,
generation supersession, queue replacement and a stalled ROS subscriber. Saved
image reference inference covers both models on eight images each, including
ordinary-object photos, retained captures and blank rectangular/square fixtures.
Those synthetic and saved-image checks are not live empty-scene or motion tests.

Unobserved: physical motion, a newly arranged empty scene, physical USB unplug/
replug, surveyed distance accuracy, physical screen scanout, long-duration load,
multi-viewer performance and post-reboot behavior. The user explicitly chose the
current static scene and left the cameras/lights available overnight. OAK 60 Hz
is still excluded because the prior acquisition evidence found pairing failures;
the historical OAK IMU offending sample was not reproduced and IMU was disabled
for these integration runs.

## Reproduction and identity

Use [the launch guide](../../launch.md), [component pins](../../../sources.json),
[camera profiles](../../../config/cameras.json) and the detector model export/build
instructions. [Engine artifact hashes](engine-artifacts.json) identify the exact
target-built engines and manifests. The TensorRT path is shared by both cameras.
The unchanged camera revision is `0f4b82958f0d7798f0bf911641d0aa67084cc927`; the
tested detector implementation is `01e36cb`. The first three 30 Hz cases use
runtime `07fe8b3`; remaining cases use `cbfed17`, whose only subsequent functional
change refreshes identity before explicit media admission. Image/encoding code is
identical between those two revisions. The source manifests in the component
repositories bind the actual tested bytes and packaged artifacts.

Private imagery, raw tensors, full native CSVs, browser capture markers, resource
samples and failed fixture attempts are retained in the task archive, outside Git.
The public summary includes their numerical outcomes without device serials or
authentication material. No `main` branch was promoted.


The verified development histories were preserved both as archive branches and
local Git bundles before squash consolidation. Detector `dev` is `cca101c` and
runtime `dev` is `9c5f6a9`; both were published with their archive branches. Their
squashed trees exactly match the archived feature tips. This composition remains
local on its feature branch with no remote. Camera source and every `main` branch
remain unchanged.


The final cleanup audit checked 13 campaign profiles, found no remaining task
browser profiles, confirmed both selected workloads stopped/unblocked, released
the exact hardware reservation, and verified restoration of the D455's original
owner/mode/ACL. Persistent management services remain selected. The prepared
permanent D455 permission helper still requires the operator's sudo step.
