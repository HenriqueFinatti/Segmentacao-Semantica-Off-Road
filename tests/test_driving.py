"""Testes da direção que não precisam do CARLA. Rodar com: python -m unittest discover tests"""
import os
import socket
import tempfile
import threading
import unittest

import cv2
import numpy as np

from carla_client.protocol import recv_message, send_message
from modules.driving.controller import SpeedController
from modules.driving.route import Route, RouteTracker, steering_to_point
from configs import paths
from modules.driving import recorder as recorder_module
from modules.driving.recorder import Recorder
from modules.driving.server import DrivingSession, LOST_TRAIL_STEPS, RunConfig, split_images
from modules.driving.steering import (
    CURVATURE_PER_STEER, LOOKAHEAD_DISTANCES, distance_to_mask_row, estimate_steering, lateral_offset, pursuit_steering,
)

SIZE = 512


def trail_mask(center, half_width=60, top=260):
    mask = np.zeros((SIZE, SIZE), dtype=np.uint8)
    mask[top:, center - half_width:center + half_width] = 1
    return mask


class ProtocolTest(unittest.TestCase):
    def test_round_trip_with_large_payload(self):
        left, right = socket.socketpair()
        payload = os.urandom(800 * 600 * 3)
        sender = threading.Thread(target=send_message, args=(left, {'type': 'step', 'speed': 1.5}, payload))
        sender.start()

        message, received = recv_message(right)
        sender.join()
        left.close()
        right.close()

        self.assertEqual(message, {'type': 'step', 'speed': 1.5})
        self.assertEqual(received, payload)

    def test_closed_connection_raises(self):
        left, right = socket.socketpair()
        left.close()

        with self.assertRaises(ConnectionError):
            recv_message(right)

        right.close()


class SteeringTest(unittest.TestCase):
    def test_ground_rows_get_closer_to_the_bottom(self):
        rows = [distance_to_mask_row(distance, SIZE) for distance in LOOKAHEAD_DISTANCES]
        self.assertEqual(rows, sorted(rows, reverse=True))
        self.assertTrue(all(0 <= row < SIZE for row in rows))

    def test_lateral_offset_on_the_ground(self):
        self.assertAlmostEqual(lateral_offset(256, SIZE, 7.0), 0.0)
        # Coluna 512 é a borda direita do frame de 800 px: 400 px do centro, ou 45° com foco de 400 px
        self.assertAlmostEqual(lateral_offset(512, SIZE, 7.0), 7.0)
        self.assertAlmostEqual(lateral_offset(0, SIZE, 7.0), -7.0)

    def test_pursuit_steering(self):
        self.assertEqual(pursuit_steering(10.0, 0.0), 0.0)
        # Ponto 1 m à direita a 7 m: arco de curvatura 2 * 1 / (49 + 1)
        self.assertAlmostEqual(pursuit_steering(7.0, 1.0), 0.04 / CURVATURE_PER_STEER)
        self.assertAlmostEqual(pursuit_steering(7.0, -1.0), -0.04 / CURVATURE_PER_STEER)

    def test_straight_trail_steers_zero(self):
        estimate = estimate_steering(trail_mask(256))
        self.assertEqual(len(estimate.columns), 3)
        self.assertAlmostEqual(estimate.steering, 0.0, delta=0.01)

    def test_trail_on_the_right_steers_right(self):
        self.assertGreater(estimate_steering(trail_mask(380)).steering, 0.2)

    def test_trail_on_the_left_steers_left(self):
        self.assertLess(estimate_steering(trail_mask(130)).steering, -0.2)

    def test_empty_mask_has_no_steering(self):
        estimate = estimate_steering(np.zeros((SIZE, SIZE), dtype=np.uint8))
        self.assertIsNone(estimate.steering)
        self.assertEqual(estimate.columns, [])

    def test_noise_is_not_a_trail(self):
        mask = np.zeros((SIZE, SIZE), dtype=np.uint8)
        mask[300:305, 100:105] = 1
        self.assertIsNone(estimate_steering(mask).steering)

    def test_separate_pond_is_ignored(self):
        mask = trail_mask(256)
        mask[280:320, 440:500] = 1
        self.assertAlmostEqual(estimate_steering(mask).steering, 0.0, delta=0.01)

    def test_uses_fixed_ground_rows(self):
        expected = [distance_to_mask_row(distance, SIZE) for distance in LOOKAHEAD_DISTANCES]
        self.assertEqual(estimate_steering(trail_mask(256)).rows, expected)

    def test_trail_seen_only_close_uses_the_rows_it_reaches(self):
        top = distance_to_mask_row(LOOKAHEAD_DISTANCES[1], SIZE) + 1
        estimate = estimate_steering(trail_mask(380, top=top))
        self.assertEqual(len(estimate.rows), 1)
        self.assertGreater(estimate.steering, 0)


