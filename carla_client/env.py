import glob
import math
import os
import queue
import sys

import numpy as np

EGG_DIR = os.environ.get('CARLA_EGG_DIR', '/carla/dist')

try:
    sys.path.append(glob.glob(os.path.join(EGG_DIR, 'carla-0.9.6-py3.6-*.egg'))[0])
except IndexError:
    raise RuntimeError('Biblioteca do CARLA não encontrada em ' + EGG_DIR)

import carla

CAMERA_X = 2.0
CAMERA_Z = 1.7
SETTLE_TICKS = 30

# Janela do CARLA: atrás e acima do carro. Só serve para acompanhar, não afeta o modelo
SPECTATOR_DISTANCE = 8.0
SPECTATOR_HEIGHT = 4.0
SPECTATOR_PITCH = -15.0
TIMEOUT = 60.0


class CarlaEnv:
    """Liga-se ao CARLA em modo síncrono: cada tick devolve um frame e o estado do carro."""

    def __init__(self, host, port):
        self.client = carla.Client(host, port)
        self.client.set_timeout(TIMEOUT)
        self.world = None
        self.original_settings = None
        self.vehicle = None
        self.camera = None
        self.collision_sensor = None
        self.images = queue.Queue()
        self.collision = 0.0


    def start(self, map_name, weather, spawn, fps):
        # Mapas customizados não têm OpenDRIVE: não usar world.get_map()
        self.world = self.client.load_world(map_name)
        self.world.set_weather(getattr(carla.WeatherParameters, weather))

        self.original_settings = self.world.get_settings()
        self.world.apply_settings(carla.WorldSettings(
            no_rendering_mode=False,
            synchronous_mode=True,
            fixed_delta_seconds=1.0 / fps,
        ))

        library = self.world.get_blueprint_library()
        pose = carla.Transform(
            carla.Location(x=spawn['x'], y=spawn['y'], z=spawn['z']),
            carla.Rotation(yaw=spawn['yaw']),
        )

        self.vehicle = self.world.spawn_actor(library.filter('vehicle.nissan.patrol')[0], pose)
        self.camera = self.world.spawn_actor(
            library.find('sensor.camera.rgb'),
            carla.Transform(carla.Location(x=CAMERA_X, z=CAMERA_Z)),
            attach_to=self.vehicle,
        )
        self.collision_sensor = self.world.spawn_actor(
            library.find('sensor.other.collision'),
            carla.Transform(),
            attach_to=self.vehicle,
        )

        self.camera.listen(self.images.put)
        self.collision_sensor.listen(self.on_collision)
        self.settle()


    def settle(self):
        # O carro nasce acima do chão: espera assentar antes de começar a contar colisões
        self.vehicle.apply_control(carla.VehicleControl(hand_brake=True))

        for _ in range(SETTLE_TICKS):
            self.world.tick()

        self.collision = 0.0


    def on_collision(self, event):
        impulse = event.normal_impulse
        self.collision += math.sqrt(impulse.x ** 2 + impulse.y ** 2 + impulse.z ** 2)


    def tick(self):
        frame_id = self.world.tick()
        image = self.wait_image(frame_id)

        transform = self.vehicle.get_transform()
        velocity = self.vehicle.get_velocity()
        self.follow_with_spectator(transform)

        state = {
            'type': 'step',
            'frame': frame_id,
            'x': transform.location.x,
            'y': transform.location.y,
            'z': transform.location.z,
            'yaw': transform.rotation.yaw,
            'pitch': transform.rotation.pitch,
            'roll': transform.rotation.roll,
            'speed': math.sqrt(velocity.x ** 2 + velocity.y ** 2 + velocity.z ** 2),
            'collision': self.collision,
        }

        return state, self.to_rgb(image)


    def follow_with_spectator(self, transform):
        yaw = math.radians(transform.rotation.yaw)
        location = carla.Location(
            x=transform.location.x - SPECTATOR_DISTANCE * math.cos(yaw),
            y=transform.location.y - SPECTATOR_DISTANCE * math.sin(yaw),
            z=transform.location.z + SPECTATOR_HEIGHT,
        )
        rotation = carla.Rotation(pitch=SPECTATOR_PITCH, yaw=transform.rotation.yaw)
        self.world.get_spectator().set_transform(carla.Transform(location, rotation))


    def wait_image(self, frame_id):
        while True:
            image = self.images.get(timeout=TIMEOUT)
            if image.frame == frame_id:
                return image


    def to_rgb(self, image):
        bgra = np.frombuffer(image.raw_data, dtype=np.uint8).reshape(image.height, image.width, 4)
        return bgra[:, :, [2, 1, 0]].tobytes()


    def apply(self, action):
        self.vehicle.apply_control(carla.VehicleControl(
            throttle=action['throttle'],
            steer=action['steer'],
            brake=action['brake'],
        ))


    def close(self):
        try:
            for sensor in (self.camera, self.collision_sensor):
                if sensor is not None:
                    sensor.stop()
                    sensor.destroy()

            if self.vehicle is not None:
                self.vehicle.destroy()

            # Sem isto o servidor do CARLA fica parado esperando ticks
            if self.original_settings is not None:
                self.world.apply_settings(self.original_settings)
        except RuntimeError as error:
            # Se o CARLA caiu, não há mais o que limpar nele
            print('CARLA indisponível ao encerrar:', error, flush=True)
