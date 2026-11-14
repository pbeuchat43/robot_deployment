# VO/VIO release qualification — 15 November 2026

The standard Docker build, complete installer/rerun and bounded full workloads
passed on the existing Jah Orin NX host at the final implementation pins.
Both cameras ran both detectors, Docker VIO, a decoding WebRTC viewer and all
three recording tracks for 900 measured seconds each. A separate instrumented
OAK trial recovered from a controlled clock step under the same full workload.
The [numeric summary](summary.json) and [acceptance receipt](acceptance-result.json)
retain the results and the corrected private-fixture failure described below.

This closes the standard installer and full-workload qualification gap identified
after the [14 November clock evaluation](../2026-11-14-clock-recovery/README.md).
It is stationary application-release evidence on an existing host. Fresh-OS
installation, physical display performance, calibration and moving-car accuracy
remain separate. At qualification time the branches were unmerged; the qualified release was
selected only inside the private test installation and is not the live deployment.

## Exact selection and fresh-build scope

| Component | Tested source |
| --- | --- |
| `robot_deployment` | `f7cc08868e5e78105de9a76b0745104e2c30b96e` |
| `rgbd_camera` | `48de2e5dd436524b3a12a56a8e9417181a365a60` |
| `rgbd_object_detector` | `a617f240af9203fd6b20e4ddd482c2d224aa53c0` |
| `robot_runtime` | `33854e97c0b248e731ac86c57bef17c43a42257a` |
| `visual_odometry` | `766ec225e85c306796ecab56623536f6feaab4b3` |
| DepthAI | 3.12.1, `da14320483864f7cdabada9e70d4d6a2115eff9a` |
| librealsense | 2.56.5 RSUSB, `38a41441971387197193ad3aeae3cefe6a11f2cb` |

The selected `sources.json` SHA-256 is
`a4ddad82bc75deabe49e3fae296316c1342513e3aeed590fe88aeeb37a5a91f8`.
It also pins the model inputs, vision interfaces and build dependencies.
The standard Isaac ROS 4.6 Docker build produced image
`sha256:5f69ad614687502dff1cec6e4b9a7c3fe79ee7665a8dc24bcc0842270f17bbcf`
from NVIDIA base digest
`sha256:c14ba7a86400f968069eab807595b3d01518abbe287d8cb85092101fe18e98af`.
Resolved transitive apt packages are recorded privately; they are not all locked
by the recipe. Later documentation commits do not change these build identities.

With explicit operator authorization, the old Lucid application, completed
experiments, Docker images and build cache were removed to create headroom.
Its management services were stopped and disabled first. Exact private cone
source was retained and hash-verified before deletion. Host OS, ROS/CUDA packages,
power mode and unrelated projects were preserved. This was application cleanup,
not an OS reflash.

Bootstrap verified 16 artifacts. The standard installer rebuilt SDK cores,
eight ROS packages, release Python packages, the COCO export, both TensorRT
engines, native video and the Docker image, completing in 6,445 seconds
(about 107 minutes). No previously compiled application, SDK core, engine or
Docker image was reused. DepthAI did restore 19 third-party vcpkg dependencies
from cache; this is not a claim that every dependency was rebuilt without caches.
D455 firmware remained on the restored production 5.17.0.10; no firmware update
was part of this qualification.

## Installer and software checks

- The real installed-release fixture passed repeated installer reuse without
  changing completed command logs or the private selection, CLI context,
  24-mode catalog, doctor and call explanation checks.
- Separate system ROS builds and both normal and clean student builds passed,
  preserving student sources and using the selected underlay.
- All 58 deployment unit tests passed against the installed package.
- The launch integration check passed all 48 mode/backend combinations. It
  inspects launch descriptions without starting 48 hardware workloads.
- Seven camera CTests passed in the separate instrumented camera build.
  The standard release was built with tests disabled; these are not CTest
  results from that standard build.
- OAK and D455 each passed a 45-second VO smoke measurement using the standard
  Docker release, with matching poses and clean shutdown.

The only repository code change for this qualification was the installed-test
catalog assertion: it now derives the expected Off/VO/VIO combinations from the
selected site's enabled features and admitted camera profiles, while checking
for duplicates. The previous assertion assumed only eight Off combinations.
The real installed check observed all 24 expected modes.

## Full workload on the standard release

Both trials used 1280×720 RGB at 30 Hz, cones and COCO detectors, Docker VIO,
RGB/depth/combined-overlay recording and an actual headless Chromium WebRTC
viewer. Each measurement followed a ten-second warmup. Viewer output was
640×480; the capture profile does not imply a 720p viewer.

| Camera | Cone / COCO / pose counts | Cone / COCO / pose Hz | Cone / COCO / pose p95 ms | Joint p95 ms | Cone pose-bracket coverage |
| --- | --- | --- | --- | --- | --- |
| OAK | 27,001 / 27,001 / 27,002 | 30.001 / 30.001 / 30.002 | 101.52 / 103.82 / 65.37 | 101.51 | 99.996% |
| D455 | 26,968 / 26,968 / 26,967 | 29.964 / 29.964 / 29.963 | 49.83 / 51.67 / 43.76 | 61.41 | 99.993% |