class RouteTest(unittest.TestCase):
    def setUp(self):
        # Quadrado fechado de 40 m de lado, um ponto a cada 4 m
        side = np.arange(0, 40, 4)
        points = ([(x, 0) for x in side] + [(40, y) for y in side]
                  + [(40 - x, 40) for x in side] + [(0, 40 - y) for y in side])

        self.file = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False)
        self.file.write('middle.x,middle.y,middle.z,side1.x,side1.y,side1.z,side2.x,side2.y,side2.z\n')
        for x, y in points:
            self.file.write(f'{x * 100},{y * 100},100,{x * 100},{(y + 3) * 100},100,{x * 100},{(y - 3) * 100},100\n')
        self.file.close()
        self.route = Route(self.file.name)

    def tearDown(self):
        os.unlink(self.file.name)

    def test_units_and_length(self):
        self.assertAlmostEqual(self.route.length, 160.0)
        self.assertAlmostEqual(self.route.widths[0], 6.0)
        self.assertAlmostEqual(self.route.heights[0], 1.0)

    def test_steering_sign_matches_carla_axes(self):
        # No CARLA, com o carro olhando para +x, o eixo +y fica à direita
        self.assertGreater(steering_to_point((0, 0), 0, (10, 5)), 0)
        self.assertLess(steering_to_point((0, 0), 0, (10, -5)), 0)
        self.assertAlmostEqual(steering_to_point((0, 0), 0, (10, 0)), 0.0)
        self.assertAlmostEqual(steering_to_point((0, 0), 90, (0, 10)), 0.0)

    def test_lap_is_counted_only_after_going_around(self):
        tracker = RouteTracker(self.route)
        states = [tracker.update(tuple(self.route.waypoint(i)), 0) for i in range(self.route.size)]
        self.assertFalse(states[10].lap_done)
        self.assertAlmostEqual(states[-1].mileage, 156.0)
        self.assertTrue(states[-1].lap_done)

    def test_lateral_offset_sign_matches_carla_axes(self):
        # Primeiro lado do quadrado vai para +x: +y fica à direita
        self.assertAlmostEqual(self.route.lateral_offset(2, (8.0, 1.5)), 1.5)
        self.assertAlmostEqual(self.route.lateral_offset(2, (8.0, -2.0)), -2.0)
        self.assertAlmostEqual(self.route.lateral_offset(2, (8.0, 0.0)), 0.0)

    def test_going_backwards_adds_no_distance(self):
        tracker = RouteTracker(self.route)
        tracker.update(tuple(self.route.waypoint(10)), 0)
        self.assertEqual(tracker.update(tuple(self.route.waypoint(5)), 0).mileage, 0.0)


class ControllerTest(unittest.TestCase):
    def test_launch_then_holds_range(self):
        controller = SpeedController(1, 2)
        for _ in range(SpeedController.LAUNCH_STEPS):
            self.assertEqual(controller.update(0, 0), (1.0, 0.0))

        before = controller.throttle
        controller.update(0.5, 0)
        self.assertGreater(controller.throttle, before)

        before = controller.throttle
        _, brake = controller.update(3.0, 0)
        self.assertLess(controller.throttle, before)
        self.assertGreater(brake, 0)

    def test_outputs_stay_in_carla_range(self):
        controller = SpeedController(1, 2)
        for _ in range(5000):
            throttle, brake = controller.update(0, 0)
        self.assertEqual(throttle, 1.0)

        for _ in range(5000):
            throttle, brake = controller.update(50, 0.5)
        self.assertEqual(throttle, 0.0)
        self.assertEqual(brake, 1.0)


class FakePredictor:
    def __init__(self):
        self.mask = trail_mask(256)

    def predict(self, frame):
        return self.mask


