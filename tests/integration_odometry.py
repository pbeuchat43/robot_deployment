"""Finite isolated camera/odometry run. Use only a reserved host and private site."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import argparse
from collections import deque
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from robot_deployment.configuration import load, encoded
from robot_deployment.profile import build_profile
from robot_runtime.common import Fault
from robot_runtime.ipc import request
from robot_runtime.profile import validate


def percentile(values, q):
    return sorted(values)[min(len(values)-1, math.ceil(q * len(values))-1)] if values else None


def main():
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from rgbd_camera_interfaces.msg import Status as CameraStatus
    from rgbd_object_detector_interfaces.msg import CaptureDetections
    from visual_odometry_interfaces.msg import Estimate, Status
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', required=True)
    parser.add_argument('--seconds', type=float, default=60)
    parser.add_argument('--warmup', type=float, default=10)
    parser.add_argument('--record', action='store_true', help='Record RGB, depth and the selected detector overlay')
    parser.add_argument('--wait-video', action='store_true', help='Wait for an external finite viewer to write video-ready')
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(mode=0o700)
    graph = load(args.site)
    # The caller supplies a private site. Never point this fixture at selected
    # management state; enforce storage beneath the experiment's parent.
    data = Path(graph['site']['storage']['data_root']).resolve()
    assert data.is_relative_to(root.parent) and data != root.parent
    (data / 'work').mkdir(parents=True, exist_ok=True)
    # Native AV uses filesystem Unix sockets with a short path bound.
    state = Path('/tmp') / ('robot-runtime-slice-' + uuid.uuid4().hex[:12])
    state.mkdir(mode=0o700)
    (root / 'state-path.txt').write_text(str(state))
    profile_path = root / 'runtime.json'
    profile = build_profile(graph, args.site, args.release, profile_path)
    profile['namespace'] = 'v' + uuid.uuid4().hex[:10]
    video = next(item for item in profile['units'] if item['id'] == 'video')
    video['argv'][video['argv'].index('--state')+1] = str(state)
    profile, revision = validate(profile)
    profile_path.write_bytes(encoded(profile))
    expected = args.mode.endswith(('-vo', '-vio'))
    namespace = '/' + graph['site']['ros']['namespace']
    report = dict(mode=args.mode, seconds=args.seconds, warmup_seconds=args.warmup,
                  backend=graph['site']['visual_odometry']['backend'], state_path=str(state), checks=[], cleanup_errors=[])
    logs = (root / 'manager.log').open('w')
    manager = subprocess.Popen([sys.executable, '-m', 'robot_runtime.manager', '--profile', str(profile_path), '--state', str(state)], stdout=logs, stderr=logs)
    observed = dict(camera=None, odometry=None)
    records = dict(cones=[], poses=[], joints=[])
    pending, history = deque(maxlen=128), deque(maxlen=128)
    previous = [None]
    measure = [None]

    def status():
        return request(state, 'status', fresh=True)

    def unit(identity='perception'):
        return next(item for item in status()['units'] if item['unit_id'] == identity)

    def command(action, identity='perception', **values):
        return request(state, action, unit_id=identity, request_id=str(uuid.uuid4()),
                       expires_at_ms=int(time.time()*1000)+10000, config_revision=revision, **values)

    def wait(function, seconds=15):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                value = function()
                if value:
                    return value
            except (Fault, FileNotFoundError):
                pass
            time.sleep(.1)
        raise AssertionError('runtime condition timed out')

    def join(now):
        while pending and history:
            acquired, detection_arrival, sequence, prior, generation = pending[0]
            if history[-1][0] < acquired:
                break
            pending.popleft()
            if history[0][0] <= prior and history[-1][2][2] == generation:
                points = list(history)
                def covered(target):
                    return any(point[0] == target for point in points) or any(
                        a[0] <= target <= b[0] and b[0]-a[0] <= 50_000_000
                        for a, b in zip(points, points[1:]))
                if covered(prior) and covered(acquired):
                    records['joints'].append(dict(sequence=sequence, acquisition_ns=acquired,
                        previous_acquisition_ns=prior,
                        latency_ms=(max(now, detection_arrival)-acquired)/1e6))

    def detection(message):
        now = time.monotonic_ns()
        if measure[0] is None or now < measure[0]:
            return
        acquired = message.capture.exposure_midpoint_ns
        records['cones'].append(dict(sequence=message.capture.sequence, acquisition_ns=acquired,
            arrival_ns=now, latency_ms=(now-acquired)/1e6, generation=message.capture.generation))
        if expected:
            if previous[0] and previous[0][1] == message.capture.generation and acquired > previous[0][0]:
                pending.append((acquired, now, message.capture.sequence, previous[0][0], message.capture.generation))
            previous[0] = (acquired, message.capture.generation)
            join(now)

    def estimate(message):
        now = time.monotonic_ns()
        acquired = max(message.capture.left.exposure_midpoint_ns, message.capture.right.exposure_midpoint_ns)
        key = (message.estimator_generation, message.association_epoch, message.capture.left.generation)
        if history and history[-1][2] != key:
            history.clear()
            pending.clear()
            previous[0] = None
        history.append((acquired, now, key))
        if measure[0] is not None and now >= measure[0]:
            records['poses'].append(dict(sequence=message.sequence, acquisition_ns=acquired,
                arrival_ns=now, latency_ms=(now-acquired)/1e6, epoch=message.association_epoch))
            join(now)

    rclpy.init()
    node = Node('integration_odometry_probe', namespace=namespace)
    node.create_subscription(CaptureDetections, namespace+'/detector_cones/capture_detections', detection, qos_profile_sensor_data)
    node.create_subscription(Estimate, namespace+'/odometry/estimate', estimate, qos_profile_sensor_data)
    node.create_subscription(CameraStatus, namespace+'/camera/status', lambda m: observed.update(camera=m), qos_profile_sensor_data)
    node.create_subscription(Status, namespace+'/odometry/status', lambda m: observed.update(odometry=m), qos_profile_sensor_data)
    try:
        wait(lambda: status()['fresh'])
        started = command('start', mode=args.mode)
        deadline = time.monotonic() + 100
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.1)
            if observed['camera'] and observed['camera'].state == 'error':
                raise AssertionError('camera: ' + observed['camera'].detail)
            if observed['camera'] and observed['camera'].state == 'streaming' and (
                    not expected or observed['odometry'] and observed['odometry'].state == 'tracking'):
                break
            if not unit()['blocked']:
                raise AssertionError('candidate exited before readiness')
        else:
            raise AssertionError('readiness timeout: ' + (observed['odometry'].reason if observed['odometry'] else 'no odometry status'))
        report['checks'].append('fresh_input_and_matched_output' if expected else 'fresh_input')
        (root / 'perception-ready').touch()
        if args.record:
            model = args.mode.split('-')[1]
            assert model in ('cones', 'coco', 'both'), 'Recording fixture requires detector output'
            command('start', 'recording', recording=dict(outputs=['rgb', 'depth', 'annotated'],
                    overlay='combined' if model == 'both' else model, frame_index=True))
            wait(lambda: unit('recording').get('recording', {}).get('state') == 'recording')
            report['checks'].append('recorder_started')
        if args.wait_video:
            deadline = time.monotonic() + 60
            while not (root / 'video-ready').exists() and time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=.1)
            assert (root / 'video-ready').exists(), 'External viewer did not confirm decoded frames'
            report['checks'].append('viewer_confirmed_frames')
        measure[0] = time.monotonic_ns() + int(args.warmup*1e9)
        end = measure[0] + int(args.seconds*1e9)
        while time.monotonic_ns() < end:
            rclpy.spin_once(node, timeout_sec=.1)
        report['camera'] = {key: getattr(observed['camera'], key) for key in ('state', 'frames', 'rejected_pairs', 'stereo_pairs', 'stereo_rejected', 'combined_imu_samples', 'combined_imu_rejected', 'combined_imu_overflows')}
        # Private evidence: do not publish device/session identities unredacted.
        report['identities'] = dict(camera={key: getattr(observed['camera'], key)
            for key in ('source_id', 'generation', 'clock_domain')})
        if observed['odometry']:
            report['odometry'] = {key: getattr(observed['odometry'], key) for key in ('state', 'reason', 'estimates', 'rejected', 'unmatched', 'association_epoch')}
            report['identities']['odometry'] = {key: getattr(observed['odometry'], key)
                for key in ('source_id', 'camera_generation', 'estimator_generation', 'association_epoch',
                            'calibration_id', 'configuration_id', 'clock_domain')}
        for kind in ('cones', 'poses', 'joints'):
            values = [item['latency_ms'] for item in records[kind]]
            report[kind] = dict(count=len(values), hz=len(values)/args.seconds,
                                p95_ms=percentile(values,.95), maximum_ms=max(values) if values else None,
                                over_100ms=sum(v > 100 for v in values), over_200ms=sum(v > 200 for v in values))
            report[kind]['minutes'] = []
            for minute in range(math.ceil(args.seconds/60)):
                start = measure[0] + minute*60_000_000_000
                window = [item['latency_ms'] for item in records[kind]
                          if start <= item['acquisition_ns'] < start+60_000_000_000]
                report[kind]['minutes'].append(dict(minute=minute, count=len(window),
                    p95_ms=percentile(window,.95), maximum_ms=max(window) if window else None))
        report['joint_fraction'] = len(records['joints'])/len(records['cones']) if records['cones'] else None
        if args.record:
            report['recording'] = unit('recording').get('recording')
            assert report['recording']['fresh'] and report['recording']['state'] == 'recording'
        if expected:
            assert records['poses'], 'No matched poses in measurement window'
        if args.mode.split('-')[1] in ('cones', 'both'):
            assert records['cones'], 'No cone results in measurement window'
        camera = observed['camera']
        assert camera.state == 'streaming', 'camera: ' + camera.detail
        assert 0 <= time.monotonic_ns()-camera.observed_ns <= min(camera.expires_after_ns, 1_000_000_000), 'Camera status expired during measurement'
        assert unit()['blocked'], 'Candidate exited during measurement'
        if expected:
            health = observed['odometry']
            assert health and health.state != 'error', 'Odometry reported an error'
            assert 0 <= time.monotonic_ns()-health.observed_ns <= min(health.expires_after_ns, 1_000_000_000), 'Odometry status expired during measurement'
        report['passed'] = True
    except BaseException as exc:
        report.update(passed=False, error=repr(exc))
        raise
    finally:
        (root / 'measurement-complete').touch()
        for identity in ('video', 'recording', 'perception'):
            current = {}
            try:
                current = unit(identity)
                if current['blocked'] and not current.get('stop_request_id'):
                    command('stop', identity, expected_run=current['run_id'])
                wait(lambda: not unit(identity)['blocked'], seconds=30)
                if identity == 'perception':
                    report['final_state'] = unit()
                    if current.get('run_id'):
                        report['journal'] = request(state, 'logs', run_id=current['run_id'], limit=100)
                elif identity == 'recording' and args.record:
                    report['recording_final'] = wait(lambda: unit(identity).get('recording') if unit(identity).get('recording', {}).get('finalization') in ('complete', 'incomplete') else None)
                    assert report['recording_final']['state'] == 'completed' and report['recording_final']['finalization'] == 'complete'
            except Exception as exc:
                report['cleanup_errors'].append(identity + ': ' + repr(exc))
            finally:
                if current.get('run_id'):
                    try:
                        report.setdefault('journals', {})[identity] = request(state, 'logs', run_id=current['run_id'], limit=100)
                    except Exception:
                        pass
        manager.terminate()
        manager.wait(10)
        logs.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        (root/'result.json').write_bytes(encoded(report))
        (root/'samples.json').write_bytes(encoded(records))
    print(json.dumps({key: value for key, value in report.items() if key not in ('journal', 'journals', 'final_state')}, indent=2))
    return int(not report.get('passed') or bool(report['cleanup_errors']))


if __name__ == '__main__':
    raise SystemExit(main())
