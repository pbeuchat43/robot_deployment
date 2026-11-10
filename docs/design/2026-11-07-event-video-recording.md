# Event video recording

Copyright (c) 2026 Paul N. Beuchat. MIT License.

## Agreed outcome

Record event footage on Jah while an operator drives through the RC remote and
watches live video on a laptop. Recording is independent of the browser, Wi-Fi,
viewer overlay selection and WebRTC congestion control. Camera-only viewing and
recording are supported. Driving and autonomous-control implementation are outside
this feature; any detectors needed later may already run during manual driving.

OAK-D and D455 each gain a validated 1280x720, 30 Hz acquisition profile. Preserve
their actual geometry, calibration and field of view. Keep existing profiles and
one exclusive camera session. Initially retain paired RGB-D acquisition even when
detectors are disabled. Detector model input remains 640x640; its existing inverse
preprocessing transform maps detections into the source image for exact overlays.

Each session selects any nonempty subset of:

- Unannotated compressed RGB video.
- One annotated source: cones, COCO, or their exact-capture combined overlay.
- Depth rendered as RGB using a common, camera-independent colourization stage.

The colourized depth video is a visualization, not a metric-depth archive. Use a
fixed recorded distance range and palette, with invalid pixels distinguished.
Never substitute unrelated images or detections when an overlay is missing.

## Ownership and process layout

The camera owns acquisition and geometry. The detector owns inference and exact
overlay rendering. An optional native C++ package in robot_runtime owns recording
input, colourization, encoding and file output. Its processing core remains usable
in a composed node, but the initial deployment runs it in a separate supervised
process to isolate its lifecycle and failures from perception. Runtime owns shared
command policy, CLI, authenticated browser controls and recording observations.
robot_deployment owns composition, installation, settings, paths and verified pins.

Use existing atomic Frame, OverlayFrame and CombinedOverlayFrame interfaces with
CaptureDetections. Do not depend on viewer buffers or per-viewer encoders. Ordinary
camera Image messages do not carry the complete capture identity. External Frame
subscriptions carry depth as well as RGB; measure that cost before adding custom
transport. Remove the unnecessary overlay publication copy for atomic-only demand.

Callbacks admit bounded work and return promptly. Each output has independent
bounded input and encoding/writing work. Drop excess input before encoding, count
the loss and preserve elapsed time. Do not block acquisition or inference on disk,
and do not discard arbitrary encoded H.264 buffers. Bound finalization work too.

## Files and timing

Use hardware H.264 on NX, initially approximately 6 Mb/s for RGB and annotated
outputs, a fast preset, no B-frames and a one-second keyframe target. Depth bitrate
is an explicit independently recorded setting. Cap recording admission at 30 FPS
without changing acquisition or inference configuration.

Write separate ordinary MP4 files per output, segmented at keyframes around
30 seconds. A sudden power failure may lose the active segment; completed files
must remain intact. Use exclusive unique session directories and never overwrite
old recordings. No automatic workload restart occurs after recorder failure.

Every session has a manifest, state/counters and gap/failure information. A compact
per-frame JSONL index is enabled by default and may be disabled explicitly. With
the index disabled, exact encoded-frame-to-capture reconstruction is unavailable.
Record that limitation in the manifest. Keep integer times and sequence values
lossless in JSON/browser interfaces.

Map encoded presentation timestamps and segment identity to original source ID,
generation, stream, capture sequence, acquisition/receipt timestamps, clock domain
and fixed epoch mapping. Retain calibration, dimensions and detector provenance.
Use RGB acquisition time for RGB/overlay tracks and depth acquisition time for the
depth track on a common timeline. Track indices are independent: equal frame
numbers do not assert alignment. Missing overlays do not remove RGB/depth frames.

## Lifecycle and recovery

Start and stop are explicit shared runtime operations, separate from viewer
connections. Admission validates output choices, overlay availability and the
current declared camera owner. Freeze settings for the recording run. Browser
requests cannot supply arbitrary topics, command lines or filesystem paths.

On camera loss, finalize available segments and remain waiting for the same source
and compatible profile. When that source returns, begin new files and record the
gap and generation transition. Never silently splice generations, clock domains or
different cameras into a segment. Late old-generation frames are rejected. The
recorder does not start or restart the camera. An overlay-only outage leaves other
outputs running and is reported separately. A recorder crash/reboot leaves an
interrupted session, not an automatically resumed one.

Expose recording/session identity, output location, requested settings, overall and
per-output state, received/admitted/encoded/finalized counts, rate/overload/rejection
counts, gaps, bytes and failures. Keep acceptance, source readiness, process state
and completed file finalization distinct. Final status remains inspectable after
process exit, and stale/missing observations never imply healthy recording.

## Storage

Sessions are normally 1-2 minutes; qualify a ten-minute run. This is a sizing case,
not an automatic two-minute stop. Use a configurable managed history budget,
initially 10,000,000,000 bytes, covering videos and metadata. Reclaim only the oldest
completed sessions owned by this recorder, as whole groups. Protect active files,
unrelated content and paths outside the configured root. Keep a separate filesystem
free-space reserve. If eligible reclamation cannot provide sufficient space,
finalize and report a storage stop. Dataset retention is not part of this policy.

## Verification and release boundary

All execution checks run on reserved Jah with private files, domains, ports and
processes. Preserve r20261104-everyday: deployment 7a682ac and runtime 753ba24 are its
recorded identities. New development and isolated qualification do not relabel or
replace that installation. Permanent activation, publication, squash consolidation
and main promotion remain separate authorized actions.

Test bounded admission, independent demand, capture/timing association, generation
changes, source/overlay loss, retention, disk errors, finalization and interrupted
writers. On both cameras exercise camera-only viewing/recording, each annotation
source, all outputs together, browser disconnects and viewer source changes. Decode
completed files and compare indices with source captures. Measure CPU, memory,
encoder/GPU activity, acquisition/inference rates, viewing progress and drops.
Distinguish synthetic/software checks from observed hardware and laptop display
performance. Discuss a difficult target before prolonged optimization or changing it.

Direct image/dataset collection, seamless detector startup during existing capture,
full sensor recording/replay, observer/estimator work, MCU changes, ai4r_policy,
general viewer-stall diagnosis and fresh Nano qualification are separate follow-ups.
