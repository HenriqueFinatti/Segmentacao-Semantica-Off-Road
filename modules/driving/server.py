import argparse
import os
import socket
import time
from dataclasses import dataclass

import numpy as np
import torch

from carla_client.protocol import FRAME_HEIGHT, FRAME_WIDTH, SERVER_HOST, SERVER_PORT, recv_message, send_message
from configs import paths
from modules.driving.controller import SpeedController
from modules.driving.recorder import Recorder
from modules.driving.route import OFF_TRACK_MARGIN, Route, RouteTracker
from modules.driving.steering import crop_frame, estimate_steering
from modules.segmentation.predictor import Predictor
from configs.settings import Settings

# Regra do benchmark original: abaixo de 1 km/h por mais de 20 passos, depois do passo 40
STALL_SPEED = 1.0 / 3.6
STALL_STEPS = 20
STALL_MIN_STEP = 40

# Modos: em 'waypoint' a rota dirige e a câmera só é registrada; em 'mask' a câmera dirige e a rota só pontua
MODES = ('waypoint', 'mask')

# Sem trilha na máscara, mantém a última direção por 1 s (a 10 Hz) e depois freia até parar
LOST_TRAIL_STEPS = 10


@dataclass
class RunConfig:
    map_name: str = 'Offroad_2'
    weather: str = 'ClearNoon'
    mode: str = 'waypoint'
    model: str = 'deeplabv3+'
    min_speed: float = 1.0
    max_speed: float = 2.0
    spawn_index: int = 0
    max_steps: int = 20000
    fps: int = 10
    record_view: bool = True
    # 1 toca na velocidade real do carro; 2 toca duas vezes mais rápido
    video_speed: float = 2.0


class DrivingSession:
    """Decide a ação de cada passo. Não conhece rede nem CARLA, para poder ser testada com frames salvos."""

    def __init__(self, config, predictor, route, recorder):
        self.config = config
        self.predictor = predictor
        self.route = route
        self.tracker = RouteTracker(route)
        self.controller = SpeedController(config.min_speed, config.max_speed)
        self.recorder = recorder
        self.step_count = 0
        self.slow_steps = 0
        self.lost_steps = 0
        self.last_steering = 0.0


    def process(self, state, frame, view=None):
        self.step_count += 1

        started = time.perf_counter()
        mask = self.predictor.predict(crop_frame(frame))
        inference_ms = (time.perf_counter() - started) * 1000

        estimate = estimate_steering(mask)
        route_state = self.tracker.update((state['x'], state['y']), state['yaw'])

        steering = self.choose_steering(route_state, estimate)
        throttle, brake = self.controller.update(state['speed'], steering)

        if self.lost_steps > LOST_TRAIL_STEPS:
            throttle, brake = 0.0, 1.0

        reason = self.finish_reason(state, route_state)

        self.recorder.write({
            'step': self.step_count,
            'frame': state['frame'],
            'x': state['x'],
            'y': state['y'],
            'z': state['z'],
            'yaw': state['yaw'],
            'pitch': state['pitch'],
            'roll': state['roll'],
            'speed': state['speed'],
            'waypoint': route_state.index,
            'mileage': route_state.mileage,
            'distance_from_center': route_state.distance_from_center,
            'lateral_offset': route_state.lateral_offset,
            'track_width': route_state.track_width,
            'route_steering': route_state.steering,
            'camera_steering': '' if estimate.steering is None else estimate.steering,
            'rows_found': len(estimate.columns),
            'applied_steering': steering,
            'throttle': throttle,
            'brake': brake,
            'trail_fraction': float(mask.mean()),
            'inference_ms': inference_ms,
            'collision': state['collision'],
        }, frame, mask, estimate, view)

        return {'throttle': throttle, 'steer': steering, 'brake': brake, 'done': reason is not None, 'reason': reason}


    def choose_steering(self, route_state, estimate):
        if self.config.mode == 'waypoint':
            return max(min(route_state.steering, 1.0), -1.0)

        if estimate.steering is None:
            self.lost_steps += 1
            return self.last_steering

        self.lost_steps = 0
        self.last_steering = max(min(estimate.steering, 1.0), -1.0)
        return self.last_steering


    def finish_reason(self, state, route_state):
        if route_state.lap_done:
            return 'lap_complete'

        if self.lost_steps > LOST_TRAIL_STEPS and state['speed'] <= STALL_SPEED:
            return 'trail_lost'

        if state['collision'] > 0:
            return 'collision'

        if route_state.distance_from_center > (route_state.track_width + OFF_TRACK_MARGIN) / 2:
            return 'off_track'

        if state['speed'] <= STALL_SPEED:
            self.slow_steps += 1

        if self.slow_steps > STALL_STEPS and self.step_count > STALL_MIN_STEP:
            return 'stalled'

        if self.step_count >= self.config.max_steps:
            return 'max_steps'

        return None


