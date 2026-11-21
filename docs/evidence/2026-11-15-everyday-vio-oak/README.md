# Everyday activation and OAK follow-up, 15 November 2026

Jah's everyday release `r20261115-dev` was built through the standard installer
and selected. The earlier qualified reference and consolidated candidate remain
in their separate private roots. This record supplements the
[consolidation finding](../2026-11-15-vio-consolidation/README.md); successful
follow-up trials do not establish that the intermittent OAK failure is fixed.

Across 72 minutes of OAK VO/VIO measurement, all 129,599 observed upstream
statuses reported success. The full thirty-minute workload passed; the baseline's
original fixture failure and separate boundary-freshness reconciliation are
recorded below. The prior intermittent upstream loss was not reproduced, so
its cause remains open. Jah was returned to enabled, active management with all
application workloads stopped.

## Exact selection

| Repository | Published `dev` commit used |
| --- | --- |
| robot_deployment | `19dd8bc79f3e418221f4a521d52ab9c92242d4c4` |
| robot_runtime | `aee4e9c0624d395de6bc02d27819d79c935024b8` |
| rgbd_camera | `d56b6aa21d15e1862902e9992f8f298dcf84b982` |
| rgbd_object_detector | `1a8583e0192263b278b645add57cb0dfed53025b` |
| visual_odometry | `19aefec49e7e848ff4162ec0b73c2da6d73e5677` |

The independently retained RC source heads were firmware
`f25b331810f56f4ca61dfe201e129046b4ed557b` and interface
`1903b9524a82255b2a230cdc26cb5bf255487210`. They were not provisioned into this
release: no Pico was connected and the private site had no RC identity triple.
All seven local `dev` heads matched the fetched published heads at preparation.

The Docker image is
`sha256:d3c942971a8029401b888e83e2e60ea7614d53306835214809d6d975fa7e5dc2`.
Its compared source files and ordered root-filesystem layers exactly match the
prior consolidated image, although image metadata gives it a different ID.
Both camera profiles are 720p30, with the qualified camera-specific estimator
settings unchanged. No source fix or estimator-parameter change was made.
These documentation changes do not alter the installed identity.

## Build and activation

- A clean matching bootstrap and the complete standard build succeeded,
  including DepthAI/RealSense, ROS packages, Python packages, both TensorRT
  engines, native video and the odometry image. This was a fresh application
  build on the existing host, not a fresh-host qualification.
- An identical stage-only installer rerun succeeded and left all 40 completed
  build-log files byte-identical. Selection followed this reuse check.
- Normal `lucid_conduct` installation information, doctor, the 24-mode catalog
  and fresh runtime status passed. Management services were enabled and active
  with application workloads stopped at activation.
- The actual HTTPS page loaded in temporary Chromium with fresh API status,
  two cameras, four model choices, three odometry choices and no JavaScript
  exceptions. The browser profile and process were cleaned up. This establishes
  host-browser readiness, not a remote operator's display experience.
- Existing credentials, network selection and student workspace were retained.
  The original private configuration and prior deployment records were preserved
  before selection. No firmware was flashed and no vehicle was actuated.

The extra global `pip check` **did not pass**: Debian's `pynacl 1.5.0` metadata
declares a missing `cffi` distribution. The identical finding exists in both
retained reference environments. The installed Debian CFFI backend loaded and a
PyNaCl encryption/decryption check passed; the application does not depend on
PyNaCl and its locked dependency versions were verified. Activation proceeded
with this specific inherited metadata finding recorded, without changing host
packages. The stopped first activation attempt is retained.

The first browser helper passed its page checks but failed a cleanup assertion
when systemd had already garbage-collected its transient unit. Process absence
was verified, the owned profile was removed, and the helper was corrected to
accept the observed inactive/absent unit. Its focused rerun passed with empty
cleanup errors. This was a private harness correction, not a product change.

## Diagnostic method and short trials

Trials used the exact selected release through an isolated runtime namespace,
ROS domain and data root. Idle everyday management was stopped during hardware
trials. Each trial started a fresh camera and estimator, used a ten-second
warmup and retained normal fixture coverage/rate gates: at least 29 accepted
poses/s and 98% same-epoch pose-bracket coverage, with brackets no wider than
50 ms. Detector rates were checked against 29 Hz as well.

