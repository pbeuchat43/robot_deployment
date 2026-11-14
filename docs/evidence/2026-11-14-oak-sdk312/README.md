# DepthAI 3.12.1 and offline clock mapper — 14 November 2026

**DepthAI 3.12.1 builds and runs with the stack, but does not remedy the retained
class of OAK clock faults.** The instrumented capture stopped on a timestamp
5.164938 ms ahead of provider receipt, exceeding the unchanged 5 ms allowance.
It also recorded a +182.022001 ms SDK mapping-offset step. A shared local mapper
prototype passed the retained fault replays at negligible compute cost, but its
clock estimate can lag and its absolute accuracy is unverified. It remains offline.

The feature branches select camera `0.4.1` / DepthAI `3.12.1`, runtime
`0.1.0.dev29` and deployment `0.1.0.dev7`. The legacy runtime Python OAK capture
route and optional SDK-copy branch are retired; GStreamer preparation, ROS video
and V4L2 remain. Production timestamp guards are unchanged. Nothing was merged
or selected as the persistent deployment.

## Upstream and hardware result

Release notes from 3.10.0 through 3.12.1 and the intervening host time-sync code
did not identify a verified remedy. This does not prove unchanged firmware:
the embedded synchronization implementation was not established from host code.
See the [3.12.1 release](https://github.com/luxonis/depthai-core/releases/tag/v3.12.1),
[pinned host source](https://github.com/luxonis/depthai-core/blob/da14320483864f7cdabada9e70d4d6a2115eff9a/src/device/DeviceBase.cpp)
and [historical offset-jump issue](https://github.com/luxonis/depthai-core/issues/742).
The old experimental time-sync branch is not a verified fix for this stack.

One capture targeted 3,600 measured seconds after a 15-second warm-up, using
the preceding campaign's OAK 360p30 + cones + native VIO settings, binary
arrival/dequeue/image instrumentation, batching, exposure and strict guards.
Only the camera/SDK overlay changed for this comparison. The running camera's
loaded libraries confirmed the private 3.12.1 SDK. Runtime `dev28` and deployment
`dev6` from the existing private fixture were retained; their exact installed
package manifests are hashed in [summary.json](summary.json). The new runtime
and installer were verified separately below.

| Observation | Result |
| --- | ---: |
| First-to-last SDK arrival span, including warm-up | 340.346823 s |
| Paired accel/gyro packets at each trace stage | 67,266 |
| Missing/repeated/reversed sensor sequences | 0 |
| Raw device-time regressions / mapped-time regressions | 0 / 0 |
| Arrival/dequeue ordering mismatches / trace overflow | 0 / 0 |
| Offending acquisition lead at callback / dequeue | 5.635874 / 5.164938 ms |
| Offending callback-to-dequeue delay | 0.470936 ms |
| Raw and SDK interval at the offending sample | both +5.046823 ms |
| Largest SDK offset change | +182.022001 ms |
| Resulting SDK IMU interval at that positive step | 187.073171 ms |
| Largest negative offset change, without a reversal | −3.881509 ms |
| VIO frame-gap warnings / maximum warned interval | 5 / 215.355507 ms |
| Final association epoch / combined-IMU rejections | 10 / 9 |

The final fault is another future timestamp, **not a reproduction of the backward
step on 3.12.1**. Its immediate raw and mapped intervals are equal, with no offset
step at that packet. Like the earlier future case, the SDK timestamp is already
ahead at the pre-queue callback. The trace establishes no firmware correction
trigger or calibrated clock accuracy. This failed early attempt is not an
hour-long qualification, nor a comparative failure-rate study.

## Shared local mapper prototype

The reviewable [prototype and reproduction instructions](https://github.com/pbeuchat43/rgbd_camera/tree/dev/experiments/oak-clock-mapper)
keep `clock=sdk|local` separate from `fault_policy=stop|drop`. Required comparisons
are local/strict, SDK/drop-and-count, and SDK/strict as control. They link the
unchanged production `MotionGate` and `ImuCombiner`.

One mapper uses existing provider dequeue receipts in the polling thread. It
needs no new queue, callback handoff, thread, service or per-sample allocation.
It suppresses one second of startup samples, then uses a two-second lower-envelope
window with a 5 ms margin and continuous bounded-rate corrections (±5,000 ppm).
Recent mapping segments are retained so delayed image events use the same clock
function as IMU samples. These are explicit experimental constants, not calibrated
production settings.

The [replay results](replay.json) include full input hashes and per-stream metrics.
They cover the [earlier future and backward failures](../2026-11-14-oak-imu-clock/README.md)
and the new 3.12.1 future failure, including the large positive SDK steps.

| Retained trace | Local accepted IMU reports per channel | Startup drops per channel | Local strict faults / combined rejections | Maximum mapped IMU / image age |
| --- | ---: | ---: | --- | --- |
| 3.9.0 future/positive-step case | 130,309 | 198 | 0 / 0 | 221.929 / 245.712 ms |
| 3.9.0 backward-step case | 50,862 | 199 | 0 / 0 | 16.109 / 39.804 ms |
| 3.12.1 future/positive-step case | 67,067 | 199 | 0 / 0 | 210.125 / 232.227 ms |

No mapped image event regressed or exceeded receipt after startup; no combiner
overflow occurred. Maximum local combined interval was below 5.50 ms. Maximum
RGB/depth event skew was 0.101 ms, stereo event skew 0.028 ms. Image diagnostics
concern event timestamps only; retained traces lack actual exposure midpoints,
pixels and pose outputs, so this does not establish VIO alignment or pose quality.

SDK strict replay reproduced each terminal fault. SDK graceful replay counted
and dropped one invalid report per sensor per trace, without stopping processing.
The retained inputs end at the fatal packet; **continued hardware recovery is
not observed**. A bounded synthetic check verifies acceptance of a later valid
sample after dropped backward/future timestamps. Forward SDK steps still pass
the existing gate and caused 4/9 combined-IMU rejections in the future traces.
Graceful handling therefore does not repair every timing disturbance.

The final 100,000-iteration microbenchmark on Jah measured an update plus two
conversions at 96 ns median, **128 ns p95**, 160 ns p99 and 19.010 µs maximum;
the full loop took 16.222 ms. Mapper state occupied **1,720 bytes**. This is a
short cost measurement including measurement-clock overhead, not a deadline
guarantee. An initial callback-receipt variant and its results remain in private
evidence; the final variant avoids needing that handoff.

Compute cost appears negligible, and steady-state conversion adds no buffering
wait. The material risks are startup suppression, clock-estimate lag, absolute
timestamp error and recovery policy. In particular, the roughly 246 ms mapped
image age is not proven physical latency: the conservative estimate contributes
to it. Independent timing evidence and a live integration observing recovery,
exposure midpoints and VIO are needed before choosing this mapper as a default.
No further parameter tuning was used to conceal that limitation.

## Upgrade, retirement and verification

Exact implementation selections:

- Camera `66262c074c0997e97e3081b9a14a14bb9a782024`; SDK
  `da14320483864f7cdabada9e70d4d6a2115eff9a` (`v3.12.1`).
- Runtime `33854e97c0b248e731ac86c57bef17c43a42257a` (`0.1.0.dev29`).
- Deployment `1003695db1f2aad97c8c098a6f53b732f18c43ab` (`0.1.0.dev7`).

The SDK builder keeps upstream's `DEPTHAI_BUILD_BETA=ON`: 3.12.1's stable
`Pipeline.cpp` references a calibration helper compiled only with that option.
The first OFF build linked the SDK itself but failed when linking the camera;
the corrected private SDK and camera build passed without an upstream source
patch. The camera creates no beta nodes. Frontend embedding is disabled.
Private test-command layout/library-path errors and corrected results are retained.

Passed: five existing camera tests and binary-trace layout checks; 25 focused
runtime tests; wheel/source-distribution builds; all 105 runtime package files and
four CLI help checks; three synthetic ROS images through the real capture child
with graceful exit; a clean installer bootstrap with dependency consistency;
57 deployment tests; all 48 mode/backend launch-description cases; and 24
deployment package files plus installed definitions matching the selected source.
The runtime's shared child transport was preserved under a neutral name, and
retired `kind: "oak"` profiles give an explicit ROS migration error.

This is not a fresh-host reinstall, a full browser/performance campaign with
these new pins, or moving-vehicle/clock-accuracy acceptance. Package metadata
and implementation source pins identify tested production code; later
documentation and offline-prototype commits do not change that code.

## Preservation

The [final audit](preservation.json) confirms empty owned cgroups, no blocked
runs, stopped fixture/resource helpers, and unchanged host packages, power mode,
Docker inventory and selected everyday release. Jah was
[released](release.json) at 01:49:55 AEDT on 14 November 2026.

The private numeric/source archive contains 121 files, 7,272,642 bytes, with
SHA-256 `d91419e2c2f5f68edac54e930aa3d2fc5050de697171148a662433b119717d3b`.
Its downloaded local copy was hash-verified. It contains traces, logs, source
snapshots, package identities and reproduction helpers; no camera images or
credentials were collected into it. The earlier raw fault archives remain
unchanged. The release receipt is retained separately because it follows archival.
