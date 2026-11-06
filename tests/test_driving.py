"""Testes da direção que não precisam do CARLA. Rodar com: python -m unittest discover tests"""
import math
import os
import socket
import tempfile
import threading
import unittest

import numpy as np

from carla_client.protocol import recv_message, send_message
from modules.driving.controller import SpeedController
from modules.driving.route import Route, RouteTracker, steering_to_point
from modules.driving.server import DrivingSession, LOST_TRAIL_STEPS, RunConfig
from modules.driving.steering import column_to_steering, estimate_steering

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
    def test_column_to_steering(self):
        self.assertAlmostEqual(column_to_steering(256, SIZE), 0.0)
        self.assertAlmostEqual(column_to_steering(512, SIZE), math.sin(math.radians(45)))
        self.assertAlmostEqual(column_to_steering(0, SIZE), -math.sin(math.radians(45)))

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

    def test_rows_follow_the_visible_trail(self):
        high = estimate_steering(trail_mask(256, top=260)).rows
        low = estimate_steering(trail_mask(256, top=360)).rows
        self.assertGreater(low[0], high[0])
        self.assertEqual(len(low), 3)


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

    def write(self, row, frame, region, estimate):
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


if __name__ == '__main__':
    unittest.main()
