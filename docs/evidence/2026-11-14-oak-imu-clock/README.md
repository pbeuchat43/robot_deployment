# OAK IMU clock regression reproduced — 2026-11-14

Follow-up: the [DepthAI 3.12.1 comparison and offline mapper prototype](../2026-11-14-oak-sdk312/README.md)
record the subsequent SDK upgrade and replay results. The findings below retain
their original DepthAI 3.9.0 scope.

**The regression is reproduced and localized to the device-to-host timestamp
mapping supplied by DepthAI.** Raw IMU device time and sequence advanced, while
the stored host-synchronized timestamp moved backward. A −6.032729 ms change in
the mapping offset exceeded the 5.052486 ms sample interval, producing a
−0.980243 ms mapped interval. The reversal was already present at the SDK callback
before queue insertion. The unchanged monotonic guard correctly stopped acquisition.

This establishes the failure mechanism for the captured occurrence. The reason
the upstream clock synchronization made that correction remains unresolved.
The earlier uninstrumented occurrence cannot be reconstructed independently.
No production timestamp policy, SDK/firmware selection, camera configuration or
deployment selection changed. All feature branches remain unmerged; this is
diagnostic evidence, not a fix or endurance qualification.

## Captures

Following the [five shorter captures](../2026-11-13-oak-imu-clock/README.md),
two attempts targeted 3,600 measured seconds after a 15-second warm-up, stopping
early on a camera fault. Both used OAK 360p30 + cones + native VIO, raw 640×400
stereo at 30 Hz, requested 200 Hz raw accel/gyro, and the existing exposure,
batching and queue settings. There was no CPU-load phase or vehicle command.
Durations below are first-to-last SDK arrival spans, including startup/warm-up
observations; neither attempt completed an hour.

| Attempt | Trace seconds | Paired IMU packets | Stop reason |
| --- | ---: | ---: | --- |
| 1, started 13 November AEDT | 660.219936 | 130,507 | Mapped acquisition timestamp 5.063184 ms ahead of provider receipt, exceeding the existing 5 ms limit |
| 2, started 14 November AEDT | 258.187206 | 51,061 | Mapped acquisition timestamp regressed by 0.980243 ms |

Together the traces contain 181,568 paired packets, or 363,136 individual sensor
reports, over 918.407142 seconds. Every dequeued packet matched the arrival trace
in order. Both runs had zero missing, repeated or reversed sensor sequences,
zero raw device-clock regressions, and zero trace overflow. The second run has
one mapped reversal in each sensor at the same packet, representing one incident.
Both fixtures report failure, as expected for terminal camera faults, with empty
cleanup-error lists.

## Exact counterexample

The following are consecutive accelerometer reports in attempt 2. Gyroscope
sequences 51,059 → 51,060 have the same timestamps and deltas.

| Field | Previous report | Offending report | Change |
| --- | ---: | ---: | ---: |
| Accelerometer sequence | 51,064 | 51,065 | +1 |
| Raw device time (ns) | 260,668,220,532 | 260,673,273,018 | +5,052,486 |
| SDK host-synchronized time (ns) | 5,288,945,057,053 | 5,288,944,076,810 | −980,243 |
| Host minus device offset (ns) | 5,028,276,836,521 | 5,028,270,803,792 | −6,032,729 |

The same stored timestamp pairs appear at SDK arrival and provider dequeue.
The offending packet took 0.929623 ms from callback to dequeue; no queue
reordering or altered timestamp is needed to explain the guard failure. The
guard runs before the IMU combiner and cuVSLAM. The last nearby image reports
precede the correction, so this capture does not show whether subsequent image
timestamps received the same step.

The pinned DepthAI source defines and serializes separate host-synchronized and
raw device timestamp fields in each IMU report. Its getters return the stored
values; the host parser deserializes those reports before the queue callback.
This places the observed reversal in the device-produced host-synchronized
metadata, upstream of the provider's admission logic:

