# CaptureDetections coordinated software verification

Date: 6 November 2026 (Australia/Sydney).

This record describes the tested feature revisions before consolidation. See the
[consolidation record](consolidation.md) for their mapping to the approved `dev`
commits and the subsequent publication and branch-cleanup scope.

The rename passed isolated software verification on reserved Jah. No deployment,
camera, GPU inference or browser session was started. The permanent
`r20261104-everyday` installation still uses its recorded earlier interfaces.
The [machine-readable summary](summary.json) records tested Git identities,
source archives, wheel/library/probe hashes, results and cleanup.

## Baseline and scope

`robot_composition` is now `robot_deployment`, retaining the original Git history.
Its clean `dev` baseline `b8d401990e103d2e911dea9df36ae7bcea160e40` selected
camera `0f4b829`, detector `61219c6` and runtime `3624916`. Work uses
`feature/capture-detections` in the three affected repositories.

| Owner | Changes | Selected/tested revision |
| --- | --- | --- |
| `rgbd_object_detector` | Generated interface, publishers, both overlays, helpers, tests, hardware harness and current docs; detector/interfaces 0.2.0 | `cda6e3efd6aa75b6581a95088c999c0e5df0c21f` |
| `rgbd_camera` | Rate probe, its benchmark CSV/report reader and current examples; no provider/interface change | `b43cb999f57bb834b756a0eb7f7213b02bf249fc` |
| `robot_deployment` | Combined remappings, both integration probes, package 0.1.0.dev2, component pins and launch check | `400e3e5fd5a3f308e243c3da1f14ca08a163707c` |
| `robot_runtime` | Unchanged; standard image/status consumer | `36249160ead1f4f9bf67ad7f6ccf8497f883b651` |

The native build used camera `6fa3100` and deployment `950cdb6`. The final camera
revision changes only the benchmark Python/current docs; the final deployment
revision changes only its camera pin. Byte comparisons confirmed their native
interface/probe inputs are identical to those actually compiled. The benchmark
check and installed deployment tests used the final revisions above. This
evidence/documentation commit changes no tested code or pins.

## Naming and compatibility

| Before | After |
| --- | --- |
| `rgbd_object_detector_interfaces/msg/Batch` | `rgbd_object_detector_interfaces/msg/CaptureDetections` |
| `~/batches` | `~/capture_detections` |
| `first_batches`, `second_batches` | `first_capture_detections`, `second_capture_detections` |
| `OverlayFrame.batch` | `OverlayFrame.capture_detections` |
| `CombinedOverlayFrame.batches` | `CombinedOverlayFrame.capture_detections` (fixed two-element array) |
| `make_batch`, `draw_batch`, `receive_batch` | Corresponding `*_capture_detections` helpers |
| `batches.csv`, observer count `batches` | `capture_detections.csv`, `capture_detections` |
| Report `batch_count`, `empty_batches`, `batch_rate_hz`, `batches` | `capture_detections_count`, `empty_capture_detections`, `capture_detections_rate_hz`, `capture_detections` |

Message-related internal identifiers follow the same naming; the renderer uses
`model_results` for its array of two inputs. The detector repository's
`docs/capture-detections-migration.md` provides the full migration guide.
Payload fields/defaults match the old message exactly, with semantic
`schema_version = 1`. Capture/model/calibration/depth identity, acquisition time,
spatial indices/validity, fresh empty results, bounded work and exact association
are unchanged. Model tensor batch-one settings and camera IMU SDK batching are
unrelated and unchanged.

This is a coordinated generated-binding and ROS wire change. Both atomic overlay
types also change their embedded field/type hashes. Rebuild interfaces, detector,
presentation components, all three probes and external C++/Python clients in a
clean prefix; update subscriptions, fields, launch remaps and CSV/report readers.
Topic remapping alone cannot bridge the old type. External student subscribers,
visualizers, recorders and bag readers are migration consumers, not tested
participants. Old recordings need the original bindings or a separately designed
conversion. Standard image/status topics and model/engine artifacts are unchanged.

## Verification

- Fresh isolated ROS build from the ROS Jazzy base, with pinned `vision_msgs`
  `adbf56a`; rebuilt camera interfaces, detector interfaces and detector. No old
  detector install was used as an underlay. Both integration probes and the
  camera rate probe linked against the new install. The existing TensorRT FP16
  builder-flag deprecation warning remained visible; its source is unchanged.
- All four registered native suites passed: `detector_contract`,
  `detector_adapter`, `detector_overlay`, `combined_overlay` (0 failures/skips).
  They cover publication, identity/timestamps, spatial validity, fresh empty
  results, bounds, expiry, generation invalidation, exact rendering and combined
  association. The combined suite uses actual ROS remappings in a custom namespace.
- Repository bootstrap built source distributions/wheels from the clean final
  deployment commit and pinned runtime, recorded artifact identities, passed
  dependency consistency and CLI help. All **38 deployment unit tests** passed
  from the installed wheel outside the source tree.
- `tests/integration_launch.py` passed for all **six camera/model modes** using
  actual ROS composable descriptions and expanded topics in `capture_rename`.
  The launch service was intercepted before process execution.
- Generated Python bindings round-tripped `CaptureDetections`, `OverlayFrame`
  and `CombinedOverlayFrame`. The old type/embedded fields and generated Batch
  artifacts were absent from the fresh install.
- The benchmark's report functions consumed synthetic `capture_detections.csv`
  with two samples, one valid XYZ and one explicit empty result. This check
  extracted only report functions, without executing its hardware orchestration.
  The benchmark, detector hardware harness and launch files passed syntax checks.
- Git whitespace and new relative documentation links passed. Targeted tracked
  searches found no unintended active message/topic names. Remaining old names
  are migration explanations, historical milestones/evidence/source manifests,
  or unrelated model tensor/IMU SDK batching. Existing historical evidence and
  recorded software identities were not rewritten. Other primary workspace
  repositories had no affected consumers; `ai4r_policy` was excluded entirely.

The private raw logs and scripts were retained in the task's isolated Jah
directory and local task archive; their hashes are in the summary. Native checks
used ROS domain 231, localhost discovery and at most two build jobs.

## Cleanup and limits

The audit found no remaining task processes. Management services remained active,
their manager generation and both workload run IDs were unchanged, and perception
and video remained inactive with no process members. Selected deployment and power
mode were unchanged. The exact reservation was released and the shared lock file
retained. Cleanup reported no errors.

No hardware, deployment, full installer/maintenance, browser or unrelated runtime/
provider regression result is claimed. Historical October/November camera results
remain evidence for their original software only. Existing `main` and `dev` refs
are unchanged; intermediate feature commits are retained. After the user's finish
confirmation, archive those commits, squash components into `dev`, repin deployment
to the resulting commits and retain the mapping back to these tested revisions.
No push or deployment is authorized by this record.
