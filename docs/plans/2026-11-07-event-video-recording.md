# Event video recording implementation plan

Implements the [agreed design](../design/2026-11-07-event-video-recording.md).
Implementation is authorized. Use the user's Solo workflow, proportionate focused
checks and intermediate commits. All execution runs on reserved Jah. Do not promote
integration branches or select a permanent release as part of development.

## Work packages

1. Extend rgbd_camera startup profiles and calibrated geometry for 1280x720 at
   30 Hz on OAK-D and D455. Preserve legacy defaults, timing and pairing contracts.
   Parameterize OAK output/copy/intrinsics validation and D455 profile selection,
   rectification maps and depth-to-colour projection. Extend existing geometry and
   adapter checks; verify actual camera profiles in an isolated build.
2. Add the optional native runtime recorder package. Consume atomic camera/overlay
   messages, render depth and encode independent bounded H.264/MP4 branches. Reuse
   the existing interfaces and optimize atomic-only detector overlay publication.
   Verify colourization, frame admission and independently playable segments.
3. Implement session manifests, optional frame indices, acquisition-based timelines,
   gaps/generations, waiting/resume, graceful finalization and interrupted-session
   reporting. Exercise missing overlays, restarts, stale/out-of-order input, clock
   mismatches, encoder failure and writer interruption with controlled inputs.
4. Integrate recording with the existing runtime operation/lifecycle policy, CLI and
   authenticated browser controls. Freeze bounded validated startup options, expose
   current and terminal state, and preserve worker independence from management,
   browser leases and live video settings. Verify authorization, request identity,
   source admission, duplicate operations and disconnect behavior.
5. Extend deployment profiles, camera-only topology, unannotated viewing, native
   builds/factory checks, storage configuration and component pins. Implement the
   10 GB managed-history policy and filesystem reserve with bounded, safe ownership
   checks. Verify invalid paths, active/unrelated protection, whole-session eviction,
   quota exhaustion and staged-install behavior.
6. Run integrated acceptance on both cameras and an isolated installed candidate:
   RGB only, depth only, annotated only, combined outputs and each annotation choice;
   live viewing during recording; viewer disconnect/change; source recovery; file
   decode and capture association; resource/drops measurements; ten-minute run and
   interrupted finalization. Preserve exact identities and evidence limits, inspect
   final diffs and report remaining hardware/display limitations.

## Engineering decisions

- Native recording runs outside perception initially. Measure full RGB-D transport
  and image-copy costs before introducing shared-memory transport or co-location.
- Generic lifecycle operations remain authoritative; no browser-owned recorder lease
  or second command-policy implementation. Keep heavy file reads/media work outside
  the serialized manager loop.
- Source dimensions/profile changes are explicit startup choices. A waiting recorder
  resumes only a compatible configured source; it does not reconfigure the camera.
- Keep camera-independent visualization and recording separate from sensor SDK code.
- Prove exact renamed interface compatibility in the candidate; the old permanent
  installation retains its Batch bindings and recorded provenance.

## Starting identities

| Repository | dev baseline |
| --- | --- |
| rgbd_camera | e225ea79c885b29d54f1fee2861c9d3a25e60cb0 |
| rgbd_object_detector | 68215056f36a423458c7968111ccfb6ff247e834 |
| robot_runtime | 3f50ffb006df7df4401370c31b5f2e0e625be96f |
| robot_deployment | 4c57a5484dc2bf8df843b5e3da08f9a58796e043 |

Work is isolated on feature/video-recording in four sibling worktrees. Existing
RC-calibration work and the original checkouts are preserved. No new pre-squash
archive branches, tags or bundles are required.
