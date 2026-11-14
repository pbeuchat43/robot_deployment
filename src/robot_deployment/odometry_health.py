"""Fail candidate startup without a fresh matched estimate; never auto-restart."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import argparse
import hashlib
import json
from pathlib import Path
import time


def main():
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from visual_odometry_interfaces.msg import Status
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    identity = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    rclpy.init()
    node = Node('odometry_readiness', namespace=config['namespace'])
    started = time.monotonic()
    state = dict(ready=False, last=None, failed=None)

    def receive(message):
        now = time.monotonic_ns()
        if message.configuration_id != identity or message.mode != config['mode']:
            state['failed'] = 'odometry_configuration_mismatch'
            return
        if not 0 <= now - message.observed_ns <= min(message.expires_after_ns, 1_000_000_000):
            return
        state['last'] = time.monotonic()
        if message.state == 'error':
            state['failed'] = message.reason
        if message.state == 'tracking' and message.estimates > 0 and message.last_output_ns > 0:
            if not state['ready']:
                node.get_logger().info('First fresh matched odometry estimate received')
            state['ready'] = True

    subscription = node.create_subscription(Status, config['namespace'] + '/odometry/status', receive, qos_profile_sensor_data)
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=.2)
            now = time.monotonic()
            if subscription.get_publisher_count() > 1:
                state['failed'] = 'multiple_odometry_publishers'
            if not state['ready'] and now - started >= 90:
                state['failed'] = 'odometry_startup_deadline_exceeded'
            if state['ready'] and state['last'] is not None and now - state['last'] > 3:
                state['failed'] = 'odometry_status_unavailable'
            if state['failed']:
                node.get_logger().error(state['failed'])
                return 1
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
