# Visual odometry implementation plan

Status: initial software implementation and stationary integration checks are
complete; the implementation is consolidated on `dev`. See the [integration evidence](../evidence/2026-11-13-visual-odometry/README.md)
for tested revisions, the retained OAK clock fault, recording losses and unobserved
fresh-host/moving-vehicle work. This plan remains the implementation history.
Scope is production integration of the proposed design, excluding implementation
of cone association or vehicle control. Execute
on feature branches from each repository's `dev`, preserving existing work. Use
intermediate commits for coherent changes. Do not replace the selected Jah release
or merge/promote branches merely because checks pass.

## Benchmark disposition and immediate follow-up

Use [the retained findings](../visual-odometry-troubleshooting.md) and
[the design](../design/2026-11-12-visual-odometry.md). Begin integration with OAK 360p and
D455 720p as performance references, with D455 native depth/IR fixed at 640×480.
Do not advertise OAK 720p or D455 360p as qualified VIO presets yet.

Bound the remaining investigations rather than retuning the whole system:

- OAK 720p: the 12 November disposable fixture recovered 30 Hz and 85–86 ms Docker
  cone p95 with `pipeline_->setXLinkChunkSize(0)`. Port that transport setting into
  the camera integration, preserving capture and IMU rates, and verify current
  components plus full load. The resumed RGB recording check sustained 30 Hz and
  passed decode/index checks, with about 1 ms added cone p95. Targeted IMU traces
  subsequently proved eviction from the four-message host queue during bursty
  delivery. The fixture's 16-message queue plus one atomic bounded drain per poll
  eliminated loss in two recording runs totaling five minutes; a reversal lost
  22 native sequence positions. Port this correction with explicit coherent
  provider/worker bounds (16 messages × 10 paired entries × 2 sensors = 320
  reports per poll), preserving timestamp, freshness and interpolation guards.
  Do not retain the fixture's environment switch as a production interface.
  A failed original-configuration startup also recorded a 332 ms worker pause;
  qualify startup/stall behavior separately rather than claiming this buffer
  covers every pause. Current-component and full-workload acceptance still apply.
- D455 360p: the targeted follow-up reproduced the tail before odometry DDS
  publication, with timely stereo/IMU publication. Port the verified rectified
  stereo convention (`rectified_images=true`) and explicit single-threaded
  `component_container` recipe. The multithreaded reversal retained tails even
  with rectification corrected; two single-threaded runs totaling eight minutes
  had about 51 ms VIO p95 and 60–61 ms maxima. Keep original and follow-up results,
  including individual-minute maxima; a pooled p95 cannot erase a failed repeat. Qualify
  the final components/full workload before advertising this candidate profile.
- VIO memory: the original stationary investigation is complete. The 30-minute
  run reached a 398.13 MiB page-map RSS plateau; the completed one-hour diagnostic
  ended at 399.48 MiB with only 84 KiB growth in minutes 45–60. Allocator in-use
  estimates stayed near 89 MiB from about minute 20 onward without an upward
  trend, while the allocator retained free space. Raw evidence was retrieved and hash-verified;
  cleanup, preservation and reservation-release checks passed. Finite IMU/local-map
  histories offer a plausible warmup mechanism, but no live-object attribution
  or upstream memory defect has been established. No upstream patch is indicated.
  Retain moving-scene and prolonged inertial-recovery memory checks in final
  qualification; this bench result is not a lifetime bound.

No benchmark settings were silently changed to turn these findings into a pass.
The remaining implementation slices may proceed as proposed work; final acceptance
depends on the relevant performance, lifecycle and hardware gates below.

## 1. Fix the input and output contracts

Record the benchmark's candidate camera/resolution matrix and unresolved failures
in the design. Define camera stereo topics, image/calibration convention, timing,
IMU interpolation, native versus published resolutions and internal TF ownership.
Define `Estimate` and `Status` fields, epoch transitions, freshness and the limited
meaning of NVIDIA's `vo_state`. Specify the binding between camera monotonic capture
time and ROS pose stamps. Keep bounds explicit and reject unsupported combinations.

Include explicit exposure-midpoint/duration fields in the versioned capture
reference and propagate them atomically through current detections/overlays.
Preserve the documented legacy acquisition-event meaning and independent depth
pairing times; do not silently reinterpret an existing timestamp field. Add focused
cross-package checks that the detector retains the exact new timing and identity.