The added observer captured each published upstream `VisualSlamStatus`, raw
odometry, stereo sidecar, combined IMU and accepted estimate, plus camera/adapter
health and host resource samples. Exact source stamps were joined using the
session's fixed clock mapping. Numeric subscriptions use best-effort QoS;
missing observer rows alone cannot establish an upstream drop. Upstream tracker
execution time excludes queueing before the callback and DDS delivery afterward.

Scene and lighting confirmation was requested but not received. No physical
scene or lighting changes were made by the operator agent. These are bench
workload comparisons under **unconfirmed environmental conditions**, not
controlled lighting experiments or physical motion acceptance.

| Trial | Measured time | Accepted poses/s | Bracket coverage | Observed upstream successes / failures |
| --- | ---: | ---: | ---: | ---: |
| OAK cones + VIO, fresh start 1 | 180 s | 30.0056 | 99.9815% | 5,400 / 0 |
| OAK cones + VIO, fresh start 2 | 180 s | 30.0000 | 99.9815% | 5,400 / 0 |
| OAK cones + VO | 180 s | 30.0056 | 99.9815% | 5,400 / 0 |
| OAK both detectors + VIO + video + recording | 180 s | 30.0000 | 99.9815% | 5,400 / 0 |
| D455 cones + VIO reference | 60 s | 29.9667 | 99.8888% | 1,798 / 0 |

All short trials passed their unchanged gates, with empty cleanup errors and no
missing stereo/status/raw-pose/accepted-estimate matches in the measured windows.
The OAK VIO baseline trials reported no stereo, IMU or clock rejections. Their
95th-percentile tracker execution times were approximately 9.7 and 11.9 ms.

The short full workload delivered both detectors at 30 Hz. Browser decoded-frame
growth was 5,641. RGB/depth/annotated recordings finalized with 5,777/5,777/5,776
indexed frames and seven segments each. Durable state, frame indexes, segment
ledgers, counters and generation separation passed; first and last segments of
each track decoded successfully. Peak reported host RAM was 4,280 MB and maximum
reported sensor temperature was 66.468 degrees C. The short full trial overlapped
a small earlier-trial summary operation; longer measurement windows exclude
that analysis workload.

## Long trials, fixture correction and interpretation

The thirty-minute cones + VIO baseline delivered 30.0000 accepted poses/s and
99.9981% bracket coverage. All 54,000 independently observed upstream results
were successful, with exact stereo/status/raw-pose/estimate matches throughout
the acquisition window. The worst complete minute was 29.9833 poses/s with
100% coverage for its acquisition-window samples. Pose latency was 51.648 ms
at the 95th percentile and 83.456 ms maximum; none exceeded 100 ms. Peak reported
RAM was 3,640 MB and maximum reported sensor temperature was 60.062 degrees C.
There were no measured-window stereo, combined-IMU or clock rejections. Startup
counters included seven RGB pair rejections and two combined-IMU rejections;
those counts did not grow during the measured window.

**The original baseline fixture verdict remains failed.** It checked the age of
its last camera status after computing all per-minute statistics, while no longer
servicing ROS callbacks. This made the freshness result depend on report
generation time. Its retained snapshot matched an independent observer sample
only 155.899 ms old at the scheduled measurement end. The independent observer
received all 9,000 camera and 9,000 health samples in that window; maximum receipt
gaps were 204.551 and 206.495 ms, and maximum receipt ages were 5.971 and 7.936 ms.
Both streams continued normally beyond the measurement boundary. Replaying the
retained statistics alone took about 0.69 seconds on the idle host.

The canonical integration fixture and private diagnostic copy now capture one
monotonic timestamp immediately after the final spin. Both existing freshness
assertions compare the frozen observations against that timestamp. The one-second
upper bound and rejection of future timestamps remain unchanged, and the report
records the boundary timestamp and ages. No extra spin refreshes the snapshot.
The original result and trace remain untouched; a separate reconciliation records
the passing measurement metrics and independently observed boundary freshness.
This change affects verification code, not the selected application or estimator.

The thirty-minute full workload passed the corrected fixture and all rate and
coverage gates. It delivered 29.9994 poses/s, 29.9994 cone results/s, 30.0000 COCO
results/s and 99.9981% bracket coverage. All 53,999 observed upstream results
were successful, with no missing stereo/status/raw-pose/estimate matches in the
acquisition window. The worst complete minute was 29.9667 poses/s with 100%
acquisition-window coverage. Pose latency was 65.798 ms at the 95th percentile
and 105.879 ms maximum; two samples exceeded 100 ms and none exceeded 200 ms.
Boundary camera and odometry status ages were 193.825 and 128.256 ms. This real
long-run result exercises the corrected check; the canonical script also passed
Python compilation on Jah. No application rebuild was needed for this fixture
change.

