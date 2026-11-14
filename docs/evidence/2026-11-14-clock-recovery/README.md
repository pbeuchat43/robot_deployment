# Camera clock recovery and isolated RealSense evaluation

SDK timestamp recovery is implemented and verified in isolated native and Docker
runs. Both RealSense versions crossed an observed raw video clock wrap; the
candidate completed its post-wrap window and cleanup. Original firmware and SDK
operation were restored and the preservation audit passed. The feature branches
remain unmerged and the selected deployment is unchanged.

## Implemented behavior

Camera 0.5.0 / interfaces 0.3.0 add startup-only `timestamp_policy=recover|strict`.
The default recovery policy drops and counts inadmissible mapped timestamps
without advancing accepted timestamp watermarks. It preserves original acquisition
times. A device-to-host mapping-offset change above 5 ms holds all publication,
clears temporal buffers and rotates the camera generation. Capture continues
draining bounded SDK queues. Publication resumes after two seconds of fresh,
stable observations across the enabled streams. Raw device clock/sequence resets,
invalid geometry and device loss remain terminal. Strict policy makes mapped
clock faults terminal as well.

VIO 0.2.0 latches the old adapter unavailable at the boundary. Its supervisor stops
the tracker and adapter together, waits for their process group and publisher to
disappear, then starts a fresh pair for the settled camera generation. It relays
health during this interval; runtime retains ownership of the enclosing process
tree or Docker container. No estimator pose is relabelled across generations.

The camera `Status` fields `clock_state`, `clock_discontinuities`,
`last_clock_step_ns`, `clock_recovery_since_ns`, `imu_clock_rejected` and
`image_clock_rejected` expose recovery. Rebuild all ROS consumers for interfaces
0.3.0; the status wire layout changed. The RealSense production SDK/firmware pins
remain 2.56.5 / 5.17.0.10.

## Software and deterministic hardware checks

The reserved Jetson passed 13 component checks: seven camera, two VIO and four
detector checks. They include rejected-watermark preservation, both mapping-step
directions, raw reset rejection, combined-IMU flushing, one-open synthetic camera
continuation, generation isolation and estimator descendant cleanup. The current
camera was checked again after private instrumentation changes. The isolated
upgrade camera build also passed its seven checks.

A clean deployment bootstrap passed 58 installed tests, all 48 launch combinations
(24 modes × two backends), dependency checks and console help. The installed
24 package source files, 10 definition assets and selected source pins matched
the committed bootstrap source.

For a deterministic integration check, a private overlay shifted every available
OAK mapped timestamp back 182 ms for the first minute, then removed that offset.
Raw device times were unchanged. This creates a forward mapping discontinuity
while keeping the pre-step samples admissible. These trials test recovery, not
timestamp accuracy or ordinary latency.

| Estimator backend | Observed step | Camera publication hold | Pose interruption | Clock-rejected IMU reports / images | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Native | +182 ms | 2.200 s | 3.898 s | 806 / 244 | Fresh camera and estimator generations; one camera process; cleanup passed |
| Docker | +182 ms | 2.200 s | 4.630 s | 806 / 244 | Fresh camera and estimator generations; one camera process; cleanup passed |
| Docker, shutdown correction | +182 ms | 1.999 s | 7.010 s | 802 / 244 | Fresh camera and estimator generations; one camera process; cleanup passed |

Both retained traces and status histories contain output before and after the
boundary. The first injection attempt incorrectly offset an absent depth-exposure
timestamp, suppressing RGB/depth before the step. It was stopped during warmup,
retained as an unsuccessful fixture attempt, and corrected before the table's
three trials. No production recovery fix was needed for that fixture error.

The uninjected OAK follow-up completed fifteen measured minutes with 27,000
matched poses, one camera process, zero clock discontinuities, zero clock
rejections and clean shutdown. It did not encounter a natural clock fault and
therefore adds continuity evidence, not another observed recovery event.

