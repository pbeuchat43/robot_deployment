# Visual odometry integration evidence

This record covers the initial five-repository implementation, checked on the
reserved Jetson on 12–13 November 2026. It distinguishes installed software
checks from stationary camera observations. It does not establish moving-vehicle
accuracy, mounting calibration, confidence calibration or driving acceptance.

## Software identities

The deployment package is `0.1.0.dev6`; the verified preparation implementation
is `02a41b1`, published with documentation as `4695f2c`. Its source manifest pins:

| Component | Executable source commit | Versions |
| --- | --- | --- |
| rgbd_camera | `f1f64eb4862dab4b96c9b4a6c45edb238747576d` | node 0.4.0; interfaces 0.2.0 |
| rgbd_object_detector | `a617f240af9203fd6b20e4ddd482c2d224aa53c0` | node/interfaces 0.3.0 |
| robot_runtime | `2301180b4c0f86351b750a5201379e28a290edb5` | Python 0.1.0.dev28; recorder 0.2.0 |
| visual_odometry | `b0347ef97f9aaa0aae4e7a6c4175cb0ba16e1737` | node/interfaces 0.1.0 |

Later documentation-only commits do not change these artifact source pins.
The two estimator installations use the same camera types, estimator preset and
adapter source. The dependency recipe pins the NVIDIA base digest and Isaac ROS
Visual SLAM `4.6.0-0noble.20260818193828000`; native archives have individual
SHA256 locks. Docker's resolved package closure is retained with the resulting
immutable image identity. Transitive apt packages are recorded, not completely
locked for a future rebuild.

The final Docker image is
`sha256:544d56e34b63f4f22898686ede76f9638630a820cc47b73b6a4b3c7815921b84`.
Native and Docker source-file inventories match. The installed upstream
`libvisual_slam_node.so` and `libcuvslam.so` hashes match exactly across backends;
the latter is `864513fa79c755e4b5cd5b1fe0ca6e1f0ac248bf14944a971d8104bd197092e4`.

## Installed software checks

- Camera: five CTests passed, including stereo input/output contracts and
  RealSense geometry. Detector: four CTests passed, including both overlay paths.
- Odometry: exact-stamp association/freshness CTest passed. Recorder: both CTests
  passed, including the added 640×360 admission case.
- Runtime: 189 installed-package tests passed. The ten focused Docker policy
  tests also passed after the final GPU argument change. Real systemd, client
  and Chromium integration checks passed. Four real Docker lifecycle scenarios
  passed on the earlier retained benchmark image: ownership, manager recovery,
  launcher loss and bounded graceful-stop timeout. Final-image camera checks
  are recorded separately below.
- Deployment: 57 installed-package tests passed. Actual ROS launch descriptions
  for all 24 modes on each backend passed namespace/remapping inspection;
  this launches no components. Isolated maintenance checks passed with empty
  cleanup errors.
- Bootstrap from clean published commit `4695f2c` passed. The installed candidate
  matched 105 runtime package files, 24 deployment package files and 11 deployment
  data files; `pip check` passed. Canonical and compatibility runtime CLI help
  entry points were checked.
- The recorder recovery fixture used synthetic ROS captures and real native
  hardware encoding, and verified intentional invalid-capture rejection and
  discontinuity segmentation. This is distinct from the live recording below.

Failed attempts were retained. They exposed a recorder height allowlist omission,
contradictory OAK VO/IMU parameters, the D455 360p native depth requirement,
fixture state-path/finalization errors, and insufficient disk space during the
first Docker image export. Corrections were followed by the affected checks.
The private test venv needed its own pinned PyYAML and cffi dependencies; host
packages were not changed to repair the test environment.