Two full-run association changes occurred during startup, at 18.442 and 18.609
seconds after observer startup. Video became ready at 16.166 seconds, followed
by the ten-second warmup, so both preceded measurement. No upstream failure
status was observed, and epoch 3 remained stable through the measured window.
Measured camera counters reported no stereo/IMU rejection, sequence gap or clock
discontinuity. Peak reported RAM was 4,324 MB, maximum reported sensor temperature
69.031 degrees C, and GPU utilization median/p95/maximum was 33/65/86%.

The browser recorded 54,219 decoded-frame growth with no JavaScript exceptions
and empty cleanup errors. Recording finalized all three tracks, each with
63 segments and a single camera generation:

| Track | Finalized indexed frames | Bytes | Overload drops | Rate drops |
| --- | ---: | ---: | ---: | ---: |
| RGB | 54,516 | 1,362,845,637 | 5 | 43 |
| Depth | 54,547 | 1,693,200,984 | 9 | 8 |
| Annotated | 54,504 | 1,362,536,340 | 12 | 43 |

The annotated track also reported one rejection. These are bounded recording
results, not lossless capture claims. All durable/index/ledger/frame-count and
generation checks passed, and the first and last segment of each track decoded.
Recording/browser counts include startup and finalization outside the thirty-minute
pose measurement. Full workload ownership was empty and its container was removed.

The old failure trace had 300 stereo sidecars per complete ten-second interval,
but only approximately 273-292 raw poses, with upstream tracking-failure
observations throughout the run. It was not solely a startup transient.
Continued detector output distinguishes that symptom from missing detector
output; it does not exclude shared scheduling or workload as a contributor.
Current successful trials do not identify its trigger or future recurrence rate.

If it recurs, retain exact-stamped numeric rows and estimator warnings around
the first loss before tuning anything. A separately bounded NVIDIA debug dump
can retain tracker inputs if numeric reproduction warrants it; dumping occurs
inline and can perturb timing. Lighting/texture, input timing and initialization
remain hypotheses. No speculative executor or exposure change is justified by
the current successful trials.

## Evidence retention

The [redacted numeric summary](summary.json) retains each trial's original
fixture verdict, performance gates, latency/counter/resource measurements,
recording drops and raw-source hashes. The first two summaries were regenerated
with the later analysis script to add provenance fields. Their original copies
remain retained; all sensor counts and other numeric metrics were unchanged.
Only schema/observer-heartbeat counts were omitted from the later topic-only
count dictionary.

Private activation records, original failed attempts, source inventory, helper
versions, per-frame traces, resource logs and recordings remain on Jah under
`/home/poi/.local/state/robot-experiments/vio-everyday-oak-20261115`.
This directory includes private configuration and imagery and is not suitable
for publication. Public summaries exclude device/session identities, secrets
and image data. Source hashes tie numeric summaries to retained raw records.

## Final everyday state

The normal `lucid_conduct` camera start selected the exact installed Docker image
and produced 819 accepted estimates during a bounded startup/smoke observation.
The owned run stopped with empty membership and its container removed. Both
everyday management services were restarted and verified enabled/active, while
perception, video and recording remained stopped and unblocked. The HTTPS page
and fresh status API passed again using the existing certificate.

The final package list, power-setting output and credential bytes matched the
preserved pre-installation values. Both private reference roots remain present.
No trial/browser processes, camera SDK mappings or containers remained, and the
shared verification reservation was released. Approximately 24 GiB remained free
on the root filesystem. The inherited global Python packaging metadata finding
above remains recorded; it was not repaired or hidden.

The fixture correction was checked by the full thirty-minute hardware run and
Python compilation on reserved Jah. Documentation links and the final diff were
inspected locally. The broader application unit/mode suites were not repeated
for this verification-only correction; the selected application implementation
was unchanged from the previously verified consolidated selection.

Physical mount calibration, moving-camera accuracy, driving, the future browser
interface and RC provisioning are outside this campaign. No reboot or new-host
qualification is claimed. See the [current everyday guide](../../everyday-jah.md).
