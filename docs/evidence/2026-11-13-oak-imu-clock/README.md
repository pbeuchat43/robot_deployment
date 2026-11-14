# OAK IMU clock regression investigation — 2026-11-13

**Follow-up:** the [14 November capture](../2026-11-14-oak-imu-clock/README.md)
reproduced the regression and identified a device-to-host mapping step larger
than one IMU sample interval. The report below records the earlier negative
result; neither investigation changed the production timestamp policy.

**These five captures did not reproduce the regression or establish its cause.**
Five instrumented bench captures recorded 328,186 paired IMU packets
(656,372 individual sensor reports) over 1,659.416 seconds, about 27.7 minutes.
All device and host-mapped IMU timestamps advanced. No sensor sequence was
repeated, reversed or skipped, and every dequeued packet matched the SDK arrival
trace in the same order. This includes a controlled CPU-load phase.

The [earlier integrated run](../2026-11-13-visual-odometry/README.md) stopped on
`IMU acquisition clock regressed` about 61 seconds after the camera component
loaded. Its log does not contain the offending report, so these new captures
cannot reconstruct its sequence or either timestamp. The original failure remains
an open qualification limit. No production timestamp policy, SDK, firmware or
deployment was changed, and these results do not establish a fix.

## Configuration and instrumentation

The device reported **BMI270**, USB **SUPER**, and backend **DepthAI 3.9.0**.
The capture used the same OAK 360p30 + cones + native VIO configuration as the
failed run: raw 640×400 stereo at 30 Hz, requested 200 Hz raw accel/gyro,
20 ms / ISO 800 mono exposure, host IMU queue 16, batch threshold 1 and maximum
10 reports. The fixture issued no vehicle commands or lighting changes.

Camera source was `837959f700554bf548daac484ed03f6fe1b675e4`, whose runtime
implementation is `f1f64eb4862dab4b96c9b4a6c45edb238747576d`.
DepthAI remained pinned to `ac928141ef7750bf3082b5e1c319a115618660e7`.
The estimator, detector and runtime were the previously tested native artifacts.
The camera alone was rebuilt into a private overlay. Loaded-library observations
confirmed the camera process used that overlay.

Temporary instrumentation recorded:

- Each sensor's sequence, stored host-mapped timestamp and raw device timestamp.
- Host monotonic time at the SDK callback before queue insertion and at provider
  dequeue, with batch/packet position, poll snapshot size, queue occupancy and a
  message correlation value.
- RGB, depth and both stereo images' sequence and host/device timestamp pairs.
- The sensor, current/previous sequence and mapped timestamp, receipt/current
  time and signed delta if the unchanged monotonic guard failed.

Preallocated buffers held at most 262,144 packet rows per IMU stage and 65,536
image rows. Receive paths performed no file I/O; traces were written after
pipeline/device shutdown. All buffers stayed within capacity. Analysis preserved
arrival order, without timestamp sorting or deduplication. The diagnostic source
diffs and full source archive are retained with the raw evidence.

## Observations

Each row represents a separate camera start. Durations are the first-to-last SDK
arrival span, including startup/warm-up and shutdown observations. Counts are
paired packets, with one accelerometer and one gyroscope report per packet.
The signed correction is the change in `host timestamp − device timestamp`.

