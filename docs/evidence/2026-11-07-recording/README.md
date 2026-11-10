# Event recording verification — 7 November 2026

This campaign implements the [agreed recording design](../../design/2026-11-07-event-video-recording.md)
and exercises isolated candidates on Jah. The [operator guide](../../recording.md)
describes the resulting behavior. Permanent release `r20261104-everyday` retains
deployment `7a682acafc52fc93d2b8cc02018c35842c4fdc4f` and runtime
`753ba241034371bcc93b7157ad7e63d03753aaf4`; it is not this candidate.

## Identity and boundaries

Camera `564fa6a021783beb87f5518a4b98c13c28293d22` and detector
`32781ed100b8891e02f0d9a853196f363517b9b4` supply atomic CaptureDetections-era
interfaces. Runtime `d0275bf9f88727aac8a33bd145a36df169e4c62f` includes the final
generation-calibration and directory-durability changes. Earlier passing cases
used earlier recording commits; the final source-recovery/sustained case and
native regression checks cover these corrections. The sustained-load candidate
used deployment wheel `fd77bedf9b75e848b86d4d4bec44256da8967c7b` and runtime wheel
`14034449c5e34e64d90839cfba984bb5a63518ce`, plus the rebuilt native package from
`d0275bf`. The Python implementation is unchanged between those runtime commits;
the wheel provenance remains `1403444`.

The earlier behavior candidates use fresh interface/native builds, installed Python
wheels, a private profile/state, ROS domain 231, localhost HTTPS and a temporary
Chromium profile. They reuse the permanent installation's SDK/native-video
prefixes read-only and copy hash-verified model/engine artifacts. This reuse
is distinct from the separate full installer build. All cameras remained
stationary; no driving command or autonomous controller was run.

The full installer was started earlier from deployment
`b0e22a9b5a26ad3aea4234bfdc610707311498a9` and runtime
`0ac996646a708cef17d299b2277d2880c307818e`, using the same camera/detector pins.
Its private release is `r20261107-recording`; later UI, observation and native
recovery fixes do not rewrite that build identity.

Private raw evidence is retained under Jah's
`/tmp/video-recording-20261107-01a1abe4`. Reports include configuration hashes,
run identities, file indices and model provenance. Imagery, credentials and
device serials are excluded from this repository.

## Camera and recording checks

Both providers delivered 600 accepted 1280x720 paired captures in direct-provider
checks: OAK-D measured 29.95 Hz and D455 29.92 Hz. Native geometry tests preserve
legacy dimensions and verify the independent colour/depth grids used by D455.
These measurements establish acquisition behavior without recording load.

Authenticated browser acceptance covered all eight camera/model modes. Each
camera passed camera-only RGB and depth recording; cone, COCO and combined
annotation; simultaneous RGB/depth/annotated output; and annotated-only output.
Changing the viewer selection and disconnecting it left recording counters and
session identity progressing. Unauthenticated recording Start was rejected.

The private manager restart retained the recording run, PID and session. Actual
camera restarts retained the recording run and produced new source generations
and files. A D455 restart exposed changed calibration values across sessions;
the recorder now retains calibration per generation, while rejecting changes
within one generation. Source dimensions, optical frame and depth conventions
remain fixed. Exact-capture probes passed 25 samples for each individual and
combined overlay on each camera: 150 checked renders with measurement markers
disabled.

Across the four successful browser campaigns, all 32 recorded sessions decoded:
242 completed MP4 segments and 75,322 frames. Every decoded segment matched its
indexed frame count and configured dimensions. The largest relative timestamp
difference was 332,557 ns, within the 30 FPS files' 1/3000-second MP4 timescale.
Across 24,138 captures present in both RGB and annotated indices, capture
identity, presentation time and calibration matched exactly. All indexed tracks
used the declared acquisition-based timeline, retained model provenance where
applicable and kept different source generations in separate segments.

## Sustained simultaneous load

The final D455/both-detector run passed a 600.05-second measurement with all three
recording outputs and a separate 640x480/30 FPS live cone-overlay viewer, while
the annotated recording selected the combined overlay. The installer was
paused only during this measurement and resumed afterward. The host's existing
15 W power mode was unchanged. Rates below use the 590.01-second interval between
the first and last ten-second samples; status counters have their own sampling
phase.

| Path | Observed progress |
| --- | ---: |
| Paired camera acquisition | 29.983 Hz |
| Cones inference | 29.984 Hz |
| COCO inference | 29.984 Hz |
| Combined overlay rendering | 29.952 Hz |
| RGB recording | 29.957 FPS |
| Depth recording | 29.961 FPS |
| Annotated recording | 29.959 FPS |

The entire long recording session finalized 18,374 RGB, 18,377 depth and 18,376
annotated frames in 22 segments per track. Three RGB and one annotated overload
drops were counted; depth had none. No track reported a finalization failure.
All 66 completed MP4 segments decoded successfully, totaling 55,127 frames;
decoded geometry, counts and timestamps matched the independent frame indices.
The viewer presented 17,242 frames during the ten-minute measurement (28.73 FPS),
with a largest observed presentation-callback gap of 82.8 ms. This gap is not
capture-to-display latency.

| Workload cgroup | Mean CPU, percent of one core | Maximum summed RSS |
| --- | ---: | ---: |
| Perception, both detectors | 213.7% | 1,336.5 MiB |
| Video worker and native media processes | 48.3% | 529.1 MiB |
| Recorder | 75.1% | 399.8 MiB |

These process measurements exclude management and the temporary browser and can
double-count shared memory in summed RSS. Across 298 two-second tegrastats
samples, GPU activity averaged 27.2% (maximum 60%), system RAM averaged 3,737 MB
(maximum 3,834 MB), and reported input power averaged 13.56 W. Encoder utilization
was not exposed by this tegrastats output; native hardware encoding was exercised
by the actual pipelines. Only D455 received this ten-minute load measurement;
OAK-D received the finite simultaneous functional checks above.