Numeric summaries are retained for the [native step](oak-forward-native-r2-recovery.json),
[first Docker step](oak-forward-docker-r1-recovery.json),
[corrected-shutdown Docker step](oak-forward-docker-r2-recovery.json) and
[uninjected OAK capture](oak-natural-r1-recovery.json).

The first D455 baseline attempt exposed an over-strict startup sequence check:
depth frame number moved from 8 to 0 while raw device time advanced 401.509 ms,
before the existing startup gate became ready. The provider now permits counter
settling only inside that unpublished gate and still requires two seconds of
valid increasing observations. Sequence resets after readiness remain terminal.
Librealsense's [metadata/fallback counter selection](https://github.com/realsenseai/librealsense/blob/v2.56.5/src/ds/ds-timestamp.cpp)
can change independently of its raw UVC timestamp; this trace does not identify
which underlying counter transition occurred. The failed attempt and correction
are retained separately from the subsequent wrap comparison.

## Build identities and limits

- Camera implementation: `bfb8c078368e6eb5b15449e9df6590e406e6d261`;
  coordinated source pin, including interface documentation:
  `bd8515baada78ff8c8d3b5098c910f5ab0fd0261`.
- VIO implementation: `d86e5af7aa11860bee1228bd12bba32d7a9eda48`.
- Deployment bootstrap: `e579ea16f2f8fd2a4471f43e752d06d6278dcc05`.
- DepthAI: 3.12.1, `da14320483864f7cdabada9e70d4d6a2115eff9a`.
- Native estimator manifest SHA-256:
  `4a76dda5b6e744798cccd9afd7eaf6c2bfdcd96d17f8b9ad128cf3349c769629`.
- Private Docker image:
  `sha256:e6d72674869b2853f5aab600b1a89f5b7e53121a938cbe84a4636865989c4574`.

Those identities apply to the deterministic and natural OAK trials. The
subsequent D455 startup correction is camera
`48de2e5dd436524b3a12a56a8e9417181a365a60`, selected by deployment
`56a16b7e7ce99ae04015773eebf6afc9f9cfb1a3`. It changes only pre-readiness
RealSense sequence handling; the OAK implementation and shared recovery code
are unchanged.

The corrected camera passed all seven checks against both SDK variants. A second
clean deployment bootstrap at `56a16b7e7ce99ae04015773eebf6afc9f9cfb1a3` passed
the 58 installed tests and 48 launch combinations; source and asset identities
matched again. The rebuilt native estimator manifest SHA-256 is
`1a84389b8dd4617c8ef11d27ce7aac619da49c55b271e2e82e5aa65b1c90bc43`.
The corresponding private Docker image is
`sha256:8fdf1b8e28b63f336b6941d7209e57f40b5469e2ee4af7773663280892045d03`.
The corrected D455 baseline passed startup and entered streaming/tracking.

The native estimator used the component installer and verified cached dependency
archives. Docker's standard build did not reuse its dependency layer, although
the Dockerfile and dependency lock were unchanged. That attempt was cancelled.
The private test image instead derives from the retained exact image
`sha256:544d56e34b63f4f22898686ede76f9638630a820cc47b73b6a4b3c7815921b84`,
builds the new interfaces/adapter into a fresh overlay and uses only the new
entrypoint. Its complete installed package list equals the parent's. The initial
untagged parent reference failed to resolve; the successful build used a verified
local tag. This is a private dependency-reuse fixture, not a fresh standard
Docker installer qualification. Failed attempts and manifests are retained.

## RealSense candidate rationale

The corrected baseline SDK 2.56.5 / firmware 5.17.0.10 capture crossed a raw
32-bit microsecond wrap on RGB, depth and both infrared streams. It retained
88,883 matched poses and 123.14 seconds of pose output after the boundary.
The pose-arrival gap across that boundary was 34.15 ms; the largest gap anywhere
in the measured run was 60.22 ms. Camera and estimator generations stayed the
same, with zero clock discontinuities, clock rejections or combined-IMU queue
overflows. Streaming callback records showed no SDK timestamp regressions or
video mapping-offset steps above 5 ms. Raw same-sample IMU timing is unavailable
through the public RSUSB API, so video raw-clock evidence does not establish
equivalent IMU raw-clock behavior.

