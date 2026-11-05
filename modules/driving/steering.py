import math
from collections import namedtuple

import cv2
import numpy as np

from carla_client.protocol import FRAME_WIDTH

# Faixa do frame com a mesma proporção das imagens de treino e o horizonte no centro
CROP_TOP = 92
CROP_BOTTOM = 508

# Câmera de 90° e 800 px de largura: distância focal de 400 px
FOCAL_LENGTH = FRAME_WIDTH / 2

# Posição de cada linha entre o topo visível da trilha e a base da máscara
ROW_FRACTIONS = (0.21, 0.33, 0.41)

# Abaixo disto a região é ruído, não trilha
MIN_REGION_PIXELS = 200

SteeringEstimate = namedtuple('SteeringEstimate', 'steering rows columns region')


def crop_frame(frame):
    return frame[CROP_TOP:CROP_BOTTOM]


def largest_region(mask):
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)

    if count <= 1:
        return np.zeros(mask.shape, dtype=bool)

    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))

    if stats[largest, cv2.CC_STAT_AREA] < MIN_REGION_PIXELS:
        return np.zeros(mask.shape, dtype=bool)

    return labels == largest


def steering_rows(region):
    filled = np.flatnonzero(region.any(axis=1))

    if filled.size == 0:
        return []

    top = int(filled[0])
    height = region.shape[0] - top
    return [top + int(round(fraction * height)) for fraction in ROW_FRACTIONS]


def column_to_steering(column, mask_width):
    """Com a câmera sem inclinação, a direção de um ponto depende só da coluna, não da distância."""
    u = column * FRAME_WIDTH / mask_width
    return math.sin(math.atan2(u - FRAME_WIDTH / 2, FOCAL_LENGTH))


def estimate_steering(mask):
    region = largest_region(mask)
    rows = []
    columns = []

    for row in steering_rows(region):
        pixels = np.flatnonzero(region[row])
        if pixels.size:
            rows.append(row)
            columns.append(float(pixels.mean()))

    if not columns:
        return SteeringEstimate(None, rows, columns, region)

    values = [column_to_steering(column, mask.shape[1]) for column in columns]
    return SteeringEstimate(sum(values) / len(values), rows, columns, region)
