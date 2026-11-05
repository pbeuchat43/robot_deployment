# Jah everyday installation — 4 November 2026

The existing Jah Orin NX host now selects `r20261104-everyday` under
`~/.local/share/robot_deployment`. See the [operator guide](../../everyday-jah.md)
for paths and daily commands, and [summary.json](summary.json) for exact identities,
measurements, cleanup inventory and private evidence hashes.

## Installation and management

Deployment `7a682acafc52fc93d2b8cc02018c35842c4fdc4f` built both SDKs, the ROS
packages, Python environments, both TensorRT engines and native video in the
permanent release directory. Model inputs and the reused COCO export cache were
hash-verified. All nine installer stages passed. Normal selection verified the
completed stages and installed the CLI context, wrapper and Bash completion.

The installed `lucid_conduct` passed configuration validation, catalog, call
explanation and integrity doctor without an explicit site argument. A fresh
interactive Bash found the wrapper and completed `runtime st` to start/status/
stop, with no legacy DREAM hook, activated virtual environment or build-tree
PATH entries. The short `lucid` alias was not installed.

`robot-manager-jah.service` and `robot-web-jah.service` are enabled and active.
Existing account lingering was preserved. Permanent HTTPS pages and fresh
manager status passed with the existing trusted certificate; unauthenticated
Start returned 401. The existing credential verifier remained byte-identical
and private. The operator passphrase was neither needed nor changed.

## Observed camera and viewer checks

Both attached cameras passed unique compatible-device discovery and ran both
detectors. Each camera produced 10 exact cone, 10 exact COCO and 10 exact combined
overlay samples, with measurement markers disabled: 60 exact samples total.
Observed model/engine identities matched the installed descriptors.

The headless browser used a temporary loopback HTTPS gateway and credential,
connected to the permanent manager and native video worker. The normal LAN
gateway's HTTPS/authentication checks were separate. Each overlay selection was
explicitly connected after source readiness. Both detector counters advanced,
failures remained zero and application run identities stayed unchanged during
the three viewer selections for each camera.

| Camera / mode | Cones callbacks / 4 s | Combined callbacks / 4 s | COCO callbacks / 4 s |
| --- | ---: | ---: | ---: |
| D455 / both | 115 | 115 | 111 |
| OAK-D / both | 112 | 118 | 101 |

The initial test clicked Unlock before the page module initialized. Waiting for
initialized controls fixed this harness race. Both hardware cases then passed.
Its final assertion incorrectly required lifecycle `stopped`; runtime retains
successfully stopped runs as `exited`. The original report was preserved.
Supplemental validation checked completed stop operations with outcome
`cgroup_empty`, successful inactive supervisors, zero PIDs/members, no blocked
ownership or transition, and fresh conflict-free state.

Management was then restarted. Its generation changed, both application run
identities remained unchanged and both workloads remained stopped. The final
audit confirmed enabled/active management, the current HTTPS generation, no
leftover test or legacy processes, and all 43 removed paths absent. This is a
service restart observation, not a physical reboot test.

## Cleanup and retained recovery

Removed 35 inspected DREAM-related test/build trees older than the campaign's
one-week cutoff, plus eight legacy installation/config/data directories.
Removed the `dream_system` checkout, its Bash hook, four superseded management
units, three legacy global ROS assignments and DREAM camera/lidar udev rules.
The operator applied the reviewed root script; its resulting files and attached
camera access were verified. New camera permissions grant the runtime account
access to compatible OAK and D455 devices.

Disk usage on the root NVMe filesystem was initially 82% (about 20 GiB free).
After cleanup and the new permanent build it was 51%, with 58,741,772,288 bytes
(about 54.7 GiB) available. Shared system dependencies, independent source work,
recent qualification artifacts and the Windows checkouts were preserved.
Older private raw evidence directories listed in the summary are retired;
their committed historical summaries remain available.

The previous independent RGB-D release, its configuration/state and a guarded
management restore helper were retained. Paths and helper syntax were checked;
a restoration round trip was not run. No new deployment depends on the deleted
`dream_system` installation. The agreed pinned cone ONNX artifact still comes
from the legacy detector repository; that detector is not built or installed.

Private run reports, imagery, credentials and device identities remain on Jah.
This campaign does not establish fresh-image/Nano deployment, laptop display
performance, endurance, firmware flashing or vehicle control. Existing broader
software and six-mode acceptance evidence was not repeated. No implementation
changed, repository was published, or branch was promoted to `main`.
