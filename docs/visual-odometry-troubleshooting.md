# Visual odometry troubleshooting

These notes preserve the reasons for settings measured in disposable Jetson
fixtures on 11–14 November 2026. They guide integration; they are not acceptance
of the final packages, moving scenes, calibration or vehicle operation.

| Symptom | Setting or check | Why / limit |
| --- | --- | --- |
| OAK 720p cone age around 305 ms despite 30 Hz capture | Set DepthAI `pipeline.setXLinkChunkSize(0)` | Repeated Docker VIO fixtures then gave 30 Hz, 85–86 ms cone p95 and complete pose brackets. Preserve capture rates and measure the final workload. |
| OAK IMU sequence gaps while SDK arrivals are complete | Nonblocking host queue of 16 messages; atomically drain one snapshot, at most 16 × 10 paired entries × 2 sensors = 320 reports | Four-message queue eviction was isolated with arrival/dequeue traces. Corrected recording runs lost no reports across 119,042 reports in five minutes; reversal lost 22. This is bounded burst tolerance, not protection against arbitrary stalls. |
| OAK startup reports an invalid acceleration bracket | Inspect native arrival and worker timing; retain the interpolation guard | An original-configuration attempt had a 332 ms worker pause. Its cause was not localized. Never extrapolate or widen timing limits to conceal loss. |
| D455 occasional odometry tails near 120 ms | Validate rectified IR geometry, set `rectified_images=true`, use single-threaded `component_container` for the estimator | Two corrected runs totaling eight minutes gave about 51 ms p95 and 60–61 ms maxima. A multithreaded reversal reproduced the tail. Native camera/detector composition remains independently configured. |
| Unexpected D455 depth detail/resolution | Declare native depth/IR separately from RGB and aligned output | The VIO fixture used native 640×480 depth/IR, aligned to the chosen RGB grid. A 1280×720 aligned image does not create native 720p depth detail. |
| OAK 360p looks stretched | Use aspect-preserving CROP for 640×360; validate transformed intrinsics | The legacy 640×640 profile uses STRETCH. Width alone cannot select the geometry. |
| Initial VIO RSS rises | Allow the measured warmup, track in-use memory and per-window growth | One-hour stationary fixture ended at 399.48 MiB RSS, growing 84 KiB in its last 15 minutes; allocator in-use stayed near 89 MiB after about minute 20. No upstream patch was indicated. Moving scenes and fault recovery remain separate checks. |
| External ROS readers lag/drop large frames | Apply the same tested Fast DDS shared-memory XML to every participant | Fast DDS 2.14.6 uses `FASTRTPS_DEFAULT_PROFILES_FILE`. Applying it to only the producer or using the other spelling leaves readers unconfigured. |
| Process is alive but no valid VIO | Check fresh stereo/IMU, matching upstream status and exact-stamp estimates | Process/container liveness is not tracking. Freshness must expire; `vo_state=1` is a limited upstream success flag, not calibrated accuracy. |
| OAK VO rejects an explicit IMU rate | Leave `imu_rate_hz=0` when IMU is disabled; request 200 Hz only for VIO | The provider rejects contradictory settings before opening the camera. |
| D455 360p fails even with odometry Off | Keep native depth at 640×480 and align it to 640×360 RGB | This acquisition constraint applies independently of enabling stereo or IMU. |
| Docker finishes compilation but cannot write its image ID | Check disk space for the build cache, compressed layers and unpacked image together | The first integrated build exhausted available space while unpacking an approximately 18 GB image. Allow substantial build headroom; remove only identified, approved obsolete images/cache and retain failure logs. |
| Repeated visual tracking loss in an otherwise timely stream | Keep scene and lighting conditions recorded and stable during comparisons | An integrated OAK comparison lost tracking while room lights were accidentally off. Retain those windows separately from the restored-lighting repeat; low output latency alone does not establish tracking. |
| OAK reports a regressed or future SDK timestamp | Keep inadmissible samples out of publication; inspect clock rejection counters and generation changes | A [captured recurrence](evidence/2026-11-14-oak-imu-clock/README.md) has forward device time and sequence but a −6.032729 ms host-mapping offset step, causing a −0.980243 ms acquisition interval. The reversal exists before SDK queue insertion. Its upstream correction trigger remains unknown. `timestamp_policy=recover` drops/counts inadmissible estimates and holds publication at mapping discontinuities; `strict` preserves terminal diagnostic behavior. Neither policy sorts, clamps or corrects timestamps. |