- [IMU fields, getters and serialization](https://github.com/luxonis/depthai-core/blob/ac928141ef7750bf3082b5e1c319a115618660e7/include/depthai/pipeline/datatype/IMUData.hpp#L31-L97).
- [IMU message deserialization](https://github.com/luxonis/depthai-core/blob/ac928141ef7750bf3082b5e1c319a115618660e7/src/pipeline/datatype/StreamMessageParser.cpp#L269-L273).
- [Callback before queue insertion](https://github.com/luxonis/depthai-core/blob/ac928141ef7750bf3082b5e1c319a115618660e7/src/pipeline/MessageQueue.cpp#L145-L146).

DepthAI continuously synchronizes the device clock to host monotonic time.
The offset step is consistent with a device-side timesync correction. The
[pinned host responder](https://github.com/luxonis/depthai-core/blob/ac928141ef7750bf3082b5e1c319a115618660e7/src/device/DeviceBase.cpp#L1308-L1321)
and [configuration RPC](https://github.com/luxonis/depthai-core/blob/ac928141ef7750bf3082b5e1c319a115618660e7/src/device/DeviceBase.cpp#L2020-L2027)
show the host side of that service, but do not expose why the firmware chose this
correction. The [vendor clock documentation](https://docs.luxonis.com/software-v3/depthai/depthai-components/device#host-clock-syncing)
describes the separate clocks and ongoing synchronization. This evidence does
not identify a specific firmware estimator defect, transport trigger or host
scheduling event. It also does not reproduce the historical BMI270 raw-device
timestamp reversal: raw device time remained strictly increasing here.

## Other clock fault in attempt 1

Attempt 1 stopped on the existing future-time check. The offending timestamp
was already 5.258283 ms ahead of the SDK callback observation and 5.063184 ms
ahead of provider receipt. The adjacent raw and mapped timestamps both advanced
5.059894 ms; there was no offset step at that packet. A stable offset had been
used for about 2.75 seconds. The trace alone cannot distinguish a stale clock
estimate from changing delivery delay as the reason this crossed the limit.

Earlier in that run a −5.008701 ms offset change left only a +0.046555 ms mapped
interval, a near miss for the monotonic guard. The largest positive correction
was +119.625698 ms. These observations and the separate future-time stop remain
qualification concerns; the second attempt's counterexample establishes the
backward-timestamp mechanism directly.

## Instrumentation and verification

Camera source was `837959f700554bf548daac484ed03f6fe1b675e4`, with runtime
implementation `f1f64eb4862dab4b96c9b4a6c45edb238747576d`. DepthAI remained 3.9.0
at `ac928141ef7750bf3082b5e1c319a115618660e7`; the device reported BMI270.
Only the private camera overlay was rebuilt. Loaded-library records identify
that overlay; the native estimator, detector and runtime artifacts were reused.
The production monotonic condition and future tolerance were preserved. Private
instrumentation only added tracing and a more detailed monotonic-error message.

Fixed buffers retained 1,048,576 paired packet rows per IMU stage and 524,288
image rows, about 244 MiB in total. Receive paths performed no file I/O. After
pipeline/device shutdown, the fixture wrote binary snapshots and explicit
completion/count/overflow metadata. The diagnostic build and a focused native
writer/Python decoder check passed, covering signed sequence values, unsigned
correlation values, row order, binary layout, capacity and overflow accounting.
Both actual captures passed byte-size/completion validation with zero overflow;
analysis preserved acquisition order without sorting or deduplication.

The experiment fixture also checked final freshness before aggregating the
long-run results, using the actual capture-end time. This avoids falsely
expiring observations while computing summaries. These private fixture changes
do not alter camera clock admission. Production software suites were not rerun
for this documentation-only repository change.

## Evidence and preservation

[summary.json](summary.json) contains sanitized counters, the exact counterexample
at both observation stages, signed clock steps, source hashes and binary hashes.
[preservation.json](preservation.json) confirms both runtime states unblocked,
owned cgroups empty, fixture/resource processes stopped, and unchanged host
packages, power mode, Docker inventory and selected deployment.
[release.json](release.json) records verified reservation-process exit.

The private archive retains 96 numeric/log/source/provenance files, 12,428,541
compressed bytes, including both complete traces, full owned-unit journals,
instrumented sources, baseline camera source and a per-file SHA-256 manifest.
The downloaded archive SHA-256 matched:

```text
4e9073651db2cb2787369c4e750bd30e58b3db999280f64e90fbd40a4896c1b6
```

The initial `source-hashes.txt` records build/start identities; the final archive
manifest and summary identify the final analysis helpers. Reservation release
was verified separately after archiving. Raw device/process identities stay
private; no image pixels or recordings were retained.
