"""Coordinated mode, preparation and backend identity boundaries."""
# Copyright (c) 2026 Paul N. Beuchat. MIT License.
import json
import subprocess
import unittest
from unittest.mock import patch

from robot_deployment.configuration import encoded, digest, ConfigurationError
from robot_deployment.odometry import modes
from robot_deployment.preparation import effective, prepare
from robot_deployment.profile import build_profile
from robot_runtime.prepared import freeze, load as frozen
from robot_runtime.profile import validate
import test_configuration


class OdometryTests(unittest.TestCase):
    setUp = test_configuration.ConfigurationTests.setUp
    tearDown = test_configuration.ConfigurationTests.tearDown
    save = test_configuration.ConfigurationTests.save
    graph = test_configuration.ConfigurationTests.graph

    def installed(self, backend='docker'):
        self.site['visual_odometry'] = dict(enabled=True, backend=backend)
        self.save()
        graph = self.graph()
        target = self.work / 'release/visual-odometry'
        target.mkdir(parents=True, exist_ok=True)
        (target / 'estimator.yaml').write_bytes(b'fixture')
        artifact = dict(schema_version=1, backend=backend, source_id=graph['sources']['components']['visual_odometry']['commit'],
            camera_source_id=graph['sources']['components']['rgbd_camera']['commit'], preset_sha256=digest(b'fixture'),
            image='sha256:' + 'a'*64, argv=['/bin/bash', '/opt/visual_odometry/run.sh'])
        (target / 'manifest.json').write_text(json.dumps(artifact))
        return graph, target.parent

    def test_24_modes_default_off_and_consistent_video_recording(self):
        graph, release = self.installed()
        profile, _ = validate(build_profile(graph, self.path, release, self.work / 'runtime.json'), check_paths=False)
        unit = profile['units'][0]
        self.assertEqual(len(unit['launch_modes']), 24)
        self.assertEqual(unit['default_launch_mode'], 'oak-both')
        self.assertEqual(len(unit['launch_selections']), 3)
        for mode in unit['launch_modes']:
            family, model, odometry = modes(graph)[mode['id']]
            self.assertEqual('docker' in mode, odometry != 'off')
            value = effective(self.graph(), release, mode['id'], check_artifacts=False)
            if odometry == 'off':
                self.assertIsNone(value['odometry'])
                self.assertFalse(value['nodes']['camera']['enable_imu'])
            else:
                camera = value['nodes']['camera']
                self.assertEqual(camera['combine_imu'], odometry == 'vio')
                self.assertTrue(camera['publish_stereo'])
                if family == 'd455':
                    self.assertEqual((camera['depth_width'], camera['depth_height']), (640, 480))
                    self.assertEqual(value['odometry']['config']['executor'], 'single')
                else:
                    self.assertEqual((camera['imu_rate_hz'], camera['mono_exposure_us'], camera['mono_iso']),
                                     (200 if odometry == 'vio' else 0, 20000, 800))
            self.assertIn(mode['id'], profile['recording']['overlays_by_mode'])

    def test_unsupported_camera_profile_has_only_off(self):
        graph, release = self.installed()
        self.site['camera_profiles']['d455'] = 'd455-60'
        self.save()
        choices = modes(self.graph())
        self.assertEqual(len(choices), 16)
        with self.assertRaises(ConfigurationError):
            effective(self.graph(), release, 'd455-camera-vio', check_artifacts=False)

    def test_d455_360p_off_keeps_native_depth_and_rejects_unsupported_rate(self):
        self.site['camera_profiles']['d455'] = 'd455-360p30'
        self.save()
        camera = effective(self.graph(), self.work / 'release', 'd455-camera', check_artifacts=False)['nodes']['camera']
        self.assertEqual((camera['width'], camera['height'], camera['depth_width'], camera['depth_height']),
                         (640, 360, 640, 480))
        self.assertFalse(camera.get('publish_stereo', False))
        from robot_deployment.configuration import validate_parameters
        with self.assertRaises(ConfigurationError):
            validate_parameters(dict(camera=dict(width=640, height=360, fps=35.),
                                     detector_cones={}, detector_coco={}, combined_overlay={}))

    def test_backend_and_camera_revision_mismatch_fail_preparation(self):
        graph, release = self.installed()
        manifest = release / 'visual-odometry/manifest.json'
        for key, replacement in (('backend', 'native'), ('camera_source_id', 'f'*40)):
            value = json.loads(manifest.read_text())
            previous = value[key]
            value[key] = replacement
            manifest.write_text(json.dumps(value))
            with self.assertRaises(ConfigurationError):
                effective(self.graph(), release, 'oak-camera-vio', check_artifacts=False)
            value[key] = previous
            manifest.write_text(json.dumps(value))

    def test_image_absence_fails_before_frozen_launch(self):
        graph, release = self.installed()
        with patch('robot_deployment.odometry.subprocess.check_output', side_effect=subprocess.TimeoutExpired('docker', 2)):
            with self.assertRaisesRegex(ValueError, 'unavailable'):
                effective(graph, release, 'd455-camera-vio')

    def test_frozen_odometry_input_matches_camera_and_survives_site_change(self):
        graph, release = self.installed()
        candidate = prepare(self.path, release, 'perception', 'revision', 'oak-camera-vio', root=self.root, check_artifacts=False)
        state = self.work / 'state'
        state.mkdir()
        reference = freeze(candidate, state, 'perception', 'revision', 'oak-camera-vio')
        self.site['visual_odometry']['backend'] = 'native'
        self.save()
        _, inputs = frozen(reference)
        effective_config = json.loads(inputs['effective'])
        odometry_config = json.loads(inputs['odometry'])
        self.assertEqual(effective_config['odometry']['config'], odometry_config)
        self.assertEqual(effective_config['odometry']['backend'], 'docker')
        self.assertEqual(odometry_config['frames']['left'], effective_config['nodes']['camera']['left_frame'])
