import csv
import json
import os
from datetime import datetime

import cv2
import numpy as np

from carla_client.protocol import FRAME_HEIGHT, FRAME_WIDTH
from configs import paths
from modules.driving.steering import CROP_BOTTOM, CROP_TOP
from modules.metrics.inference_metrics import InferenceMetrics

COLUMNS = [
    'step', 'frame', 'x', 'y', 'z', 'yaw', 'pitch', 'roll', 'speed', 'waypoint', 'mileage',
    'distance_from_center', 'lateral_offset', 'track_width', 'route_steering', 'camera_steering', 'rows_found',
    'applied_steering', 'throttle', 'brake', 'trail_fraction', 'inference_ms', 'collision',
]

VIDEO_CODEC = cv2.VideoWriter_fourcc(*'mp4v')

# No vídeo de comparação, a visão do CARLA (4:3) ocupa a altura dos dois painéis de 800x416 empilhados.
# A largura é arredondada para número par, que os codificadores de vídeo exigem
CROP_SIZE = (FRAME_WIDTH, CROP_BOTTOM - CROP_TOP)
COMBINED_VIEW_SIZE = (2 * round(FRAME_WIDTH * CROP_SIZE[1] / FRAME_HEIGHT), 2 * CROP_SIZE[1])

# Metade da largura do Nissan Patrol: acima disto de deslocamento, uma roda já passou da borda
CAR_HALF_WIDTH = 1.0
TRAIL_COLOR = np.array([0, 0, 255], dtype=np.uint8)
TRAIL_ALPHA = 0.45


