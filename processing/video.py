import os
import cv2
import numpy as np

from configs import paths
from modules.models.registry import MODELS

# Mesma cor e transparência do overlay do CARLA (vermelho em BGR)
TRAIL_COLOR = np.array([0, 0, 255], dtype=np.uint8)
TRAIL_ALPHA = 0.45

class Video:

    def __init__(self, video_path=paths.VIDEO_PATH, output_dir=paths.VIDEO_OUTPUT_DIR,
                 frames_dir=paths.VIDEO_FRAMES_DIR, segmented_frames_dir=paths.VIDEO_SEGMENTED_FRAMES_DIR):
        self.video_path = video_path
        self.output_dir = output_dir
        self.images_dir = frames_dir
        self.segmented_images_dir = segmented_frames_dir

        os.makedirs(self.output_dir, exist_ok=True)

        self.video_fps = None

    def clear_frames(self):
        # Remove frames de um vídeo anterior, senão um vídeo mais curto herdaria os frames finais do outro
        for folder in [self.images_dir, self.segmented_images_dir]:
            if os.path.isdir(folder):
                paths.safe_rmtree(folder)
            os.makedirs(folder, exist_ok=True)

    def extract_video(self):
        frame_count = 0
        video = cv2.VideoCapture(self.video_path)

        if not video.isOpened():
            raise FileNotFoundError(f"Não foi possível encontrar o video no caminho especificado: {paths.relative(self.video_path)}")

        self.clear_frames()

        self.video_fps = video.get(cv2.CAP_PROP_FPS)
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

        if self.video_fps <= 0:
            video.release()
            raise ValueError("Não foi possível obter um FPS válido do vídeo.")

        try:
            frame_id = 0
            while video.isOpened():
                success, frame = video.read()
                
                # Se falhou, geralmente indica que o vídeo chegou ao fim de forma natural
                if not success:
                    break 

                frame_path = os.path.join(self.images_dir, f"frame_{frame_id:06d}.png")
                cv2.imwrite(str(frame_path), frame)

                frame_count += 1
                frame_id += 1
        finally:
            video.release()

        return frame_count

    def _draw_inference_time(self, frame, model, inference_ms):
        # Fontes do OpenCV não suportam acentos
        text = f"{model.upper()} | Inferencia: {inference_ms:.1f} ms ({1000 / inference_ms:.1f} FPS)"
        position = (10, 25)
        font = cv2.FONT_HERSHEY_SIMPLEX

        cv2.putText(frame, text, position, font, 0.6, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(frame, text, position, font, 0.6, (0, 255, 255), 1, cv2.LINE_AA)

    def _overlay_mask(self, frame, mask):
        # Pinta a trilha prevista sobre o frame original, como no overlay do CARLA
        overlay = frame.copy()
        trail = mask > 0
        overlay[trail] = ((1 - TRAIL_ALPHA) * frame[trail] + TRAIL_ALPHA * TRAIL_COLOR).astype(np.uint8)
        return overlay

    def _open_writer(self, output_path, size):
        writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), self.video_fps, size)

        if not writer.isOpened():
            raise RuntimeError(f"Não foi possível criar o vídeo: {paths.relative(output_path)}")

        return writer

    def _build_video(self, model, inference_times=None):
        masks_path = os.path.join(self.segmented_images_dir, model)
        frames = sorted(
            filename for filename in os.listdir(masks_path) if filename.endswith(".png")
        )

        if not frames:
            raise FileNotFoundError(f"Nenhuma imagem encontrada em {paths.relative(masks_path)}")

        first_frame = cv2.imread(os.path.join(self.images_dir, frames[0]))

        if first_frame is None:
            raise RuntimeError(f"Não foi possível ler o frame original {frames[0]} em {paths.relative(self.images_dir)}")

        height, width = first_frame.shape[:2]
        overlay_writer = self._open_writer(os.path.join(self.output_dir, f"{model}.mp4"), (width, height))
        mask_writer = self._open_writer(os.path.join(self.output_dir, f"{model}_mascara.mp4"), (width, height))

        try:
            for filename in frames:
                frame_path = os.path.join(self.images_dir, filename)
                mask_path = os.path.join(masks_path, filename)
                frame = cv2.imread(frame_path)
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

                if frame is None or mask is None:
                    raise RuntimeError(f"Não foi possível ler o frame ou a máscara de {filename}")

                # As máscaras já vêm no tamanho do frame; isto só protege contra máscaras antigas em 512x512
                if mask.shape != (height, width):
                    mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)

                overlay = self._overlay_mask(frame, mask)
                mask_frame = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

                frame_name = os.path.splitext(filename)[0]
                if inference_times and frame_name in inference_times:
                    self._draw_inference_time(overlay, model, inference_times[frame_name])
                    self._draw_inference_time(mask_frame, model, inference_times[frame_name])

                overlay_writer.write(overlay)
                mask_writer.write(mask_frame)
        finally:
            overlay_writer.release()
            mask_writer.release()


    def make_segmented_video(self, segmentation_results=None):
        segmentation_results = segmentation_results or {}

        for model in MODELS:
            if not os.path.isdir(os.path.join(self.segmented_images_dir, model)):
                print(f"Pulando vídeo do {model.upper()}: nenhuma imagem segmentada.")
                continue

            inference_times = segmentation_results.get(model, {}).get('inference_times')
            self._build_video(model, inference_times)


