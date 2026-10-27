# Operator-assisted physical checks - 27 October 2026

The operator exercised deployed release `rgbd-20261027-dev20` in the laptop
browser while a metadata-only ROS observer recorded camera status, detector
status and detection batches on reserved Jah. No images or browser telemetry
were recorded by this observer. Visual statements below are operator reports;
rates, counters, empty batches and state transitions come from the recording.
Observation windows include operator and waiting time, not continuous motion.
Camera/model switches and initial startup are excluded from steady-state rates.

## Motion and clearing

| Camera / model | Camera / inference Hz | Operator observation | Recorded continuous zero detections |
| --- | ---: | --- | ---: |
| D455 / cones | 29.96 / 29.96 | No stuck boxes or freezes; boxes cleared and returned | 117.64 s |
| D455 / COCO | 29.92 / 29.92 | Laptop/person motion; no stuck boxes or freezes; labels cleared and returned | 42.08 s |
| OAK-D / cones | 30.00 / 30.00 | Smooth motion; no stuck boxes or freezes; boxes cleared and returned | 7.00 s |
| OAK-D / COCO | 30.00 / 30.00 | Smooth motion and no stuck boxes; labels cleared and returned; one video freeze | 3.60 s |

Rates use the motion observation windows. D455 empty-scene windows also sustained
about 29.96 Hz. The operator pointed at the ceiling to obtain COCO empty scenes.
Subsequent nonempty batches confirmed detection return. Camera and detector stayed
streaming in these windows, with no camera sequence gaps or pairing rejections,
detector stale/rejected results or failures, or overlay failures. These counters
do not establish browser display continuity.

Both OAK modes demonstrated clearing and return, but the recorded uninterrupted
empty intervals were shorter than the requested ten-second hold. A full ten-second
continuous zero-detection hold remains unverified for both OAK modes. Intermittent
nonzero predictions in the COCO empty-scene interval were not visually labelled
or independently assessed as false positives.

## OAK-D / COCO viewer interruption

The operator reported one freeze of about five seconds and clicked **Connect
video** again. Spontaneous recovery was not established. The recording contains
a matching 5.20-second interval in which overlay rendering did not advance and
the no-consumer counter rose by 156, while inference processed 156 more frames.
This counter means neither overlay image topic had a subscriber. Camera capture
and inference continued; the largest recorded acquisition interval in the
diagnostic window was 133.54 ms, rather than a multi-second acquisition stall.

This points to a viewer connection/demand interruption but does not identify why
the subscription disappeared. Browser telemetry was not retained for that event.
The [28 October follow-up](../2026-10-28-viewer-acceptance/README.md) reproduced
lost demand from one failed subscription renewal and deployed bounded recovery
in runtime dev22. The original event's exact trigger remains unproven. Both
ten-second OAK empty-scene checks subsequently passed. The operator still saw
brief, automatically recovering stalls, so uninterrupted physical viewing remains
unaccepted and further diagnosis was deferred at the operator's request.

## Physical USB disconnect and recovery

Both cameras were physically unplugged while COCO was running. New frames and
detection batches stopped; the detector became unavailable. OAK-D reported
`camera connection/pipeline unavailable`; D455 reported `raw_acquisition_stalled`.
Frame counters remained unchanged while the error persisted. The overall runtime
could remain running while its camera was in error.

For each camera, the operator confirmed that the error remained after replugging
and before manual restart. **Restart with selection**, followed by **Connect
video**, restored video and detection. Each restart produced a different runtime
and capture generation. OAK-D sustained approximately 30 Hz for the 125.85-second
recovery observation; D455 sustained approximately 29.96-29.98 Hz for 53.98 seconds.
Neither recovery window recorded capture gaps, camera rejection, detector stale
or rejected results, detector failure or overlay failure. Manual restart after
a terminal camera disconnect is the implemented behavior, not an automatic USB
reconnect guarantee.

The operator installed the permanent D455 USB rule before these checks. It was
verified before use and again after physical replugging: the new USB device node
belonged to the configured local operator, had mode `0660`, and could be opened
for read/write access. The device node changed across replugging. Private USB
identities and paths remain outside source control. No additional permission step
is pending; reboot behavior was not tested.

## Evidence retention and cleanup

Raw metadata, per-phase JSON reports, operator observations, USB permission
checks and the cleanup audit are retained privately on Jah under
`~/.local/state/rgbd-verification/physical-20261027`. Finalized CSV SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `batches.csv` | `3be9a97d9c6ed1dd61720b30d4f2f45398a57c91544a13705f5860629b8dea56` |
| `camera.csv` | `c853658253ca932d1a98dded9762d2b8ffdacf4120fc0d3bc61d870d34b867de` |
| `detector.csv` | `6c22f6656397422b6f56607e34382353669d9b802e8b12d7a46f38e6ba9e5f96` |

The temporary observer was stopped and its exact verification reservation was
released. The operator's D455/COCO and video workloads were preserved running;
both persistent management services remained active. No software implementation
or deployment was changed during these physical checks.

Remaining broader evidence boundaries include surveyed distance accuracy,
physical display scanout, long-duration load, multi-viewer behavior and reboot
recovery. These checks do not extend previously measured frame-rate or model
accuracy claims.
