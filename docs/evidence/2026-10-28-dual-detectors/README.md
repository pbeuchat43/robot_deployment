# Shared-camera cone and COCO detectors - 28 October 2026

Both existing detectors ran together at approximately 30 results/s each from one
D455 or OAK-D. No camera or detector implementation change was required. This was
an isolated feasibility/performance experiment; the installed single-model
runtime profile and viewer selections were not changed.

## Configuration and method

The deployed `rgbd-20261027-dev20` components and existing target-built TensorRT
engines were reused. Component pins are in [sources.json](../../../sources.json);
tested engine/profile hashes and cleanup are in
[artifact-and-cleanup.json](artifact-and-cleanup.json). The host remained in its
existing 15 W power mode with four CPU cores online. Power/clock settings were not
changed. The current stationary room contained cones and ordinary objects.

Each case used one `component_container_mt`, one camera, and either one detector
or two independently named detector components. All components enabled ROS
intra-process communication. Both detector subscriptions targeted the same atomic
RGB-D frame topic. Separate model namespaces kept batch and status topics distinct.
Camera image publication and both overlay workers were disabled. External probes
subscribed only to batches and status; they did not subscribe to RGB-D images.

Six cases were measured: cones alone, cones plus COCO, then COCO alone, first on
D455-30 and then OAK-30. Each case had ten seconds of warm-up and a nominal
45-second measurement window (actual durations are in the JSON). CPU and memory
were sampled from the perception cgroup. Probe costs were recorded separately.
`tegrastats` sampled whole-host GPU utilization once per second. Results are finite
observations, not endurance, thermal-soak, driving or avoidance acceptance.

## Results

CPU is percent of one core: 100% means one fully occupied core. The perception
group includes acquisition, both model workers when selected, and the launcher.
GPU columns are sampled median/maximum utilization. Latency is acquisition to
completed detection batch, in host monotonic time; no display latency was measured.

| Camera | Models | Results/s, cones / COCO | CPU % | GPU median / max % | Cone latency p50 / p95 ms | COCO latency p50 / p95 ms | Peak RSS MiB |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| D455 | cones | 29.98 / - | 123.8 | 17.5 / 40 | 42.7 / 43.4 | - | 726 |
| D455 | both | 29.98 / 29.96 | 166.2 | 25 / 65 | 45.4 / 46.8 | 50.5 / 52.7 | 770 |
| D455 | COCO | - / 29.96 | 120.5 | 13.5 / 38 | - | 46.3 / 47.0 | 726 |
| OAK-D | cones | 30.00 / - | 35.7 | 11 / 39 | 49.5 / 56.0 | - | 849 |
| OAK-D | both | 30.00 / 30.00 | 89.5 | 36 / 65 | 53.3 / 60.0 | 60.5 / 67.4 | 898 |
| OAK-D | COCO | - / 30.00 | 54.2 | 13.5 / 38 | - | 55.5 / 62.1 | 870 |

Compared with cones alone, adding COCO increased perception CPU by approximately
0.42 core on D455 and 0.54 core on OAK-D, and peak RSS by approximately 44 MiB and
50 MiB respectively. Cone median latency increased by 2.70 ms and 3.72 ms; its
p95 increased by 3.40 ms and 3.91 ms. Both dual configurations retained the full
camera rate, without measured pending-frame replacement or stale-result rejection.

Every measurement window had streaming camera/detector states, zero camera
sequence gaps or pairing rejections, and zero detector rejection, stale expiry,
supersession or failure. The two recorded output streams shared 1,368 exact
capture identities for D455 and 1,375 for OAK-D, with one camera generation in
each dual case. This establishes that both produced results for the same captures;
it is not allocation/copy instrumentation. Best-effort probe receipts can omit
results, so rates and replacement counts use the detector status counters.

The reported labels included blue/yellow cones and ordinary COCO classes such as
keyboard, laptop and TV. They are model predictions, not ground-truth annotations.
Full timing quantiles, counts, labels and resources are in [summary.json](summary.json).

## Interpretation and implementation boundary

The existing acquisition adapter moves the owned RGB/depth vectors into one
atomic frame. Detector subscriptions retain `Frame::ConstSharedPtr`, and both
components run in the same intra-process container. That topology shares the
acquired image/depth storage without requiring a second full-frame input copy
for the additional detector. Each worker still has its own bounded processing
and latest-pending slots, so models can select different captures under overload.
Downstream consumers must retain capture identity and freshness checks.

Each detector independently preprocesses into its own pinned input tensor and
transfers that tensor to its GPU buffers. These costs are not eliminated by shared
source-frame ownership. The cone profile stretches; COCO letterboxes. The D455
source therefore needs different model inputs. Even square OAK input still has
separate color conversion, normalization and tensor packing for each model.
Each backend has its own TensorRT execution context and nonblocking CUDA stream;
there is no global inference mutex or cone-priority scheduling policy.

Permanent dual-mode support mainly needs composition/profile changes: load both
components, expose their separate data and processing status, and choose which
overlay feeds the viewer. A combined exact-capture overlay would require a bounded
join by capture identity in the presentation layer. Neither feature was added
to the persistent deployment by this experiment.

A per-detector rate cap, such as running COCO less often than cones, would require
a small admission-policy change because no such parameter currently exists.
It should skip work before preprocessing and retain the freshest pending frame.
It was not needed to sustain 30 Hz in this experiment and was not implemented or
measured. Neither current stream has a reserved compute budget or deadline guarantee.

The observed CPU/GPU use supports dual operation at 30 Hz in these conditions.
It does not establish a fixed remaining GPU capacity: utilization is whole-host,
sampling can miss short peaks, clocks were not fixed, and these tegrastats logs
did not report GPU frequency or EMC utilization. No viewer, encoder, navigation,
tracking or vehicle-control workload was added. Model-specific 2D/spatial results
also do not establish a complete obstacle-avoidance system or coverage of obstacles
outside the COCO categories.

## Reproduction and cleanup

The finite launch, orchestration, sampling and summarization scripts, their hashes,
raw CSVs and tegrastats logs are retained privately on Jah under
`~/.local/state/rgbd-verification/dual-20261028`, campaign `4f88c12094`.
The launch creates one camera and one or two existing detector components with
the topology above; it does not patch, rebuild or replace installed components.
Re-running it requires reserving Jah and leaving the persistent camera/video
workloads stopped. Raw camera identifiers remain outside source control.

All six experiment units and metadata probes stopped normally. The verification
reservation was released, power mode was unchanged, and the user's pre-existing
stopped camera/video workloads stayed stopped with their run records preserved.
Persistent management services remained active. No changes were made to the
previously accepted physical-test findings.
