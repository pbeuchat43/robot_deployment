# Dual-detector selection and uninterrupted overlay changes

Both cameras now support Cones, COCO 80, or Cones + COCO 80. Each selected model
has its own inference and presentation status. In dual mode, Video source selects
the displayed model while both inference workers continue. Changing this shared
video source disconnects viewers and requires Connect video again. Changing the
camera or selected models still uses the existing controlled restart.

The source implementation is composition `e035513` with runtime `1f16c1b` and
`015c177` (0.1.0.dev21). `sources.json` records the consolidated revisions.
Camera and detector implementations, TensorRT engines and the 15 W power mode
were unchanged. The single-model node paths are now `detector_cones` and
`detector_coco`, matching dual mode; see [launch instructions](../../launch.md).

## Observed checks

All six camera/model combinations passed across the recorded campaigns. The
selected evidence contains 200 exact overlay comparisons: 25 per active model
per configuration. The native probe compares each overlay with a fresh render
of its matching original RGB capture and result batch, then releases full-image
subscriptions. [Hardware results](hardware.json) record each case.

The final release was checked from its installed paths with both cameras in
dual mode, selecting cones, COCO, then cones again. Camera/perception and video
run identities remained unchanged; both detector generations remained unchanged
and both processed counters advanced through every switch. Explicit reconnection
produced new WebRTC frames, checked with presentation callbacks. In single-model
runs, the absent model was inactive with no stale sample or upstream subscription,
and its video choice was disabled.

Runtime verification passed 147 unit tests and 18 packaged browser checks. The
final installed source files matched their recorded hashes. The final browser-only
review change clears an inactive label on observation disconnection; it does not
change native perception or video switching. Its packaged regression passed.
The pinned [runtime software report](https://github.com/pbeuchat43/robot_runtime/blob/c2b2b6d16964b00caa543006d814c9b112520843/docs/evidence/2026-10-28-video-source-choices/software.json)
contains the individual checks and package hashes.

## Retained failures and limits

The first harness used the image-snapshot RPC instead of the status RPC and timed
out despite healthy native processing. A diagnostic run confirmed the mistake and
was stopped cleanly. The corrected campaign passed five configurations, then
failed a short video-frame-progress assertion during OAK dual mode's COCO choice.
That window did not retain its before/after counters, so its cause is undetermined.
A focused OAK dual rerun passed with frame-count and media-state diagnostics; both
cameras then passed from the final release using presentation callbacks. All
campaigns cleaned up, and the original persistent workloads were preserved.

This is finite functional evidence using headless Chromium on Jah. It is not a
sustained display-rate benchmark, multi-viewer hardware test or physical display
scanout measurement. No new motion, empty-scene or USB tests were performed, and
the previously accepted physical-check findings were not reinvestigated. The
[earlier data-only performance experiment](../2026-10-28-dual-detectors/README.md)
remains the relevant comparison of single and dual inference load. No combined
overlay renderer, detector priority policy or autonomous driving was validated.

## Deployment

The selected release is `rgbd-20261028-dev21`. The manager and web services passed
fresh-status and HTTPS checks; served browser assets matched the installed package.
Camera/perception and video were left stopped. Service files, enabled state,
credentials/TLS and power configuration were preserved. The previous dev20 release
and a coherent stopped-state configuration/database backup were retained.
[Deployment evidence](deployment.json) and [rollback instructions](../../deployment-jah.md)
describe the selection. A rollback round trip was not performed.
[Final cleanup](cleanup.json) confirmed no isolated processes remained and released
the shared host reservation with both workloads stopped and power unchanged.

Raw reports and diagnostic imagery remain private on Jah under
`~/.local/state/rgbd-verification/dual-viewer-20261028`. The public JSON omits
credentials, device identities, private imagery and media-session details.