class FakeRecorder:
    def __init__(self):
        self.rows = []

    def write(self, row, frame, mask, estimate, view=None):
        self.rows.append(row)


class SessionTest(unittest.TestCase):
    def setUp(self):
        side = np.arange(0, 100, 4)
        points = [(x, 0) for x in side] + [(100, y) for y in side] + [(100 - x, 100) for x in side] + [(0, 100 - y) for y in side]

        self.file = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False)
        self.file.write('middle.x,middle.y,middle.z,side1.x,side1.y,side1.z,side2.x,side2.y,side2.z\n')
        for x, y in points:
            self.file.write(f'{x * 100},{y * 100},0,{x * 100},{(y + 3) * 100},0,{x * 100},{(y - 3) * 100},0\n')
        self.file.close()

        self.recorder = FakeRecorder()
        self.predictor = FakePredictor()
        self.route = Route(self.file.name)
        self.session = self.new_session('waypoint')
        self.frame = np.zeros((600, 800, 3), dtype=np.uint8)

    def tearDown(self):
        os.unlink(self.file.name)

    def new_session(self, mode):
        return DrivingSession(RunConfig(mode=mode), self.predictor, self.route, self.recorder)

    def state(self, x=0.0, y=0.0, speed=1.5, collision=0.0):
        return {'frame': 1, 'x': x, 'y': y, 'z': 0.0, 'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0,
                'speed': speed, 'collision': collision}

    def test_route_steers_and_camera_is_only_logged(self):
        action = self.session.process(self.state(), self.frame)
        row = self.recorder.rows[0]
        self.assertFalse(action['done'])
        self.assertEqual(action['steer'], row['route_steering'])
        self.assertAlmostEqual(row['camera_steering'], 0.0, delta=0.01)

    def test_mask_mode_steers_with_the_camera(self):
        session = self.new_session('mask')
        self.predictor.mask = trail_mask(380)

        action = session.process(self.state(), self.frame)
        row = self.recorder.rows[0]

        self.assertGreater(action['steer'], 0.2)
        self.assertEqual(action['steer'], row['camera_steering'])
        self.assertNotEqual(action['steer'], row['route_steering'])

    def test_lost_trail_keeps_steering_then_stops(self):
        session = self.new_session('mask')
        self.predictor.mask = trail_mask(380)
        kept = session.process(self.state(), self.frame)['steer']

        self.predictor.mask = np.zeros((SIZE, SIZE), dtype=np.uint8)
        for _ in range(LOST_TRAIL_STEPS):
            action = session.process(self.state(), self.frame)
            self.assertEqual(action['steer'], kept)
            self.assertFalse(action['done'])

        braking = session.process(self.state(speed=1.0), self.frame)
        self.assertEqual((braking['throttle'], braking['brake']), (0.0, 1.0))
        self.assertFalse(braking['done'])

        self.assertEqual(session.process(self.state(speed=0.0), self.frame)['reason'], 'trail_lost')

    def test_trail_coming_back_resumes_driving(self):
        session = self.new_session('mask')
        self.predictor.mask = np.zeros((SIZE, SIZE), dtype=np.uint8)
        for _ in range(LOST_TRAIL_STEPS + 3):
            session.process(self.state(), self.frame)

        self.predictor.mask = trail_mask(256)
        action = session.process(self.state(), self.frame)
        self.assertGreater(action['throttle'], 0.0)
        self.assertEqual(session.lost_steps, 0)

    def test_collision_ends_the_run(self):
        self.assertEqual(self.session.process(self.state(collision=100.0), self.frame)['reason'], 'collision')

    def test_leaving_the_track_ends_the_run(self):
        self.assertEqual(self.session.process(self.state(x=20.0, y=8.0), self.frame)['reason'], 'off_track')

    def test_stopped_car_ends_the_run(self):
        reasons = [self.session.process(self.state(speed=0.0), self.frame)['reason'] for _ in range(50)]
        self.assertEqual(reasons[39], None)
        self.assertEqual(reasons[40], 'stalled')