The [baseline wrap summary](d455-baseline-wrap-r2-wrap-analysis.json) identifies
stream slots as RGB 0, depth 1, accelerometer 2, gyroscope 3, left infrared 4 and
right infrared 5. A zero raw-clock anomaly count is meaningful only when
`raw_clock_records` is nonzero. `fixture_passed` records the capture assertions;
cleanup is checked separately, and `wrap_qualification_passed` includes cleanup.

This capture's shutdown failed: a second SIGINT, relayed by ROS launch after
runtime had signalled the cgroup, interrupted the new supervisor's final cleanup
loop. An inner launcher survived and runtime correctly kept the run blocked.
Its exact process group was stopped manually, absence was inspected, and the
isolated runtime's missing-service state was resolved. The original cleanup
failure is retained; the full fixture is not marked as passing.

VIO commit `766ec225e85c306796ecab56623536f6feaab4b3` ignores repeated
SIGINT/SIGTERM during final cleanup while retaining bounded child-group
escalation and reaping. A focused subprocess regression delivers both repeated
signals while cleanup waits on a stubborn child. Deployment
`9ce9be15dfe28c36ac7d541a82e107883bdcde0e` pins that correction. The timing
algorithm and camera code are unchanged; subsequent live shutdown evidence is
recorded separately. Both VIO checks (including the three subprocess lifecycle
cases), all 58 deployment tests and all 48 launch combinations passed after the
correction. A 60-second D455 measurement passed native shutdown. The repeated
Docker forward-step trial passed recovery and shutdown; its longer measured
interruption is included in the table rather than replacing the earlier result.

The corrected native estimator manifest SHA-256 is
`85a05cfaa1d65eeb4622b80d844912589269f48e7c7f541a703689499bd0080e`;
the private Docker image is
`sha256:76c2cfb903ca24e0196cf80b43b8f2de75e2cb712c5ee999110e50c230990ab3`.