class DrivingServer:
    def __init__(self, config, settings):
        self.config = config
        self.route = Route(os.path.join(paths.CARLA_CONFIG_DIR, f'{config.map_name}.csv'))
        self.predictor = Predictor(config.model, settings.get_image_size())

        image_size = self.predictor.image_size
        self.predictor.warmup(torch.zeros(3, image_size, image_size))


    def serve(self):
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((SERVER_HOST, SERVER_PORT))
            listener.listen(1)

            print(f'Servidor pronto em {SERVER_HOST}:{SERVER_PORT}. Aguardando o cliente do CARLA...', flush=True)
            connection, _ = listener.accept()

        with connection:
            connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            return self.run_episode(connection)


    def run_episode(self, connection):
        hello, _ = recv_message(connection)

        if hello.get('type') != 'hello':
            raise ValueError(f'Mensagem inesperada do cliente: {hello}')

        send_message(connection, {
            'type': 'config',
            'map': self.config.map_name,
            'weather': self.config.weather,
            'fps': self.config.fps,
            'spawn': self.route.spawn_pose(self.config.spawn_index),
            'record_view': self.config.record_view,
        })

        recorder = Recorder(self.config)
        session = DrivingSession(self.config, self.predictor, self.route, recorder)
        reason = 'client_disconnected'

        try:
            while True:
                state, payload = recv_message(connection)
                frame, view = split_images(payload)

                action = session.process(state, frame, view)
                send_message(connection, dict(action, type='action'))

                if action['done']:
                    reason = action['reason']
                    break
        except (ConnectionError, OSError) as error:
            print(f'Conexão perdida: {error}')
        finally:
            summary = recorder.close(reason, self.route.length)

        print(f'Fim da execução: {reason}')
        print(f'Resultados em: {paths.relative(recorder.run_dir)}')
        return summary


def split_images(payload):
    """A primeira imagem é a câmera do modelo; a segunda, se veio, é a visão de trás do carro."""
    size = FRAME_HEIGHT * FRAME_WIDTH * 3
    images = np.frombuffer(payload, dtype=np.uint8)
    frame = images[:size].reshape(FRAME_HEIGHT, FRAME_WIDTH, 3)
    view = images[size:2 * size].reshape(FRAME_HEIGHT, FRAME_WIDTH, 3) if images.size >= 2 * size else None
    return frame, view


def parse_args():
    defaults = RunConfig()
    parser = argparse.ArgumentParser(description='Servidor de direção para o CARLA')
    parser.add_argument('--weather', default=defaults.weather)
    parser.add_argument('--mode', choices=MODES, default=defaults.mode)
    parser.add_argument('--min-speed', type=float, default=defaults.min_speed)
    parser.add_argument('--max-speed', type=float, default=defaults.max_speed)
    parser.add_argument('--spawn-index', type=int, default=defaults.spawn_index)
    parser.add_argument('--max-steps', type=int, default=defaults.max_steps)
    parser.add_argument('--no-view-video', action='store_true', help='Não grava a visão de trás do carro (carla.mp4)')
    parser.add_argument('--video-speed', type=float, default=defaults.video_speed,
                        help='Velocidade dos vídeos: 1 é a velocidade real do carro, 2 é o dobro')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    DrivingServer(RunConfig(
        weather=args.weather,
        mode=args.mode,
        min_speed=args.min_speed,
        max_speed=args.max_speed,
        spawn_index=args.spawn_index,
        max_steps=args.max_steps,
        record_view=not args.no_view_video,
        video_speed=args.video_speed,
    ), Settings()).serve()