Update `rgbd_camera/docs/interface-v1.md` and add the new repository's interface
document. Identify affected package versions and all consumers requiring a rebuild.
This slice ends when the contracts and concrete message/config changes agree;
it does not need a new general interface framework.

## 2. Add production stereo export and explicit camera profiles

Work in `rgbd_camera` provider types, OAK/D455 providers and the thin ROS adapter.
Port only the useful benchmark behavior, removing temporary filesystem tracing and
hardcoded benchmark topics. Keep sole device ownership and bounded latest-frame
processing. Publish the delivered stereo images/CameraInfo and actual internal
calibration, explicitly distinguishing raw from rectified geometry per profile.
For the tested D455 stream, validate matching intrinsics, zero distortion,
identity relative rotation and the horizontal baseline before selecting the
rectified estimator preset. Preserve the OAK raw-stream convention unless separately
validated; a successful launch is not calibration evidence.

Add the qualified 360p profile and, if qualified, the D455 independent RGB/depth
profile. Preserve existing profile behavior. Expose actual native/published dimensions
and source/calibration identity. Do not silently substitute a different native depth
profile when an unsupported combination is requested. Unsupported combinations
must fail during preparation or startup with a useful reason.

Use focused geometry/storage tests for transformed intrinsics, unequal native depth
and RGB sizes, stride handling and malformed calibration. On reserved Jah, verify
actual simultaneous profiles and image stamps for each newly supported profile,
including VIO-disabled operation. Existing required camera checks still apply.
Keep this as a separate commit from estimator or lifecycle changes.

## 3. Add bounded VIO-ready IMU delivery

Implement the camera-owned gyro-time interpolation of bracketing accelerometer
samples. Preserve raw independent streams where they are part of the existing
contract. Declare IMU rate selection, timestamp convention, axes/origin, interpolation
gap bound, queue bound, startup behavior and missing/stale-sample counters.

Test nonuniform sample intervals, missing brackets, excessive gaps, out-of-order
timestamps, queue exhaustion and generation changes. Do not extrapolate or rewrite
timestamps to hide invalid data. Use targeted device observations to verify rates
and static gravity/axis conventions. Physical positive-rotation and mounting checks
are explicit hardware acceptance, not synthetic-test claims.

## 4. Create `visual_odometry` bringup and the small output adapter

Create the reusable repository and independent interface package with MIT notices
for project-owned code and preserved upstream attribution. Add VO/VIO YAML presets,
a launch file, topic/frame mappings and package build/install metadata. Keep
mapping/localization/loop closure and competing TF publishers disabled.
Pin the image convention per camera profile and the executor explicitly. Begin
the D455 candidate with the validated rectified-input setting and single-threaded
`component_container`; do not inherit the original benchmark's unrectified/multi
defaults. Include both choices in effective configuration identity and verify
the adapter's placement does not introduce callback starvation.

The adapter publishes atomic estimate identity and bounded health observations;
standard Odometry is a convenience output. Reset retained work on session changes
or tracking discontinuities. Use upstream status messages and timestamps instead
of parsing log text. Document covariance and the absence of calibrated confidence.
Provide a plain standalone launch path usable within a prepared development environment.

Use the measured Isaac ROS 4.6 dependency combination as the reference. Supply the
package-owned Docker build interface and a manifest recording the base, package
closure and final image digest. Build outside measurement windows. Check message
compatibility between the host interface install and image, component loading, GPU
execution with real stereo/IMU input, readiness and normal shutdown.

## 5. Make Docker ownership part of runtime supervision

Extend `robot_runtime` with a narrowly scoped owned-Docker-resource contract.
Keep trusted configuration validation, command policy and observation separate.
Persist intended run identity before create; verify exact container ID/name/labels;
retain ownership through launcher/client death and manager recovery. Container
inspection or daemon failure must distinguish empty, retained work and unknown.

Keep bounded Docker operations outside the serialized manager loop. Stop targets
the actual owned container as well as native processes. Confirm both are empty
before permitting replacement. Preserve existing explicit escalation and no-automatic-
restart policies. Do not solve this only with a launcher `finally` block or shell trap.

Add focused lifecycle tests for normal start/stop, partial create/cancel races,
client/launcher death, mismatched ownership, manager recovery, daemon unavailability
and a container that refuses graceful stop. Exercise the essential failure paths
with a disposable real container on reserved Jah; use a small deterministic test
workload for lifecycle behavior rather than repeatedly opening cameras.