| Capture | Trace seconds | Packets | Smallest mapped interval (ms) | Most negative correction (ms) | Most positive correction (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Control 1 | 195.883 | 38,751 | 4.535073 | −0.355369 | +1.410738 |
| Control 2 | 315.709 | 62,446 | 4.044737 | −1.017094 | 0 |
| Control 3 | 315.665 | 62,429 | 4.280112 | −0.765675 | 0 |
| Control 4 | 315.694 | 62,432 | 4.167200 | −0.887074 | 0 |
| Baseline / CPU load / recovery | 516.465 | 102,128 | 4.120105 | −0.936744 | 0 |

The SDK host/device offset changed during capture. The first run's largest
absolute step was 1.410738 ms in both IMUs and all four image streams, consistent
with a shared clock correction. Across the IMU traces, the largest positive
adjustment was +1.410738 ms; the most negative was −1.017094 ms.
The smallest adjacent mapped IMU interval remained positive at 4.044737 ms.
These ordinary corrections demonstrate changing clock estimates, but do not
identify the original failure as a mapping error.

The last capture had 150 seconds of baseline after readiness, five CPU workers
for 150 seconds, then recovery until its 500-second measurement plus 15-second
warm-up ended. Each worker consumed 147.4–149.8 CPU seconds. Resource samples
peaked at 611% summed CPU use across eight cores and 68.125 °C junction
temperature. Host power settings were unchanged. This controlled scheduling-load
test also produced no timestamp regression or raw IMU sequence loss.

All five runs finished with camera streaming and VIO tracking, then cleaned up.
The load capture recorded two combined-IMU rejections and zero combiner overflows;
the four controls recorded neither. The raw traces contain no timestamp reversal
or sequence gap explaining those two rejections. They are not the original
terminal clock fault and are not a claim of lossless combined-IMU delivery.

An initial fixture setup attempt used a ROS domain outside the configured range
and failed before opening a camera. It is retained privately and excluded from
the five hardware captures.

## What is established, and what remains open

The production provider passes the SDK report's stored `getTimestamp()` directly
to `MotionGate`. That guard runs before IMU combination and cuVSLAM. Thus the
failure is observed in the SDK-facing acquisition path; downstream VIO does not
generate the backwards timestamp. The pinned SDK invokes queue callbacks before
insertion and drains its queue FIFO. The new traces confirm preserved order for
these five runs; they do not establish the ordering in the original failed run.

The next captured failure can distinguish the remaining cases:

| Evidence at the offending report | Interpretation |
| --- | --- |
| Sequence and device time advance; mapped time reverses | Host-clock mapping reversal |
| Sequence advances; device time reverses | Device-side timestamp assignment or clock discontinuity |
| Sequence and device time repeat or go backwards | An older/repeated report; compare arrival and dequeue order to locate it |

Luxonis previously fixed a BMI270 device-timestamp reversal in a 2023 SDK build.
That historical report does not establish recurrence in 3.9.0. See
[Luxonis issue #774](https://github.com/luxonis/depthai-python/issues/774),
[the pinned IMU timestamp fields](https://github.com/luxonis/depthai-core/blob/ac928141ef7750bf3082b5e1c319a115618660e7/include/depthai/pipeline/datatype/IMUData.hpp),
and [host-clock synchronization](https://docs.luxonis.com/software-v3/depthai/depthai-components/device#host-clock-syncing).

Retain the monotonic guard. There is no evidence here supporting sorting,
clamping, relaxing the guard, or changing the SDK version as a correction.
A longer capture under the workload that actually triggers the fault is needed
to resolve its precise cause. These are finite diagnostic observations, not
endurance, moving-vehicle or clock-accuracy qualification.

## Evidence and preservation

[summary.json](summary.json) records the per-run counters, signed clock margins,
artifact hashes and load phases without device/session identities.
[preservation.json](preservation.json) confirms all five runtime states unblocked,
owned cgroups empty, helpers stopped, and unchanged packages, power mode,
Docker inventory and selected deployment. [release.json](release.json) confirms
the hardware reservation was released.

The private archive contains 153 numeric/log/source/provenance files, 25,062,102
compressed bytes. Its downloaded SHA-256 was verified:

```text
358d748e850ce95cca06c50a4910580f88ff2644e634be26bb69bd57b868318d
```

The archive's `source-hashes.txt` is the initial build/instrumentation receipt;
`evidence-files.sha256.json` and the public summary identify the final analysis
files. The reservation-release receipt was collected separately after archiving.
Raw device/process identities stay private. The retained evidence contains no
image pixels or recordings.
