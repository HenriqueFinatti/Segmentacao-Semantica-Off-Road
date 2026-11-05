import csv
import math
from collections import namedtuple

import numpy as np

RouteState = namedtuple('RouteState', 'index steering mileage distance_from_center track_width lap_done')

# Mesmos waypoints que o mathDriver usa: do 2º ao 4º à frente, cerca de 8 a 16 m no Offroad_2
STEERING_WAYPOINTS = (2, 3, 4)

# Margem somada à largura da trilha para considerar que o carro saiu, como no benchmark original
OFF_TRACK_MARGIN = 4

# Evita que o fim da volta dependa de passar exatamente pelo último waypoint
LAP_END_TOLERANCE = 5


def steering_to_point(location, heading, target):
    """Seno do ângulo até o alvo no referencial do carro. Positivo é para a direita."""
    direction = np.asarray(target) - np.asarray(location)
    direction = direction / np.hypot(*direction)
    radians = math.radians(heading)
    return float(-direction[0] * math.sin(radians) + direction[1] * math.cos(radians))


class Route:
    def __init__(self, csv_path):
        with open(csv_path, newline='', encoding='utf-8') as file:
            rows = list(csv.DictReader(file))

        # O CSV está em centímetros
        self.points = np.array([[float(r['middle.x']), float(r['middle.y'])] for r in rows]) / 100
        self.heights = np.array([float(r['middle.z']) for r in rows]) / 100

        side1 = np.array([[float(r['side1.x']), float(r['side1.y'])] for r in rows]) / 100
        side2 = np.array([[float(r['side2.x']), float(r['side2.y'])] for r in rows]) / 100
        self.widths = np.hypot(*(side1 - side2).T)

        following = np.roll(self.points, -1, axis=0)
        self.segments = np.hypot(*(following - self.points).T)
        self.length = float(self.segments.sum())
        self.size = len(self.points)


    def nearest(self, location):
        return int(np.argmin(np.sum((self.points - np.asarray(location)) ** 2, axis=1)))


    def waypoint(self, index):
        return self.points[index % self.size]


    def heading_at(self, index):
        direction = self.waypoint(index + 2) - self.waypoint(index)
        return math.degrees(math.atan2(direction[1], direction[0]))


    def spawn_pose(self, index, height_offset=1.0):
        x, y = self.waypoint(index)
        z = self.heights[index % self.size] + height_offset
        return {'x': float(x), 'y': float(y), 'z': float(z), 'yaw': self.heading_at(index)}


    def steering(self, index, location, heading):
        values = [steering_to_point(location, heading, self.waypoint(index + step)) for step in STEERING_WAYPOINTS]
        return sum(values) / len(values)


class RouteTracker:
    def __init__(self, route):
        self.route = route
        self.index = None
        self.mileage = 0.0


    def update(self, location, heading):
        route = self.route
        index = route.nearest(location)

        if self.index is not None:
            forward = (index - self.index) % route.size
            if 0 < forward < route.size // 2:
                self.mileage += float(sum(route.segments[(self.index + i) % route.size] for i in range(forward)))

        self.index = index

        # Distância até o waypoint mais próximo, a mesma medida usada no benchmark original
        distance = float(np.hypot(*(np.asarray(location) - route.waypoint(index))))

        return RouteState(
            index=index,
            steering=route.steering(index, location, heading),
            mileage=self.mileage,
            distance_from_center=distance,
            track_width=float(route.widths[index]),
            lap_done=self.mileage >= route.length - LAP_END_TOLERANCE,
        )