class Recorder:
    """Guarda em results/carla/<execução>: log.csv, frames/, summary.json e os vídeos.

    overlay.mp4     o que o modelo vê, com a trilha usada em vermelho e os pontos de direção em amarelo
    mascara.mp4     a saída do modelo em preto e branco, antes de qualquer filtro
    carla.mp4       a visão de trás do carro, quando o cliente envia a segunda câmera
    comparacao.mp4  os vídeos acima lado a lado

    Todos têm um quadro por passo, então ficam sincronizados. config.video_speed acelera todos igualmente.
    """

    def __init__(self, config, save_every=10):
        name = f"{datetime.now():%Y-%m-%d_%H-%M-%S}_{config.map_name}_{config.weather}_{config.mode}"
        self.run_dir = os.path.join(paths.CARLA_RESULTS_DIR, name)
        self.frames_dir = os.path.join(self.run_dir, 'frames')
        os.makedirs(self.frames_dir)

        self.config = config
        self.save_every = save_every
        self.rows = []

        self.log_file = open(os.path.join(self.run_dir, 'log.csv'), 'w', newline='', encoding='utf-8')
        self.log = csv.DictWriter(self.log_file, fieldnames=COLUMNS)
        self.log.writeheader()

        # Cada vídeo é criado no primeiro quadro, pelo tamanho da imagem
        self.videos = {}


    def write(self, row, frame, mask, estimate, view=None):
        self.rows.append(row)
        self.log.writerow(row)

        bgr = frame[:, :, ::-1].copy()

        if row['step'] % self.save_every == 0:
            cv2.imwrite(os.path.join(self.frames_dir, f"{row['step']:06d}.jpg"), bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])

        overlay = self.build_overlay(bgr, estimate.region, estimate, row)
        mask_image = self.build_mask_image(mask)
        view_bgr = None if view is None else view[:, :, ::-1].copy()

        self.write_video('overlay.mp4', overlay)
        self.write_video('mascara.mp4', mask_image)

        if view_bgr is not None:
            self.write_video('carla.mp4', view_bgr)

        self.write_video('comparacao.mp4', self.build_comparison(overlay, mask_image, view_bgr))


    def write_video(self, name, image):
        if name not in self.videos:
            height, width = image.shape[:2]
            # Um quadro por passo: com config.fps quadros por segundo, o vídeo toca na velocidade real do carro
            fps = self.config.fps * self.config.video_speed
            writer = cv2.VideoWriter(os.path.join(self.run_dir, name), VIDEO_CODEC, fps, (width, height))

            if not writer.isOpened():
                raise RuntimeError(f'Não foi possível criar o vídeo {name}')

            self.videos[name] = writer

        self.videos[name].write(image)


    def build_mask_image(self, mask):
        # A máscara crua do modelo, 512x512, volta para a proporção do recorte
        white = cv2.resize(mask.astype(np.uint8) * 255, CROP_SIZE, interpolation=cv2.INTER_NEAREST)
        return cv2.cvtColor(white, cv2.COLOR_GRAY2BGR)


    def build_comparison(self, overlay, mask_image, view_bgr):
        panels = np.vstack([self.label(overlay, 'Overlay'), self.label(mask_image, 'Mascara do modelo')])

        if view_bgr is None:
            return panels

        view = self.label(cv2.resize(view_bgr, COMBINED_VIEW_SIZE), 'CARLA')
        return np.hstack([view, panels])


    def label(self, image, text):
        # Fontes do OpenCV não suportam acentos
        labeled = image.copy()
        position = (10, labeled.shape[0] - 15)
        cv2.putText(labeled, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 5, cv2.LINE_AA)
        cv2.putText(labeled, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        return labeled


    def build_overlay(self, bgr, region, estimate, row):
        view = bgr[CROP_TOP:CROP_BOTTOM].copy()
        height, width = view.shape[:2]
        scaled = cv2.resize(region.astype(np.uint8), (width, height), interpolation=cv2.INTER_NEAREST).astype(bool)
        view[scaled] = ((1 - TRAIL_ALPHA) * view[scaled] + TRAIL_ALPHA * TRAIL_COLOR).astype(np.uint8)

        for mask_row, column in zip(estimate.rows, estimate.columns):
            point = (int(column * width / region.shape[1]), int(mask_row * height / region.shape[0]))
            cv2.circle(view, point, 6, (0, 255, 255), -1, cv2.LINE_AA)

        camera = row['camera_steering']
        camera_text = 'sem trilha' if camera == '' else f'{camera:+.3f}'
        text = (f"{row['step']} | {row['speed']:.1f} m/s | {row['mileage']:.0f} m | "
                f"rota {row['route_steering']:+.3f} | camera {camera_text}")
        cv2.putText(view, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(view, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1, cv2.LINE_AA)
        return view


    def close(self, reason, lap_length):
        self.log_file.close()

        for writer in self.videos.values():
            writer.release()

        summary = self.build_summary(reason, lap_length)

        with open(os.path.join(self.run_dir, 'summary.json'), 'w', encoding='utf-8') as file:
            json.dump(summary, file, indent=2, ensure_ascii=False)

        return summary


    def build_summary(self, reason, lap_length):
        rows = self.rows
        summary = {
            'map': self.config.map_name,
            'weather': self.config.weather,
            'mode': self.config.mode,
            'reason': reason,
            'steps': len(rows),
            'lap_length_m': round(lap_length, 1),
        }

        if not rows:
            return summary

        estimated = [row for row in rows if row['camera_steering'] != '']
        errors = np.array([abs(row['camera_steering'] - row['route_steering']) for row in estimated])
        centered = np.array([row['distance_from_center'] for row in rows])
        offsets = np.abs([row['lateral_offset'] for row in rows])
        edges = np.array([row['track_width'] / 2 - CAR_HALF_WIDTH for row in rows])

        summary.update({
            'mileage_m': round(rows[-1]['mileage'], 1),
            'mean_speed_ms': round(float(np.mean([row['speed'] for row in rows])), 2),
            'all_rows_found_pct': round(100 * sum(row['rows_found'] == 3 for row in rows) / len(rows), 2),
            'max_distance_from_center_m': round(float(centered.max()), 2),
            'mean_lateral_offset_m': round(float(offsets.mean()), 2),
            'max_lateral_offset_m': round(float(offsets.max()), 2),
            'wheel_past_edge_pct': round(100 * float(np.mean(offsets > edges)), 2),
            'inference_ms': InferenceMetrics().summarize([row['inference_ms'] for row in rows]),
        })

        if errors.size:
            summary['camera_vs_route_steering'] = {
                'mean': round(float(errors.mean()), 4),
                'median': round(float(np.median(errors)), 4),
                'p95': round(float(np.percentile(errors, 95)), 4),
                'max': round(float(errors.max()), 4),
            }

        return summary