class RecorderVideoTest(unittest.TestCase):
    """Usa o Recorder de verdade numa pasta temporária."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.original_dir = paths.CARLA_RESULTS_DIR
        paths.CARLA_RESULTS_DIR = self.folder.name

        side = np.arange(0, 100, 4)
        points = [(x, 0) for x in side] + [(100, y) for y in side] + [(100 - x, 100) for x in side] + [(0, 100 - y) for y in side]
        self.file = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False)
        self.file.write('middle.x,middle.y,middle.z,side1.x,side1.y,side1.z,side2.x,side2.y,side2.z\n')
        for x, y in points:
            self.file.write(f'{x * 100},{y * 100},0,{x * 100},{(y + 3) * 100},0,{x * 100},{(y - 3) * 100},0\n')
        self.file.close()

    def tearDown(self):
        paths.CARLA_RESULTS_DIR = self.original_dir
        os.unlink(self.file.name)
        self.folder.cleanup()

    def drive(self, with_view, steps=4, **options):
        config = RunConfig(mode='mask', **options)
        recorder = Recorder(config)
        session = DrivingSession(config, FakePredictor(), Route(self.file.name), recorder)
        frame = np.zeros((600, 800, 3), dtype=np.uint8)
        view = np.full((600, 800, 3), 80, dtype=np.uint8) if with_view else None

        for step in range(steps):
            state = {'frame': step, 'x': 4.0 * step, 'y': 0.0, 'z': 0.0, 'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0,
                     'speed': 1.5, 'collision': 0.0}
            session.process(state, frame, view)

        recorder.close('lap_complete', 0.0)
        return recorder.run_dir

    def video(self, run_dir, name):
        capture = cv2.VideoCapture(os.path.join(run_dir, name))
        size = (int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        ok, first = capture.read()
        capture.release()
        return size, frames, first

    def test_all_four_videos_with_the_carla_view(self):
        run_dir = self.drive(with_view=True)
        expected = {
            'overlay.mp4': (800, 416),
            'mascara.mp4': (800, 416),
            'carla.mp4': (800, 600),
            'comparacao.mp4': (recorder_module.COMBINED_VIEW_SIZE[0] + 800, 832),
        }
        for name, size in expected.items():
            got_size, frames, _ = self.video(run_dir, name)
            self.assertEqual(got_size, size, name)
            self.assertEqual(frames, 4, name)

    def test_without_the_carla_view_there_is_no_carla_video(self):
        run_dir = self.drive(with_view=False)
        self.assertFalse(os.path.exists(os.path.join(run_dir, 'carla.mp4')))
        self.assertEqual(self.video(run_dir, 'comparacao.mp4')[0], (800, 832))
        self.assertEqual(self.video(run_dir, 'mascara.mp4')[1], 4)

    def frame_rate(self, run_dir, name):
        capture = cv2.VideoCapture(os.path.join(run_dir, name))
        fps = capture.get(cv2.CAP_PROP_FPS)
        capture.release()
        return fps

    def test_videos_play_twice_as_fast_by_default(self):
        run_dir = self.drive(with_view=True)
        for name in ('overlay.mp4', 'mascara.mp4', 'carla.mp4', 'comparacao.mp4'):
            self.assertAlmostEqual(self.frame_rate(run_dir, name), 20.0, places=1)

    def test_video_speed_one_keeps_the_real_speed(self):
        run_dir = self.drive(with_view=False, video_speed=1.0)
        self.assertAlmostEqual(self.frame_rate(run_dir, 'overlay.mp4'), 10.0, places=1)

    def test_mask_video_is_the_raw_model_output(self):
        run_dir = self.drive(with_view=False, steps=1)
        _, _, first = self.video(run_dir, 'mascara.mp4')
        gray = first.mean(axis=2)
        # A FakePredictor marca trilha nas colunas 196-315 de 512, da linha 260 para baixo
        self.assertGreater(gray[400, 400], 200)
        self.assertLess(gray[400, 50], 50)
        self.assertLess(gray[50, 400], 50)


class SplitImagesTest(unittest.TestCase):
    def test_one_image(self):
        frame, view = split_images(bytes(800 * 600 * 3))
        self.assertEqual(frame.shape, (600, 800, 3))
        self.assertIsNone(view)

    def test_two_images(self):
        payload = bytes(800 * 600 * 3) + bytes([7]) * (800 * 600 * 3)
        frame, view = split_images(payload)
        self.assertEqual(frame.max(), 0)
        self.assertEqual(view.shape, (600, 800, 3))
        self.assertEqual(view.min(), 7)


if __name__ == '__main__':
    unittest.main()
