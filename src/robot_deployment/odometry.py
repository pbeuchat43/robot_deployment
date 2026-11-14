"""Installed estimator recipes and finite camera/model/odometry combinations."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import json
from pathlib import Path
import subprocess

from .configuration import require, file_digest


def modes(graph):
    enabled = graph['site']['visual_odometry']['enabled']
    supported = graph['cameras'].get('stereo_profiles', [])
    return {camera + '-' + model + ('' if mode == 'off' else '-' + mode): (camera, model, mode)
            for camera in ('d455', 'oak') for model in ('camera', 'cones', 'coco', 'both')
            for mode in (('off', 'vo', 'vio') if enabled and graph['site']['camera_profiles'][camera] in supported else ('off',))}


def artifact(graph, release, *, check_available=False):
    path = Path(release) / 'visual-odometry/manifest.json'
    require(path.is_file() and path.stat().st_size < 4 * 1024 * 1024, 'Install the selected odometry backend before rendering or preparing VO/VIO')
    value = json.loads(path.read_text())
    require(value.get('schema_version') == 1 and value.get('backend') == graph['site']['visual_odometry']['backend'], 'Installed odometry backend differs from selected site')
    require(value['source_id'] == graph['sources']['components']['visual_odometry']['commit'] and
            value['camera_source_id'] == graph['sources']['components']['rgbd_camera']['commit'], 'Odometry image/prefix and host interface source revisions differ')
    require(file_digest(path.parent / 'estimator.yaml') == value['preset_sha256'], 'Estimator preset identity changed')
    if check_available:
        if value['backend'] == 'docker':
            try:
                found = subprocess.check_output(['/usr/bin/docker', '--host', 'unix:///var/run/docker.sock', 'image', 'inspect',
                                                 '--format', '{{.Id}}', value['image']], text=True, timeout=2).strip()
            except (OSError, subprocess.SubprocessError) as exc:
                raise ValueError('Installed odometry image or Docker daemon is unavailable') from exc
            require(found == value['image'], 'Installed odometry image is unavailable')
        else:
            from .platform import package_version
            require(all(package_version(name) == version for name, version in value['host_packages'].items()),
                    'Native estimator host dependencies changed; prepare a new release')
            require((path.parent / 'run.sh').is_file() and (path.parent / 'install/setup.bash').is_file(), 'Native estimator prefix is unavailable')
    return value, file_digest(path)


def configure(graph, release, camera, mode, mount, *, check_available):
    require(camera['fps'] == 30., 'Stereo odometry requires the admitted 30 Hz camera profile')
    camera.update(publish_stereo=True, enable_imu=mode == 'vio', combine_imu=mode == 'vio')
    if camera['backend'] == 'oak':
        camera.update(imu_rate_hz=200 if mode == 'vio' else 0, mono_exposure_us=20000, mono_iso=800)
    else:
        camera.update(depth_width=640, depth_height=480)
    camera.update(left_frame=camera['backend'] + '_left_optical_frame',
                  right_frame=camera['backend'] + '_right_optical_frame',
                  imu_frame='oak_imu_native_frame' if camera['backend'] == 'oak' else 'realsense_imu_frame')
    value, manifest_sha = artifact(graph, release, check_available=check_available)
    namespace = '/' + graph['site']['ros']['namespace']
    config = dict(schema_version=1, mode=mode, camera_backend=camera['backend'], namespace=namespace,
                  camera_node=namespace + '/camera', executor='single' if camera['backend'] == 'realsense' else 'multi',
                  frames=dict(body=mount['child_frame'], odom='odom', left=camera['left_frame'], right=camera['right_frame'], imu=camera['imu_frame']),
                  preset_sha256=value['preset_sha256'], backend_identity=value['image'] if value['backend'] == 'docker' else 'sha256:' + manifest_sha)
    return dict(backend=value['backend'], manifest_sha256=manifest_sha, argv=value['argv'], config=config,
                startup_timeout_seconds=90.)


def docker_recipe(graph, release, environment):
    value, _ = artifact(graph, release)
    return dict(image=value['image'], argv=value['argv'], gpu=True, prepared_input='odometry',
                environment={**{key: environment[key] for key in ('ROS_DOMAIN_ID', 'ROS_AUTOMATIC_DISCOVERY_RANGE', 'RMW_IMPLEMENTATION')},
                             'FASTRTPS_DEFAULT_PROFILES_FILE': '/run/robot/fastdds.xml', 'ROS_LOG_DIR': '/tmp/ros-log', 'HOME': '/tmp'},
                mounts=[dict(source=str(Path(release) / 'ros/install/share/rgbd_camera/fastdds_local_frames.xml'), target='/run/robot/fastdds.xml')])
