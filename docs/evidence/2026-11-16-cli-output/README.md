# CLI output verification on Jah

Software checks passed on reserved Jah with deployment `0.1.0.dev9` at
`570e63e0f88e901a25328f50f4ad1036094ea7ee` and runtime `0.1.0.dev30` at
`ea91a1d904eae688f5098fc5052b962aa5545ef5`. Documentation-only follow-ups do not
change these installed identities. Exact source selections and wheel/source
distribution hashes are in [summary.json](summary.json).

## Output contract and audit

Every public `lucid_conduct` family uses readable output by default. `--json`
keeps result/error payloads and exit codes, with JSON Lines for watches and log
follow. Progress, prompts and tool diagnostics use stderr. Request IDs remain
flushed to stderr before mutation submission. Standalone `robot_runtime` and
`robot-runtime` retain JSON defaults, accept explicit `--json`, and offer
`--human`; service-worker protocols and the private Pico client are unchanged.

The audit covered install/upgrade/rollback, configuration, host plans, information,
doctor, ROS/MCU builds, flash, Pico operations, calibration, shell integration,
all runtime/ROS command families, parser/operational errors and five streaming
paths. The affected maintenance consumer now requests `--json`; installed-release
verification parses the entire stdout document and retains stderr separately.
No public CLI consumers were found in sibling component repositories.

Real-profile previews found two excessive outputs that the small fixtures did
not expose. Human status repeated mode/recording definitions in 318 lines; it now
summarizes current state in 63 lines while retaining diagnostics and recovery IDs.
Installation information expanded the full artifact inventory into 14,925 lines;
it now presents provenance and stage/artifact counts in 27 lines. JSON still
contains the complete payloads. Dedicated regression tests cover both cases.

## Package and software evidence

- The standard bootstrap ran from the clean selected Git commit on Linux
  aarch64/Python 3.12.3. Both wheels and source distributions built, pinned
  dependencies installed, and `pip check` passed.
- All 106 runtime and 26 deployment installed package files matched their build
  sources byte-for-byte, including bundled assets/notices and build identity.
- All nine console names accepted help: the four preferred runtime commands,
  their four compatibility aliases, and `lucid_conduct`. Both standalone CLI
  spellings returned identical default/explicit JSON for validation and readable
  output with `--human`.
- Compilation and **202 runtime + 68 deployment unit tests** passed with
  `PYTHONPATH` unset, using installed wheels outside the source trees.
- Native runtime verification passed **10 checks**, including lifecycle,
  recovery, stale-run rejection, logs, descendants and conflict handling.
- Synthetic deployment maintenance passed **4 checks**, covering stopped
  selection/rollback, live-workload refusal, idempotence and state compatibility.
- Native CLI output verification passed **14 checks** through actual subprocesses
  and IPC: human/JSON reads, finite status/resource/log streams, SIGINT exits,
  runtime/parser errors and recovery IDs.
- Native ROS verification passed **12 checks** in a private localhost domain,
  including shared subscriptions, lossless integers, freshness, service dispatch,
  durable deduplication and worker/manager recovery. All subscriptions were
  released at completion.

Every native report had empty cleanup errors, fresh final observations, unblocked
units and no retained member processes. Resource-watch consumers returned to zero.
Raw logs, synthetic state and credentials remain private on Jah.

## Deployment status

Jah now selects `r20261116-cli-output-v2`, with the manager and HTTPS web service
running and application workloads stopped for operator testing. The existing
`r20261115-dev` release passed integrity/ownership checks and remains the recorded
rollback predecessor. The first unselected `r20261116-cli-output` build was
interrupted to include the installation-summary correction; its attempt record,
partial outputs and logs were retained, with no surviving build children.

The corrected release completed all ten standard build stages from the selected
bootstrap in approximately 56 minutes. A stage-only rerun verified and reused
every stage without invoking another build command. All stage records remained
unchanged through the rerun and normal activation. The installed launch-description
check also passed all 48 mode/backend cases without starting workloads.

Post-selection checks passed through the public `lucid_conduct` wrapper:

- Installed version, fresh status, unblocked stopped workloads, complete JSON
  catalog, readable tables, and release integrity.
- Human and JSON operational errors retain stderr and exit code 1.
- A private student-workspace fixture intentionally failed its CMake build and
  preserved the build failure and JSON error. Its corrected build then succeeded
  through real colcon, with a single JSON document on stdout and diagnostics on
  stderr. The user's student workspace was not used.
- The HTTPS page and status API responded using the configured certificate;
  the API reported the selected configuration revision.
- Both management services were active, with the old release retained as rollback.

All 106 runtime and 26 deployment files in the selected release matched the tested
bootstrap sources. The installer rebuilt the runtime wheel, so its deployed
archive hash differs from the bootstrap test wheel; both hashes are recorded in
[summary.json](summary.json). Installed source bytes and versions are identical.

## Limits

These checks establish CLI/software behavior and synthetic lifecycle cleanup.
They do not establish fresh camera, Pico, ESC, physical display or vehicle
acceptance. No schema/state migration or native interface change is part of the
formatting change. Existing hardware evidence retains its original identities.