def read_video_info(video_path):
    """Retorna (fps, total de quadros) ou None se o arquivo não for um vídeo que o OpenCV consegue abrir."""
    video = cv2.VideoCapture(video_path)
    try:
        if not video.isOpened():
            return None
        fps = video.get(cv2.CAP_PROP_FPS)
        success, _ = video.read()
        if not success or fps <= 0:
            return None
        return fps, int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        video.release()


def extract_frames(video_path, output_dir, prefix, on_frame=None):
    """Salva cada quadro do vídeo como <prefix>_quadro_000000.png em output_dir. Retorna a lista de nomes e o FPS."""
    video = cv2.VideoCapture(video_path)

    if not video.isOpened():
        raise FileNotFoundError(f"Não foi possível abrir o vídeo: {paths.relative(video_path)}")

    fps = video.get(cv2.CAP_PROP_FPS)
    total = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    os.makedirs(output_dir, exist_ok=True)
    names = []

    try:
        while True:
            success, frame = video.read()
            if not success:
                break

            name = f"{prefix}_quadro_{len(names):06d}.png"
            cv2.imwrite(os.path.join(output_dir, name), frame)
            names.append(name)

            if on_frame:
                on_frame(len(names), max(total, len(names)))
    finally:
        video.release()

    return names, fps


def paint_trail(frame, mask):
    """Pinta a trilha prevista (pixels > 0 da máscara) sobre a imagem BGR, na mesma cor do overlay do CARLA."""
    height, width = frame.shape[:2]
    if mask.shape != (height, width):
        mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
    trail = mask > 0
    frame[trail] = ((1 - TRAIL_ALPHA) * frame[trail] + TRAIL_ALPHA * TRAIL_COLOR).astype(np.uint8)
    return frame


def build_overlay_image(image_path, mask_path):
    """PNG (bytes) da imagem com a trilha prevista pintada por cima, para baixar."""
    frame = cv2.imread(image_path)
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if frame is None or mask is None:
        raise RuntimeError(f"Não foi possível ler a imagem ou a máscara de {os.path.basename(image_path)}")

    ok, png = cv2.imencode('.png', paint_trail(frame, mask))
    if not ok:
        raise RuntimeError(f"Não foi possível gerar a sobreposição de {os.path.basename(image_path)}")
    return png.tobytes()


def build_overlay_video(frames_dir, masks_dir, frame_names, output_path, fps, label=None):
    """Monta um MP4 com a trilha prevista pintada sobre cada quadro (para baixar). Quadros sem máscara ficam sem pintura."""
    if not frame_names:
        raise ValueError("Nenhum quadro para montar o vídeo.")

    first = cv2.imread(os.path.join(frames_dir, frame_names[0]))
    if first is None:
        raise RuntimeError(f"Não foi possível ler o quadro {frame_names[0]}")

    height, width = first.shape[:2]
    writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Não foi possível criar o vídeo: {paths.relative(output_path)}")

    try:
        for name in frame_names:
            frame = cv2.imread(os.path.join(frames_dir, name))
            mask = cv2.imread(os.path.join(masks_dir, os.path.splitext(name)[0] + '.png'), cv2.IMREAD_GRAYSCALE)

            if mask is not None:
                paint_trail(frame, mask)

            if label:
                # Fontes do OpenCV não suportam acentos
                cv2.putText(frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4, cv2.LINE_AA)
                cv2.putText(frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1, cv2.LINE_AA)

            writer.write(frame)
    finally:
        writer.release()
