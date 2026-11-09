import math
from collections import namedtuple

import cv2
import numpy as np

from carla_client.protocol import FRAME_HEIGHT, FRAME_WIDTH

# Faixa do frame com a mesma proporção das imagens de treino e o horizonte no centro
CROP_TOP = 92
CROP_BOTTOM = 508

# Câmera de 90° e 800 px de largura: distância focal de 400 px.
# Ela fica 2 m à frente do centro do carro, a 1,7 m de altura e sem inclinação
FOCAL_LENGTH = FRAME_WIDTH / 2
HORIZON_ROW = FRAME_HEIGHT / 2
CAMERA_HEIGHT = 1.7
CAMERA_FORWARD = 2.0

# Distâncias à frente da câmera, em metros, onde a trilha é lida. Mais longe que isso
# o carro mira no trecho depois da curva e corta por dentro
LOOKAHEAD_DISTANCES = (5.0, 7.0, 9.0)

# Medido no Nissan Patrol: curvatura (1/m) que o carro faz por unidade de direção do CARLA
CURVATURE_PER_STEER = 0.267

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


def distance_to_mask_row(distance, mask_height):
    """Linha da máscara onde fica o chão a esta distância, supondo chão plano."""
    frame_row = HORIZON_ROW + CAMERA_HEIGHT * FOCAL_LENGTH / distance
    return int(round((frame_row - CROP_TOP) * mask_height / (CROP_BOTTOM - CROP_TOP)))


def lateral_offset(column, mask_width, distance):
    """Distância lateral em metros, no chão, de uma coluna da máscara. Positivo é à direita."""
    u = column * FRAME_WIDTH / mask_width
    return (u - FRAME_WIDTH / 2) * distance / FOCAL_LENGTH


def pursuit_steering(forward, lateral):
    """Pure pursuit: curvatura do arco que leva o centro do carro até o ponto, convertida em direção do CARLA."""
    curvature = 2 * lateral / (forward ** 2 + lateral ** 2)
    return curvature / CURVATURE_PER_STEER


def estimate_steering(mask):
    region = largest_region(mask)
    height, width = region.shape
    rows = []
    columns = []
    values = []

    for distance in LOOKAHEAD_DISTANCES:
        row = distance_to_mask_row(distance, height)
        if not 0 <= row < height:
            continue

        pixels = np.flatnonzero(region[row])
        if pixels.size == 0:
            continue

        column = float(pixels.mean())
        rows.append(row)
        columns.append(column)
        values.append(pursuit_steering(distance + CAMERA_FORWARD, lateral_offset(column, width, distance)))

    if not values:
        return SteeringEstimate(None, rows, columns, region)

    return SteeringEstimate(sum(values) / len(values), rows, columns, region)