For recurring latency spikes, use the same capture timestamp to trace camera
publication, the estimator's DDS write, and receipt by the observer. Compare
per-minute p95 and maximum latency with the pooled p95 to spot short bursts.

The measured OAK VIO preset requested 200 Hz accel and gyro, used raw 640×400
stereo at 30 Hz, and fixed mono exposure at 20 ms / ISO 800. Those values make the
fixture reproducible; moving-car exposure and vibration performance still need
physical validation. D455 stereo was 640×480 at 30 Hz. Do not silently apply
these settings to the legacy Off profile or claim that raw OAK images are rectified.

DepthAI 3.12.1 is selected in the development pins. Its
[instrumented comparison and mapper replay](evidence/2026-11-14-oak-sdk312/README.md)
still found a future-timestamp fault and large positive SDK steps. Production
handling now defaults to `timestamp_policy=recover`. A mapping-offset change
above 5 ms starts a new camera generation, clears temporal association state
and waits for two seconds of fresh, stable observations while capture continues.
The VIO supervisor restarts both tracker and adapter before accepting that
generation. Rejected samples remain absent; no clock mapping is substituted.
The offline local mapper remains experimental. Neither recovery nor the
prototype's low compute cost establishes absolute clock accuracy.

The [live recovery and RealSense wrap record](evidence/2026-11-14-clock-recovery/README.md)
shows recovery from an injected +182 ms OAK mapping step on native and Docker
backends, with 3.898–7.010 seconds of interrupted pose output. Both RealSense
2.56.5 / firmware 5.17.0.10 and the isolated 2.59.1 / 5.17.3.10 candidate crossed
an observed raw video clock wrap without a clock-policy fault. Keep the production
pins: the baseline wrap fault was not reproduced, and the beta updater crashed
after installing its image. Original firmware and SDK operation were restored.

The [15 November standard-release qualification](evidence/2026-11-15-vio-release-qualification/README.md)
adds 15-minute full-workload Docker VIO runs on both cameras. A separate private
OAK clock-step trial retained both detectors, viewing and all recording tracks:
pose output resumed after a 4.75-second gap, and recording resumed in new
generation-specific files after about 2.25 seconds. The uninstrumented baseline
runs reported no clock discontinuity; this does not establish a natural fault rate.

The later [consolidation checks](evidence/2026-11-15-vio-consolidation/README.md#stationary-smoke-measurements-and-open-oak-finding)
found intermittent OAK tracking failures on both the consolidated and previously
qualified artifacts. Failed 60-second windows delivered 27.15–27.73 Hz poses and
71.44–77.33% bracket coverage; an unchanged consolidated repeat passed. The old
release trace recorded upstream tracking failures with contiguous estimate
sequence numbers at the probe. Scene and lighting were not independently
verified. D455 passed its consolidated smoke check.

A further 72 minutes of OAK trials did not reproduce the loss. Its cause remains
open. Keep the 50 ms association boundary and compare all measurement windows
under controlled conditions. If tracking fails again, retain stereo, status and
pose observations with their exact timestamps, plus estimator warnings around
the first loss. See the [OAK follow-up](evidence/2026-11-15-everyday-vio-oak/README.md).

Keep acquisition-event time distinct from explicit exposure midpoint. Preserve
independent RGB/depth timing and pair admission. Estimator output uses the later
stereo midpoint with the camera's fixed ROS-clock offset; the adapter must match
camera metadata and upstream success at exactly that stamp. Do not attach the
latest metadata to an older pose.

Keep mapping/localization/loop closure and upstream TF publication disabled.
Publish camera-body odometry until the robot mount is measured and approved.
The upstream reset service has no atomic reset marker. Clock recovery uses
supervised estimator/adapter restarts with new association identity; operator
reset uses a whole-run restart.

Docker Stop must inspect and gracefully signal the verified owned container as
well as the native process group. A dead Docker client, missing name after a
timed-out create, or unavailable daemon does not prove cleanup. Retain the blocked
run until ownership is reconciled; do not start a replacement to hide uncertainty.

See the [integration design](design/2026-11-12-visual-odometry.md) and
[implementation plan](plans/2026-11-12-visual-odometry.md). Original raw traces,
failed attempts and private recordings remain outside public source control.