The first comparison was interrupted after the operator confirmed that room
lights had been accidentally turned off and restored. OAK visual tracking losses
in that series are not pooled into the restored-lighting comparison. One native
OAK run also reported `IMU acquisition clock regressed` and stopped acquisition;
that separate fault was unexplained at the time. Its log lacks the raw device
timestamp and sensor/sequence delta needed to distinguish report reordering from
clock mapping.
The monotonic guard was retained. Resource readings did not suggest CPU, RAM or
thermal exhaustion. Earlier combiner rejections do not identify the fatal sample.
A [subsequent timestamp/sequence investigation](../2026-11-13-oak-imu-clock/README.md)
captured 27.7 minutes across five camera starts, including controlled CPU load,
without reproducing the regression. The [longer follow-up](../2026-11-14-oak-imu-clock/README.md)
then reproduced a backward mapped timestamp while raw device time and sequence
advanced: a −6.032729 ms device-to-host offset step caused a −0.980243 ms
acquisition interval. The captured failure mechanism is established, while the
reason for that upstream correction and the original uninstrumented sample
remain unresolved. The production guard is unchanged.

Interruption completed workload cleanup, verified by empty containers/services
and unblocked persisted runtime ownership. A fixture double-shutdown exception
prevented that interrupted run's final report; its log and separate cleanup
record were retained. Fixture commit `bdb1eb1` adds guarded shutdown, rejects stale
or erroneous camera health even after earlier valid output, and explicitly bounds
actual pose-bracket width to 50 ms. The fresh fixed sequence uses those checks.

The timed fixture did not persist per-run stereo calibration IDs. A subsequent
reporting-only change retains camera/session/calibration/configuration identity;
two supplementary five-second Docker checks capture those private identities for
the current cameras. They are separate evidence, not reconstructed identities for
the earlier windows. Engine/profile hashes are checked against the retained
installed manifests. This provenance limit accompanies the timing results.

## Native stationary integration

Both cameras produced matched VO and VIO estimates through the installed runtime.
The final adapter's guarded shutdown completed without leaving owned work.
The following full-workload runs used both detectors, VIO, RGB/depth/combined
overlay recording, and a real finite headless Chromium WebRTC viewer:

| Camera/RGB | Window | Cones Hz | Poses Hz | Cone p95 ms | Pose p95 ms | Joint p95 ms | Pose brackets |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OAK 640×360 | 30 s | 30.033 | 30.000 | 70.67 | 38.51 | 70.67 | 99.889% |
| D455 1280×720 | 30 s | 30.000 | 29.967 | 51.72 | 42.71 | 60.23 | 99.778% |

The viewer decoded 933 frames in 34.13 seconds for OAK and 978 in 34.17 seconds
for D455. All encoded recording frames finalized; no recording gaps or rejected
frames occurred. OAK recording rate admission dropped 20–29 frames per output
at its 30 Hz cap; D455 RGB reported one overload drop. These are not zero-loss
recording claims. All runtime and viewer cleanup checks passed.

These runs overlapped Docker dependency download and establish functional
integration, not matched native/Docker performance acceptance.

## Restored-lighting comparison protocol

Each camera/RGB resolution uses Off/native/Docker/Docker/native/Off order, with
15 seconds of warmup after readiness and 60 seconds of measurement. The current
cone detector, capture interfaces and estimate adapter are included. Native and
Docker use identical camera/estimator settings; no build or package download runs
alongside the measurements. Stereo remains 640×400 for OAK and 640×480 for D455.
RGB is 640×360 or 1280×720. Both previous and current RGB captures need same-epoch
pose brackets no wider than 50 ms.

Off uses the installed product's defaults: OAK mono exposure is automatic and
D455 720p keeps its native 720p depth; VIO uses fixed OAK mono exposure and D455
native 640×480 depth aligned to RGB. This differs from the earlier disposable
benchmark's fixed Off depth/exposure settings. The Off comparison therefore
measures the actual mode change, including acquisition policy. Native versus
Docker remains a matched estimator/backend comparison.

The numerical thresholds remain 29 Hz minimum output, at most 10 ms added Docker
p95 relative to native for cones/poses/joint readiness, at most 15 ms added cone
p95 relative to Off, at least 98% brackets in every estimator run, Docker pooled
coverage within one percentage point of native, no additional missing cone
sequences relative to Off, and complete cleanup. Per-run median/p95/p99/maxima,
latency-burst counts and rate/coverage minima accompany pooled values. Resource
samples are 1 Hz and include startup, warmup and cleanup as well as measurement;
their means are whole-fixture figures, not pure steady-state estimator cost.

All 24 restored-lighting windows completed and all four groups passed these
numerical gates. Pooled p95 values in milliseconds are:

| Camera/RGB | Off cones | Native cones / pose / joint | Docker cones / pose / joint |
| --- | --- | --- | --- |
| OAK 640×360 | 66.44 | 65.53 / 43.42 / 65.55 | 64.10 / 43.06 / 64.10 |
| OAK 1280×720 | 77.78 | 86.36 / 52.95 / 86.36 | 85.30 / 52.22 / 85.30 |
| D455 640×360 | 39.43 | 39.18 / 52.37 / 69.80 | 39.14 / 51.87 / 69.30 |
| D455 1280×720 | 59.95 | 46.90 / 50.46 / 67.90 | 46.40 / 48.94 / 66.37 |

The minimum measured cone/pose rate was 29.48 Hz, in the first D455 720p Off/native
windows. Minimum individual VIO pose-bracket coverage was 99.889%. There were no
missing cone sequences in any backend, no latency samples above 100 ms, and no
cleanup failures. The largest measured latency was 94.49 ms (OAK 720p cones/joint);
D455 pose maxima remained below 56 ms. No IMU clock regression recurred in this
restored-lighting series. This does not resolve the earlier isolated fault.

Whole-fixture samples peaked at 3,193 MB reported system RAM, 50% GPU utilization,
443% summed CPU-core utilization, 59.75°C across the sampled CPU/GPU/SoC sensors,
and 10,080 mW VDD_IN. No resource exhaustion or growing latency backlog was
observed in these short windows. They do not establish an endurance bound.
The small native/Docker differences are observations from live scenes, not proof
that one backend is intrinsically faster. Detailed runs, counters, percentiles,
resource summaries and artifact identities are in [summary.json](summary.json).

## Full Docker workload

Both cameras passed 60-second measurements after five seconds of warmup with
both detectors, VIO, RGB/depth/combined-overlay recording and real headless
Chromium WebRTC decoding. These are functional full-workload observations,
separate from the matched cone-only comparison above.

| Camera/RGB | Cones Hz | Poses Hz | Cone p95 ms | Pose p95 ms | Joint p95 ms | Pose brackets |
| --- | --- | --- | --- | --- | --- | --- |
| OAK 640×360 | 30.017 | 30.000 | 70.65 | 38.43 | 70.63 | 99.944% |
| D455 1280×720 | 29.983 | 29.967 | 49.48 | 43.92 | 61.40 | 99.889% |

The viewer decoded 1,862 frames over 64.26 seconds for OAK and 1,880 over 65.30
seconds for D455. Every encoded recording frame finalized and all outputs
completed without gaps. Recording remained bounded and best effort: OAK dropped
7–75 frames per output at rate admission, dropped one queued RGB and one queued
annotated frame, and rejected one annotated sample whose source was unavailable
or incompatible. D455 reported 3–5 overload drops per output, including drops
after admission. These counters are retained in the summary; this is not lossless
recording acceptance. Runtime and viewer cleanup passed for both runs.

## Final preservation

The final audit found all 70 retained runs across 52 runtime states unblocked,
their owned cgroups empty, test viewers stopped, and Docker container inventory
back at its baseline. Host package inventory, power configuration and the selected
everyday release matched the pre-task snapshots exactly. No shared CUDA/OpenCV
package replacement was performed.

The 581-file private numeric/log archive was retrieved and hash-verified
(`5166522b67669e943ddb1290bbd46c5322dec194727dcf5ac1e7b76d89488108`).
Jah's verification reservation was then released at 03:28:11 Sydney time on
13 November; the [release receipt](release.json) confirms the owner exited.

## Scope and retained records

All execution used private candidate prefixes, runtime namespaces and ROS
domains on the reserved host. Existing SDKs, model engines and native AV
artifacts were reused. Both new estimator builders and the changed ROS packages
were exercised; a complete fresh-host installation and full release installer
rerun were not observed in this task. The selected deployment was not replaced.

Raw logs, failed attempts, exact prepared inputs, source hashes, dependency
manifests, samples and private recordings remain in the experiment archive.
Public summaries omit device identifiers, private images and credentials.
The earlier fixed-camera investigations and one-hour memory run remain separate
evidence; they do not establish final-package endurance or moving-scene behavior.