Extend the launch-mode bound to 32 consistently in profile, ROS capability and AV
validation, with boundary tests. Keep three independent selectors and finite trusted
combinations. Verify existing eight-mode profiles retain their behavior. Run runtime
checks required for the changed policy and supervision boundaries, then stop testing
unless a failure or new change justifies more.

## 6. Integrate installation, preparation and operator selection

In `robot_deployment`, extend source/image locks, dependency preflight, configuration
definitions, preparation, profile generation and `launch.py`. Pin the matching camera,
odometry-interface/implementation, detector and runtime revisions. Install the image
and host interface package during maintenance. Validate image availability and the
tested JetPack/ROS compatibility before a workload start; no launch-time download.

Add an install-time `docker` / `native` backend choice, defaulting to Docker, and
persist it in the release manifest. Resolve that choice to two explicit launch
recipes sharing the same component/ROS contract. A native recipe uses a verified
installed prefix and ordinary process supervision; a Docker recipe additionally
declares owned-container resources. Do not add another UI selector, a sensor relay,
implicit backend detection or fallback. Install and qualify only the chosen backend.
The native route must have a reproducible, compatible dependency installation before
being marked supported; temporary extracted benchmark packages are not that installer.

Add the third selector Off/VO/VIO and generate only supported combinations of the
selected camera profile and eight existing camera/model choices. Freeze backend,
image or native-prefix identity, parameters, calibration, transforms and mode into
the accepted preparation snapshot.
Invalid preparation must leave the old run intact. Group native perception and
container odometry under one run with runtime-visible external ownership.

Expose mode, tracking/freshness, session identity and failure reason through declared
observations. Do not imply that a live container is ready VIO. Update CLI/UI help and
installation/rollback documentation. Defaults must not silently enable VIO in an
existing installation. Validate configuration and packaging with the repositories'
required checks, without selecting the candidate release as the live deployment.

## 7. Qualify the integrated candidate on Jah

Reserve the shared verification lock and inspect workloads. Use a private release,
runtime state, namespace/domain and containers. Rebuild the current camera,
`CaptureDetections` detector, interfaces, probes and new adapter together. Record
source, image, model, engine, calibration, host and power identities, including
the effective `rectified_images` value and executor choice.

Repeat the fixed off/native-reference/Docker comparison for the candidate profiles,
measuring exposure-to-cone latency, stereo-to-pose latency, availability of poses at
previous/current RGB capture times, output rates, drops, CPU/GPU/memory, temperature
and cleanup. The new adapter and final lifecycle implementation must be included.
Do not reuse temporary legacy-`Batch` numbers as acceptance of the final code.
Retain individual-run and per-minute p95/maxima and latency-burst counts so pooled
statistics do not conceal intermittent estimator backlog.

Then test the intended full workload: the selected model combination, live video and
recording where simultaneous operation is required. Exercise mode changes, invalid
preparation, camera/estimator loss, restart, manager recovery and uncertain container
stop. Confirm stale/lost observations reach consumers and replacements remain blocked
when ownership is uncertain. Preserve numerical gates; explain a breach and bound
any investigation instead of continuing optimization indefinitely.

Record host/release preservation and complete cleanup of candidate processes and
containers, then release the verification lock. Report actual evidence and limits.

## 8. Separate moving-car acceptance from software integration

Before using poses for driving or calibrated cone motion compensation, verify the
physical mount, IMU axes/noise and timing; known translations/rotations; drift;
tracking loss/recovery; vibration/exposure behavior; and cone quality at the chosen
resolution. Define accuracy and maximum acceptable wait with the consuming task.
Implement cone association only against the accepted estimate/epoch contract.

These hardware checks can require a supervised physical session. They are not
replaced by unit tests or the stationary benchmark. After the user approves the
completed integration/merge, follow the existing squash-and-cleanup preferences;
promotion of a selected deployment or verified baseline remains a separate action.

## Verification sources

Use each checkout's current `AGENTS.md` and verification guidance for exact commands:
`rgbd_camera/docs/verification.md`, `rgbd_object_detector/docs/verification.md`,
`robot_runtime/tests/README.md`, and `robot_deployment/tests/README.md`.
Checks execute on reserved Jah; local editing, Git operations and static inspection
remain local. Do not import mandatory workflow boilerplate from historical plans.