Latency is acquisition-to-observer age; joint readiness waits for the matching
same-epoch pose bracket, with width at most 50 ms. These are observed values,
not hard latency bounds. OAK cone/COCO samples exceeded 100 ms 2,334/3,719 times;
D455 had one COCO and one joint-readiness sample above 100 ms. No baseline
latency sample exceeded 200 ms. Maximum pose-arrival gaps were 72.19 ms on OAK
and 93.68 ms on D455. Rates and bracket coverage exceed the earlier 29 Hz and
98% reference gates. The matched Off/native/Docker overhead and missing-sequence
comparison was not repeated, so this report makes no renewed claim for those
comparative gates.

Both baseline runs ended with stable clocks, zero clock discontinuities, zero
image/IMU clock rejections and zero combined-IMU overflows. OAK separately
recorded two combined-IMU rejections and eight rejected RGB/depth pairs; D455
recorded neither. These diagnostics are retained rather than called lossless.

| Camera | Finalized RGB / depth / annotated frames | Segments per track | Viewer decoded-frame growth | Peak host RAM / maximum reported temperature |
| --- | --- | --- | --- | --- |
| OAK | 27,432 / 27,441 / 27,434 | 32 | 27,214 | 4,004 MB / 68.94 °C |
| D455 | 27,348 / 27,348 / 27,349 | 32 | 27,217 | 3,948 MB / 70.28 °C |

Recording/viewer counters include warmup and differ from the 900-second sample
counts. Resource sampling includes startup and shutdown, excluding later decode
checks. Every encoded frame was finalized; admission, rate, overload and rejection
counters remain separate in the summary. Finalization does not establish that
every received or admitted frame was encoded.

The verifier checked completed manifests/state, session identity, frame indexes,
segment ledgers, file sizes, strict per-track acquisition ordering and a single
camera generation per file. It then decoded the first and last segment of each
track through the native NVIDIA decoder: six representative files per baseline
run. This samples decoding rather than claiming every file was decoded.

## Clock recovery with the full workload

A private camera overlay built from the exact selected camera source added
numeric tracing and a controlled SDK/acquisition/midpoint offset. It held the
mapped timestamps 182 ms behind until 60 measured seconds, then removed that
offset to create a +182 ms step while keeping raw device clocks untouched.
The standard installed camera binaries were not modified. Estimator Docker
image, detectors, video and recorder remained the standard release artifacts.

The 300-second trial recorded one clock discontinuity, dropped and counted 244
image and 808 IMU clock estimates, returned to stable publication, and changed
both camera and estimator generations. Pose output had a 4.7515-second arrival
gap and resumed 4.7564 seconds after injection. The recording session continued
with disjoint old/new generation files in all three tracks; each track's
acquisition gap was about 2.2486 seconds. The viewer recorded decoded frames
before and after recovery (2,053 and 7,022 in the verifier's respective windows).
This establishes resumed decoding, not an absence of visible interruption.

RGB/depth/annotated tracks finalized 9,273/9,324/9,275 frames across twelve
segments each, spanning two generations. All encoded frames finalized. The
first and last file for every track/generation were decoded, twelve files total.
Publication, tracking and the full workload continued for the remaining trial;
shutdown and ownership checks passed. The intentionally aged pre-step samples
inflate the recovery trial's latency metrics; they are not normal performance
measurements. This controlled step does not establish a natural fault rate or
absolute timestamp accuracy.

The first recovery attempt failed before measurement or injection: the private
camera-only overlay omitted the recorder executable path. Subsequent viewer
failure interrupted fixture cleanup, leaving its owned perception service and
container. A manager reconciled that same retained runtime and stopped the
owned workload; the cleanup receipt passed. The correction linked the unchanged
standard recorder into the private candidate and allowed in-progress cleanup
to finish. Only this trial was retried. The original driver result remains
`passed: false`, with its logs and runtime state retained; the separate
acceptance receipt records the earlier successful stages plus the successful
retry. No production fix or standard release rebuild was needed.

## Final host state and retained evidence

The final audit inspected 14 retained runtime runs and confirmed unblocked
ownership, stopped managers, empty owned cgroups/services and no containers.
Camera SDK libraries were no longer mapped; temporary browser profiles,
injection markers and test management unit files were removed. Host packages
and power mode were unchanged. About 34.8 GiB was free at audit time.

The old everyday deployment remains removed and its management services remain
disabled, as authorized. The qualified release and evidence remain in the
private experiment installation. Activation is a separate later action.

The [private archive receipt](private-archive-receipt.json) records 288 files,
22,379,276 compressed bytes and SHA-256
`730299f7975547d36db1184e03fd7b5bce0af176ef1c3e0241ebaf8e8eea47c6`.
The archive contains source/build identities, logs, numeric traces, runtime
databases and recording metadata, including failed attempts; it excludes video
imagery and generated build trees. Device identities, credentials and private
artifacts are not published here. The local downloaded copy matched the hash.

The [release receipt](release-result.json) confirms reservation exit and a free
lock at 16:36:31 UTC on 14 November (03:36:31 Sydney on 15 November). It follows
archive creation and is retained separately. No current hardware activity is
required for the remaining feature-branch integration decision.