The isolated candidate is [2.59.1 beta](https://github.com/realsenseai/librealsense/releases/tag/v2.59.1),
commit `625279aa1fe903528a818f48746ee47c1b5fefd3`, with firmware 5.17.3.10.
It includes the [hardware-wrap timestamp fix](https://github.com/realsenseai/librealsense/pull/15712)
and [RSUSB HID bounds fix](https://github.com/realsenseai/librealsense/pull/15583),
which postdate stable 2.58.1. The SDK is built into a private RSUSB prefix with
CUDA and DDS disabled. Only the private camera overlay permits the candidate
SDK/firmware; production whitelists are unchanged.

Signed candidate and rollback images were staged before any firmware mutation.
Their SHA-256 hashes are respectively
`4c347e3a18eac97b41a97947ef3b225bc1eaf77c68ffd87598736e3cebf3e4d2` and
`a7e10cf7b011929df2bfc6347d87471372621cc937c96cb529c3846f26b60f1c`.
The initial firmware was 5.17.0.10 with downgrade counter zero. Exact device
identity, calibration and a flash backup were retained privately. Update/restore
uses signed images and verifies the sole device independently before invoking
the updater; the updater's serial argument alone does not protect a one-device
selection. Device identity and raw imagery are excluded from this report.

The first candidate updater attempt reached DFU mode but failed to open its USB
interface with `RS2_USB_STATUS_ACCESS`, before transferring the candidate image.
The operator subsequently reset Jah after network loss. Read-back after both
resets confirmed the original firmware, identity and calibration, with downgrade
counter zero. The later connection loss occurred before either queued SSH command
connected; no further firmware update started at that point.

The operator then started a bounded privileged helper granting only the test
account temporary access to the D455 DFU interface on the reserved USB port.
It changes no udev rules or packages and restores surviving device ACLs on exit.
The reservation and updater run as bounded services that survive SSH disconnects.
The second signed update reported firmware 5.17.3.10 successfully installed,
then the SDK 2.59.1 updater exited with SIGSEGV. An independent read-back through
SDK 2.56.5 verified firmware 5.17.3.10, the exact original device identity and
unchanged calibration. This confirms the installed image, not a successful
updater exit. The isolated SDK 2.59.1 camera/VIO capture subsequently completed
more than 73 minutes, including the observed wrap and post-wrap window.

## Observed wrap comparison

| SDK / firmware | Matched poses | Pose-arrival gap across wrap | Output after wrap | Largest pose-arrival gap in run | Cleanup |
| --- | ---: | ---: | ---: | ---: | --- |
| 2.56.5 / 5.17.0.10 | 88,883 | 34.15 ms | 123.14 s | 60.22 ms | Failed; corrected and verified in subsequent captures as described above |
| 2.59.1 / 5.17.3.10 | 131,390 | 34.49 ms | 122.55 s | 89.93 ms | Passed |

The [candidate wrap summary](d455-upgrade-wrap-r1-wrap-analysis.json) records
raw counters crossing from 4,294,961,890 to 27,970 microseconds on depth and both
infrared streams, and from 4,294,961,923 to 28,003 on RGB. All four streams
retained their camera and estimator generations. Streaming records showed zero
SDK timestamp regressions, zero video mapping-offset steps above 5 ms and zero
over-budget future timestamps. The largest observed video mapping-offset step
was 42.752 microseconds. Clock discontinuity, clock rejection and combined-IMU
overflow counts remained zero.

The final candidate status also recorded 50,456 small-future IMU estimates
within the existing 5 ms allowance and one combined-IMU rejection. These are
separate diagnostics from clock-policy rejection. The captured process maps
verified the exact isolated 2.59.1 library; no timestamp injection was enabled.

These stationary runs establish continuity through the observed video wrap for
both tested combinations. Their durations differ; the table is not a controlled
performance comparison. They do not establish raw IMU wrap behavior, timestamp
accuracy, moving-car accuracy or a general advantage for the beta SDK. Keep the
production 2.56.5 / 5.17.0.10 pins: this evaluation did not reproduce a baseline
wrap fault, and the candidate updater's SIGSEGV remains an operational concern.

## Restoration and retained evidence

The signed original firmware was restored using the retained 2.56.5 updater,
which exited successfully. Independent read-back verified firmware 5.17.0.10,
the original device identity and byte-identical calibration. The firmware
downgrade counter changed from zero to one. A subsequent 60-second measurement
with the exact original 2.56.5 shared library passed capture and shutdown.
See the [firmware results](firmware-evaluation.json) and
[restored-baseline summary](d455-restored-baseline-r1-recovery.json).

The [preservation audit](final-preservation.json) passed: packages, power mode,
containers and selected release are unchanged; both retained runtime databases
are unblocked; owned cgroups, fixtures, monitor and viewer processes are stopped.
The privileged temporary USB helper stopped and completed its ACL cleanup.

The resets removed eight historical runtime databases under `/tmp`; their
numeric traces, results, captured journals and cleanup-remediation record
survived. Subsequent capture databases use short persistent state paths. The
final audit distinguishes current database/cgroup inspection from those saved
historical cleanup records; it does not claim the lost databases were retained.

The private archive retains numeric traces, calibration/firmware backups,
signed images, source artifacts, test/build logs, failed attempts and the two
surviving runtime databases. Device identities and those private artifacts are
excluded from source control. Its [receipt](private-archive-receipt.json) records
566 files, 109,535,351 compressed bytes and SHA-256
`96d0039fdc6a4d66f756891dafd66cfae579630820e3a0d553000e8a0551d947`.
The downloaded local copy matched that hash. The reservation was then
[released](release-result.json) at 01:07:20 UTC on 2026-11-14, and its owning
process exited. The release receipt is retained separately because it follows
archive creation. Stationary tests do not qualify physical IMU calibration,
vehicle control or general deployment acceptance.
