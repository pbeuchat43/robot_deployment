# VO/VIO development consolidation — 15 November 2026

The five repositories were squash-integrated into `dev`, including the local
documentation fixes and consolidated deployment pins. Fresh bootstrap, installed
package, ROS build and configuration checks passed. Hardware results were mixed:
D455 passed its smoke gates, while OAK had a failing trial and a passing repeat.
The previously qualified release also failed the same OAK gates in the comparison.
This record does not claim uniformly passing hardware performance.

The [numeric summary](summary.json) retains all four runs and separates source
verification from hardware performance. Jah's live deployment was not activated,
and `main` was not promoted.

## Source identities

| Repository | Consolidated source checked |
| --- | --- |
| `rgbd_camera` | `d56b6aa21d15e1862902e9992f8f298dcf84b982` |
| `rgbd_object_detector` | `1a8583e0192263b278b645add57cb0dfed53025b` |
| `robot_runtime` | `aee4e9c0624d395de6bc02d27819d79c935024b8` |
| `visual_odometry` | `19aefec49e7e848ff4162ec0b73c2da6d73e5677` |
| `robot_deployment` | `2f0fb6a8398ae09a05f9e74fdba4ff8cefceacd6` |

Deployment selects the four consolidated component commits. Its source-file
`sources.json` SHA-256 is
`cfca7b1822a85e98adecce51ebbed3919e3ae1d6dbb0f776611b045670b37072`.
The [Git comparison](implementation-equivalence.json) maps the earlier qualified
commits to these commits: all executable/configuration entries are unchanged,
apart from deployment's four commit pins and removal of two obsolete archive-ref
metadata fields. Documentation and evidence differ. Each squash initially had
exactly the same tree as its integrated feature branch. This evidence and its
entry-point links are a subsequent documentation-only commit; the tested wheels
retain the `2f0fb6a` identity.

Local evidence-retention and documentation-link fixes were imported before the
squashes. Current cross-repository links target files on `dev`; historical tested
commit IDs retain their original meaning without requiring branch retention.
The RC firmware/interface `dev` commits are unchanged.

## Build and software verification

All execution checks ran on reserved Jah in an isolated directory, ROS domain,
runtime namespace and ports, with stopped private management configuration.

- The official clean bootstrap verified 16 wheel/source artifacts and dependency
  consistency. All 24 deployment and 105 runtime installed source/assets matched
  the selected checkouts; the installed build identity and pins matched.
- The production acquisition helper checked out all four new component pins and
  the unchanged vision-interface/model sources. The production ROS builder built
  eight packages, and fresh release Python packages were installed.
- All 58 deployment and 190 runtime unit tests passed. Launch inspection passed
  all 48 mode/backend combinations without starting those workloads.
- All 24 modes passed preparation against the actual candidate artifacts. The
  old odometry manifest correctly rejected the new source IDs; the new manifest
  accepted them. Fresh ROS interface modules were loaded from the new build.
- CLI help, generated service validation, media-factory inspection and the
  installed mode catalog passed.

The standard odometry Docker builder produced image
`sha256:0e5adb392e57dd3e08d7ea68a9dfe2a63ced87710d145dac1a63882b576b79f1`
with the new source identity manifest. Five Docker build steps used cached layers.
Its filesystem layers and package inventory are identical to the earlier image
`sha256:5f69ad614687502dff1cec6e4b9a7c3fe79ee7665a8dc24bcc0842270f17bbcf`.
The image IDs differ; artifacts were not relabelled manually.

SDKs, model engines and native video were reused read-only from the
[earlier standard-release qualification](../2026-11-15-vio-release-qualification/README.md).
This candidate was assembled with production component builders and explicitly
marked as a verification fixture. It is not a new complete standard-installer or
installer-rerun result. Earlier full-build, full-workload and recovery evidence
keeps its original source and artifact provenance.

The first private harness attempt omitted `parameters(graph)` before copying
definitions, so configuration failed on the absent parameter file. The standard
installer already performs that step. The harness was corrected, its failed
receipt and definition snapshot retained, and checks resumed from configuration;
compiled artifacts and repository implementation were unchanged.

## Stationary smoke measurements and open OAK finding

Each run used 720p30 RGB, the cones detector and Docker VIO, ten seconds of warmup
and 60 measured seconds. Traced runs added numeric status, stereo-sidecar and
upstream-pose observations; they did not change production artifacts or settings.
The fixed gates were at least 29 Hz for cones and poses, and 98% same-epoch pose
bracket coverage. All fixtures completed with empty cleanup errors.

| Selection / run | Cone Hz | Pose Hz | Pose brackets | Performance gates |
| --- | --- | --- | --- | --- |
| Consolidated OAK, original fixture | 30.000 | 27.150 | 71.444% | Failed |
| Consolidated OAK, traced repeat | 30.017 | 29.983 | 99.778% | Passed |
| Previously qualified OAK, traced comparison | 30.000 | 27.733 | 77.333% | Failed |
| Consolidated D455, traced fixture | 29.983 | 29.967 | 99.889% | Passed |

The first OAK run delivered 1,800 cone observations without acquisition gaps but
only 1,629 poses. The adapter ended at association epoch 196 with 199 unmatched
entries. Camera counters reported no rejected stereo or combined-IMU samples.

The old-release comparison recorded `upstream_tracking_failed` in 22 internal
status observations, 136 pose acquisition gaps above 50 ms and no missing
`Estimate.sequence` positions at the probe. The adapter correctly starts a new
association epoch after loss or a gap, so bracket coverage falls further than
pose rate. The passing consolidated repeat had one such gap and no sampled
tracking-failed status. Sparse status observations cannot explain every failure
in the original untraced run.

The same behavior on the old release shows it is not specific to consolidation.
The cause of the intermittent upstream tracking failure remains unresolved.
Scene and lighting conditions were not independently verified in these trials;
neither a source regression nor lighting is established as its cause. A passing
repeat does not erase the failed windows. Retain this finding for a controlled
scene/lighting and upstream-status investigation before relying on consistent
OAK pose availability. No limits, parameters or confidence claims were weakened.

These short runs do not repeat the earlier dual-detector/video/recording campaign,
establish a natural fault rate, or qualify fresh-host installation, physical
calibration, motion accuracy or vehicle control.

## Host preservation, evidence and branch disposition

The final audit found all four runtime managers released, their owned services
inactive, empty cgroups/containers and no loaded camera libraries. Host packages
and power mode were unchanged. Six baseline identity files, including its
odometry manifest, matched the previously archived bytes. The old live services
remained disabled and no live selection was created. Jah retained about 36.95 GB
free space. The [reservation release](release-result.json) verified the lock was
available after evidence retrieval.

The private numeric/log archive contains 121 files and no imagery. Its
[receipt](private-archive-receipt.json) records 918,985 bytes and SHA-256
`80bc3aa296916c936af6483f3e1edfb171ff71689f243f48c865f2b51d1e3d33`;
the downloaded copy was hash-verified. Private raw records are outside Git.

The reviewed cleanup set contains 32 completed local branches, 11 corresponding
remote branches and four temporary feature worktrees. Of these, the
[23 historical branch tips](older-branch-disposition.json) are already represented
in `dev`, either directly or by identical trees. Four maintenance branches contain
the imported documentation fixes; five feature branches contain the squashed work.
No disposition is ambiguous. Removal is gated on checking published `dev` heads
and source pins. `main`, the seven normal checkouts and their existing ignored
build/artifact directories are preserved. No new archive branches or tags are
created; transfer bundles serve verification, not history retention.
