# OAK viewer and empty-scene acceptance follow-up

The original five-second OAK-D/COCO interruption lost overlay subscribers while
camera and inference processing continued. The operator confirmed the viewer
remained visible and reported weak Wi-Fi at the Jetson location. The original
browser diagnostics were unavailable, so its exact trigger remains unproven.

The [viewer comparison](viewer.json) records isolated, headless Chromium runs on
reserved Jah. Each included a two-minute live OAK-D/COCO baseline. A controlled
transport closure recovered automatically on both versions. On dev21, one
injected renewal network failure immediately disconnected the viewer, removed
media admission and eventually released capture demand, while inference continued.

Dev22 retries renewal of the same token within a bounded lease window. A
two-second injected renewal failure preserved the subscription and transport;
all 21 observation samples remained connected with one media subscription, and
inference processed 516 more frames. Sustained renewal failures expired the
subscription; explicit Connect restored video without restarting perception.
Both isolated campaigns preserved persistent workloads and cleaned up without
errors. This demonstrates the reproduced failure path and its recovery; it does
not establish the original event's radio-network cause or physical display timing.

The [deployment audit](deployment.json) records dev22 selection with stopped
workloads, unchanged services, matching served assets and verified HTTPS.
The prior combined release and coherent rollback backup are retained. The
runtime repository contains the 147-unit/22-browser verification report.

The [physical empty-scene check](empty-scenes.json) passed with both detectors
running and the Combined view selected. Cones had 20.10 continuous seconds of
zero-detection batches and COCO had 24.50 seconds; both returned detections. The
operator confirmed that displayed boxes cleared and returned. Each interval was
measured entirely within the same capture generation; the earlier run before an
operator restart was excluded. Camera gaps/rejections, detector stale/rejected
results, inference failures and overlay failures remained zero. Metadata-only
observers created no extra image demand.

The operator reported a few **Video stalled** notices lasting about one to two
seconds, each recovering automatically. These differ from the original loss of
subscription, but uninterrupted physical viewing is still not accepted. The
largest observed acquisition interval in the measured generation was 133.48 ms;
maximum result source age was 173.09 ms for cones and 178.51 ms for COCO. These
native observations do not identify where the brief display stalls occurred.
The user's browser measurement export was not retrieved: browser-control calls
timed out. Wi-Fi delivery remains a hypothesis, not an established cause.

The operator requested that testing stop for the night. The temporary observers
were stopped and the exact host reservation was released; current user camera
and video runs, management services and power settings were preserved. See the
[cleanup audit](cleanup.json). Further stall diagnosis is deferred to a future
discussion; the next useful evidence would be the viewer's **Save measurements**
export captured before reloading a session that has stalled.
