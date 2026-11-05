# Deployment implementation verification — 3 November 2026

Verification uses the existing Jah Orin NX 16GB/reference-carrier host, isolated
storage, management namespace, ROS domain and network ports. This is an
application installation on a prepared host, not a clean-image or Nano
qualification. The initial prerequisite package script was reviewed and applied
by the operator. No base image or MCU firmware was flashed.

**Installer/operator checks, all six D455/OAK-D modes and a controlled
D455-to-OAK selection change pass.** The
[redacted summary](summary.json) records exact identities, measurements and limits.

## Software identity

The full native release is built from deployment
`edb8aacbef5468788609f276a0ea1e0a2acc1dee`. The final operator package is
`3c73d6648914c451750fc23155afa0c399556411`; its differences are CLI help,
explicit JSON/readable presentation, call explanation, local context
resolution and Bash filename-completion fallback. It is bootstrapped and tested
separately against the frozen native release. Installation, configuration,
preparation and launch implementation are unchanged between those commits.
Build provenance is not rewritten to imply
that the later CLI was part of the earlier native build.

Selected components are camera `0f4b82958f0d7798f0bf911641d0aa67084cc927`,
detector `61219c6c1a692d311383cede66f1fb45b20f36e0` and runtime
`753ba241034371bcc93b7157ad7e63d03753aaf4` (`0.1.0.dev24`). The
[source lock](../../../sources.json) records the exact SDK, model and tool
selections. Documentation/evidence commits following these implementations do
not imply new binary builds.

## Completed software checks

- Final bootstrap succeeds; all **38 deployment unit checks** pass against the
  installed package outside the source checkout, with `PYTHONPATH` unset.
- Runtime's restart/operator implementation passed **169 unit checks**. The
  later authorization case passed with all **17 web checks**; those overlap the
  baseline suite. The **two new maintenance checks** also pass.
- Native lifecycle passes **10 checks**, ordinary browser **6**, prepared restart
  **4**, and native WebRTC browser **16**. Each report has empty cleanup errors.
- Real systemd maintenance passes **four synthetic checks**: management without
  application startup; refusal while a workload is live; stopped upgrade and
  rollback preserving history; and idempotent/incompatible-state handling.
  Cleanup errors are empty.
- Real interactive Bash verifies full-command and alias dispatch, completion
  registration, rerun and owned removal. A welcome-banner lookup ambiguity found
  during this check was fixed before the final pass. A real terminal check also
  exposed a blank completion candidate blocking filename fallback; the fix
  passes actual Tab completion for both the full command and alias.
- Host plans report no missing prerequisites. Generated account/USB, repository
  and package scripts pass Bash syntax checks; these newly generated scripts
  were not applied to this already prepared host.

The first full installation completed before the laptop/Jah restart and was
preserved. A subsequent unselected build was stopped after the Bash lookup bug
was discovered; its partial outputs and logs remain available. The corrected
native release passes all nine build stages. It builds both SDKs, ROS packages,
Python packages, both target engines and an independent native-video prefix,
then validates the complete profile and artifacts. It reuses the hash-verified
model export cache created by the first full installation; it does not claim a
second export execution.

Installed acceptance passes all four checks: selection and verified rerun
without rebuilding or changing selection history; final CLI catalog/doctor/call
explanation; a real system ROS build into separate outputs; and student
build/clean preserving sources and using the selected underlay. An initial test
harness preflight mistakenly applied the small configuration-file limit to the
large installation inventory; its reader was corrected before this passing run.

## Observed camera acceptance

The installed release uses unique compatible-device discovery with no device-ID
constraint. Actual model and engine identities match the release.

| Mode | Individual exact samples | Combined exact samples | Viewer selections |
| --- | --- | --- | --- |
| D455 cones | 25 cones | Not applicable | Cones |
| D455 COCO | 25 COCO | Not applicable | COCO |
| D455 both | 25 cones + 25 COCO | 25 | Cones → Combined → COCO → Cones |
| OAK-D cones | 25 cones | Not applicable | Cones |
| OAK-D COCO | 25 COCO | Not applicable | COCO |
| OAK-D both | 25 cones + 25 COCO | 25 | Cones → Combined → COCO → Cones |

OAK-D was initially absent and was reconnected by the operator after D455
acceptance. A further both-model run checks a controlled D455-to-OAK restart
with both cameras attached. It replaces the perception run while preserving
the video run, and adds 100 individual and 50 combined exact samples.

Across the three campaigns, **300 individual and 100 combined exact samples**
pass. All **20 four-second viewer windows** pass, with **92–115 presentation
callbacks** after source readiness (observed readiness 1.33–4.35 seconds). Dual selection
changes preserve perception/video runs and camera/detector generations while
both inference counters advance. Inactive models report no fresh stale sample.
Combined rendering reports no failures and respects its cache bounds. These
are finite headless observations, not an endurance or laptop-display benchmark.

Each campaign also checks parameter restart. An out-of-range request, `0.95`,
is rejected before stopping the original run.
A valid restart accepts `0.6`; changing the request file to `0.7` afterward does
not change the frozen snapshot or the node's observed `0.6` value. The selected
mode is inherited and both old/new run identities are recorded.

Cleanup reports no errors. Fresh final state has no conflicts, blocked units or
owned members. No task process remains; earlier persistent workloads are
unchanged, request input is restored and the reservation is released. The
isolated completed release and private evidence are retained for inspection and
later qualification.

## Reproduction and limits

Use the [test runbook](../../../tests/README.md) with a new private output
directory and matching bootstrap. `integration_installed.py` selects and reruns
the completed release through its matching neutral installation adapter, then
uses the separately installed final CLI for catalog, doctor, call explanation
and real system/student builds. It preserves original installation identity.

Camera acceptance uses the installed native probes and private headless
Chromium harness. It requires 25 exact samples per active individual overlay
and 25 combined samples in each both-model mode. Each viewer selection must
produce more than 20 presentation callbacks during four seconds after bounded
source readiness; dual switching must preserve runs/generations and advance
both detector counters. Parameter restart rejects an invalid request before
stop and verifies the accepted value in the replacement despite a subsequent
request-file edit.

Private raw reports, source/overlay images, screenshots, credentials and device
identities remain on Jah. Headless browser results do not establish observed
laptop display performance, detection accuracy, vehicle control, recording,
endurance, physical replacement, ambiguity or unplug/replug behavior. The
existing brief viewer-stall follow-up remains separate. Firmware dispatch checks
do not establish physical flashing. No repository was published or promoted to
`main` as part of this work.
