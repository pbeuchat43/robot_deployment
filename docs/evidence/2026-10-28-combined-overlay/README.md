# Combined overlay — 28 October 2026

The separate `CombinedOverlayNode` and the Cones / COCO 80 / Combined video
choices passed both-camera integration. The selected release is
`rgbd-20261028-combined`, retaining the unchanged runtime 0.1.0.dev21 package.
Camera and video workloads were left stopped; manager/web services remain active.

| Check | Observed result |
| --- | --- |
| Native software | Four native checks passed, including the new bounded join and renderer cases |
| Exact images | 25 cones, 25 COCO and 25 combined per camera: 150 total, including 50 combined |
| Viewer selections | Cones → Combined → COCO → Cones on D455 and OAK-D |
| Detector continuity | Both counters advanced in every selection; camera/detector generations and perception/video run identities stayed unchanged |
| Combined delivery | 86 D455 and 97 OAK-D presentation callbacks in the four-second windows after source readiness |
| Combined status | Streaming while selected, idle without demand; no render failures or cache-capacity violations |
| Deployment | TLS-verified HTTPS routes, installed assets and dual-only choice applicability passed; dev21 rollback retained |
| Cleanup | Isolated processes exited, reservation released, 15 W power mode unchanged |

The combined probe compares each output batch with the independently received
model batch using serialization with initialized padding (preserving NaN fields).
It then compares every image byte and header against a fresh render of those
batches on the exact original RGB acquisition. All probe caches are bounded and
full-image subscriptions are released after the requested sample count.

The first campaign passed D455 exact matching and its Cones/Combined selections,
then failed the COCO progress threshold with seven presentation callbacks. That
window began at WebRTC connection while the new ROS image subscription was still
starting; native COCO no-consumer counts rose until near the window's end. The
harness was corrected to bound source startup separately (15 seconds), then
apply the same four-second, more-than-20-callback delivery check. Both cameras
passed. Source readiness took about 2.1–4.9 seconds after transport connection.
No runtime or detector code changed between these two campaigns. The failed
record and its clean cleanup remain accounted for in [hardware.json](hardware.json).

These are finite functional checks with headless Chromium on Jah. They do not
establish sustained display FPS, physical screen latency, detection accuracy,
new empty-scene behavior, USB recovery or multiple-viewer behavior. Exact matching
can skip captures when either detector lacks a matching fresh result. Processing
deltas include selection, reconnection, startup and the delivery window; they
must not be interpreted as four-second inference rates.

- [Software and installed artifact identity](software.json)
- [Camera, exact-image and viewer evidence](hardware.json)
- [Selected deployment and HTTPS audit](deployment.json)
- [Cleanup and workload preservation](cleanup.json)

Feature commits are preserved before consolidation into `dev`. No `main` branch
was promoted. Device IDs, credentials, private imagery and raw reports remain
outside source control. Rollback instructions are in [the deployment guide](../../deployment-jah.md).