## Synthetic failure and timing checks

Native synthetic input checked source and annotation outages, new calibration
on generation change, retired generations, wrong source/clock, duplicate capture
identity and final event flushing. RGB/depth continued through annotation gaps.
Decoded binary sequence markers matched the original indexed captures. A 5 FPS
ceiling produced 40 finalized frames and 100 counted rate drops in its finite
fixture. MP4 timestamps were checked against each track's actual timescale.

The no-index fixture finalized 127 frames and declared exact reconstruction
unavailable. Abrupt writer termination preserved 90 completed frames; a write
permission failure preserved 60. Completed segments decoded using the durable
segment ledger, which can be newer than the last status snapshot. Retention
checks reclaimed only completed owned groups, protected active/unrelated/symlink
content and reported storage exhaustion with explicit finalization status.
These are software/encoder fixtures, not observed sudden power-loss tests.

Nine native tests passed across camera, detector and recorder packages. The
final installed runtime wheel passed 178 unit tests and deployment passed 40.
All eight launch descriptions, ten native runtime checks and 22 browser-client
checks passed. Final build-path checks and installer results are recorded
separately below.

The synthetic maintenance harness passed live-workload selection refusal,
stopped upgrade/rollback with retained history, idempotent selection and
incompatible-state refusal. Its temporary management services were removed,
cleanup errors were empty and the fixture ended with empty workload ownership.

## Installer and installed build checks

The first genuine staged installer completed eight stages: source acquisition, both
SDKs, ROS, Python, model inputs, engines and native video. Its configuration
stage failed because importing recording profile validation eagerly imported
the live D-Bus supervisor into the standalone bootstrap environment. Reproducing
the import confirmed that dependency chain. A local correction moves the native
import to recording admission, with a regression that validates profiles while
D-Bus imports are unavailable. The six recording regressions, including that
case, passed on Jah after the correction. The three system-build regressions
also passed with the recorder included in the pinned system rebuild.

The failed receipt and logs are retained. A retry through the already-built
release's installed CLI correctly refused to resume the partial/failed stage
under the same release ID. No receipt or artifact identity was rewritten to
claim success. That failed release is not a successfully qualified installation.

The corrected clean bootstrap selects deployment
`484f59ce5af13948d4909a946d0a5a9b47872921` and runtime
`1b4459e1b45d84a0076147e9fbfc644f35579d69`. Its receipt and artifact hashes were
verified. Both wheel and source distributions built, and the fresh standalone
venv passed dependency consistency. All 104 runtime package files, 21 deployment
package files and 11 installed definitions matched the exact source snapshots.
All five preferred console entry points returned help in the native test venv;
the runtime source distribution retained the complete optional recorder package.

The pure bootstrap rendered a three-unit/eight-mode runtime profile successfully.
A separate configuration preflight used the corrected definitions and Python
wheels with read-only references to the earlier build's native artifacts. It
passed all effective-mode checks, service-template validation, GStreamer factory
checks and the installed runtime catalog. This preflight does not change the
failed release's receipt or establish a new complete installation.

The system-site-packages verification environment also reported an inherited
PyNaCl requirement for absent `cffi`. Neither project declares or imports those
packages; the clean bootstrap's dependency check passed. Host packages and the
project dependency lock were not changed to suppress that diagnostic.

A fresh genuine build with the corrected pins completed successfully as
`r20261107-recording-final`. All nine stages passed, including both SDKs, all
seven ROS packages, fresh cone/COCO engines, native media plugins and final
configuration. The stage sequence took 3,054.87 seconds. This build used verified
source/download caches; it did not substitute the earlier release's built
artifacts or rewrite its failed receipt.

The installed verification selected only the private installation root and
passed two verified reruns without changing build logs or selection state.
Integrity, the three-unit/eight-mode catalog and CLI routing passed. The ordinary
system-build route rebuilt the pinned packages into separate outputs and
included the native recorder. The student build and clean rebuild passed,
preserving fixture source files and using the selected system underlay. These
checks did not restart runtime or install dependencies. Permanent release
selection and integration branches were unchanged.

A final stationary D455/both-detector browser case used the completed release's
own SDKs, engines, merged ROS install, native media and Python environment. It
passed simultaneous RGB/depth/annotated recording for all three annotation
choices, annotated-only recording, viewer selection changes and disconnects.
All four sessions finalized cleanly. Their ten MP4 segments decoded to 2,886
frames with matching indices and a maximum relative timestamp difference of
220,395 ns. These are additional to the 32 earlier sessions, not a repeat of the
ten-minute measurement.

The final case reported no browser exceptions or cleanup errors and ended with
empty private workload ownership. The two test-owned `videoinstall7` management
unit files were removed, and the host reservation was released. A final fresh
inspection confirmed unchanged permanent run identities, empty workload
ownership and permanent selection `r20261104-everyday`. Private raw evidence and
both installer attempts remain available; no publication or branch merge occurred.

## Known evidence limits

The first D455 recovery attempt correctly exposed the calibration restriction
and was retained. A later recovery attempt passed recorder continuity but timed
out reconnecting the viewer after a manager restart. The sustained run separates
source recovery from that viewer path; it does not establish seamless viewer
recovery after every manager restart. Existing recovering viewer stalls remain
a separate follow-up, as agreed.

Loopback headless Chromium progress does not establish physical laptop display,
Wi-Fi reliability or driving performance. H.264/MP4 decoding does not establish
compatibility with every editing application. This campaign does not qualify a
fresh OS image, Nano, long-term endurance or a physical power cut. Development
does not authorize permanent activation, publication or branch promotion.
