# Event video recording

Use a hardware H.264 NX profile with the selected native recorder installed.
Camera acquisition remains shared. The recorder does not open another camera,
operate the vehicle or restart a missing source. RC remains the driving channel.

Start perception in a camera-only, single-detector or dual-detector mode, then
start recording independently of live video:

```sh
lucid_conduct runtime start perception --mode oak-both
lucid_conduct runtime start recording --outputs rgb annotated depth --overlay combined
lucid_conduct runtime status --fresh
lucid_conduct runtime stop recording
```

`d455-camera` and `oak-camera` provide paired acquisition and plain RGB viewing
without inference. Every mode offers **Camera RGB** in the viewer. A recording
selects any nonempty subset of `rgb`, `annotated`, and `depth`; annotated output
requires `--overlay cones`, `coco`, or `combined`, available in the running mode.
The authenticated Video page exposes the same Start/Stop policy and per-output
state. Its recording overlay selection is independent of the viewer selection.

Source settings are copied from the current perception run's frozen snapshot.
Editing startup parameters afterward does not reconfigure that recording.
Start acceptance means a worker was admitted; inspect the reported state and
encoded counters to establish source readiness. Browser disconnection, viewer
selection and management-service restart do not own the recorder's lifecycle.

The site example selects 1280x720 at 30 Hz on either camera. Legacy source
profiles remain selectable. Models still use their fixed 640x640 preprocessing;
recording preserves the configured source geometry. The viewer has its own
resized canvas and bitrate. The colourized-depth output uses a recorded fixed
distance range (default 0.25–15 m), blue/cyan/yellow/red palette, black invalid
pixels and saturated endpoints. It is not a metric-depth archive.

Each session uses a unique directory under `recording.root` (default
`storage.data_root/recordings`). It contains separate hardware H.264 MP4 tracks,
segmented near 30 seconds, plus a manifest, state, events and per-track segment
ledgers. Default target bitrates are 6 Mb/s RGB, 6 Mb/s annotated and 4 Mb/s depth:
all three nominally use about 7.2 GB/hour plus metadata/container overhead.
Actual encoded size depends on scene and encoder behavior.

Frame indices are enabled by default. `--no-frame-index` disables exact
encoded-frame capture reconstruction for that session. Index rows map track and
segment presentation times to source identity, sequence, acquisition/receipt
timestamps, clock, generation, calibration and applicable model provenance.
Integers are decimal strings. Equal frame numbers in separate tracks do not
establish alignment. RGB and annotated tracks use RGB acquisition time; depth
uses its own acquisition time on the common source timeline.

Input queues are bounded. Rate, overload and rejected-input counters identify
drops; the timestamps preserve elapsed time. An unavailable overlay leaves RGB
and depth recording active. Players may hold the last image across a timestamp
gap; consult the events and indices. Camera loss closes available segments and
waits for the same compatible source. A new generation starts new files and
records its own calibration and intrinsics in the generation event. Dimensions,
optical frame and image/depth conventions must remain compatible; calibration
cannot change within a generation. Late retired generations, different cameras
and incompatible geometry are rejected.

Stop is explicit and does not finish until the worker exits. Inspect both the
process ownership and reported `finalization`; an accepted Stop is not a file
completion guarantee. Abrupt termination can lose the active MP4 segment.
Previously completed files remain available through each `*-segments.jsonl`
ledger, which may be newer than the last status snapshot. An interrupted session
is not automatically restarted or resumed. A recording failure does not restart
perception; inspect per-track failures and preserved files.

Storage defaults to a 10,000,000,000-byte managed budget and a separate
1,000,000,000-byte filesystem reserve. Reclamation removes the oldest completed
recorder-owned sessions as whole groups. Active, failed, interrupted, unrelated
and symlink-containing groups are protected. When those rules cannot make room,
the recorder finalizes and reports `storage_stop`; it does not silently overwrite
old files. Budgets, bitrates, segment duration, FPS ceiling and visualization
range are site settings. Reclamation includes metadata in the managed total.

Rebuild the selected interface packages and native recorder together. The Python
runtime wheel alone does not install native recording support. The Nano profile
reports recording unavailable; fresh Nano qualification is outside this feature.
Software fixtures, local headless-browser delivery and finite stationary camera
checks do not establish remote laptop display or driving performance. Consult the
[dated integration evidence](evidence/2026-11-07-recording/README.md) before
selecting a release.
