import os
import cv2

from configs import paths
from modules.models.registry import MODELS

class Video:

    def __init__(self, video_path=paths.VIDEO_PATH, output_dir=paths.VIDEO_OUTPUT_DIR):
        self.video_path = video_path
        self.output_dir = output_dir
        self.images_dir = paths.VIDEO_FRAMES_DIR
        self.segmented_images_dir = paths.VIDEO_SEGMENTED_FRAMES_DIR

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
            for frame_id in range(total_frames):
                succes, frame = video.read()

                if not succes:
                    raise RuntimeError(f"Não foi possivel gerar o frame {frame_id} do vídeo")

                frame_path = os.path.join(self.images_dir,f"frame_{frame_id:06d}.png")
                cv2.imwrite(str(frame_path), frame)

                frame_count += 1
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

    def _build_video(self, model, inference_times=None):
        images_path = os.path.join(self.segmented_images_dir, model)
        frames = sorted(
            filename for filename in os.listdir(images_path) if filename.endswith(".png")
        )

        if not frames:
            raise FileNotFoundError(f"Nenhuma imagem encontrada em {images_path}")

        first_frame_path = os.path.join(images_path, frames[0])
        first_frame = cv2.imread(first_frame_path)

        if first_frame is None:
            raise RuntimeError(f"Não foi possível ler {first_frame_path}")

        height, width = first_frame.shape[:2]
        output_path = os.path.join(self.output_dir, f"{model}.mp4")

        writer = cv2.VideoWriter(
            output_path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            self.video_fps,
            (width,height)
        )

        if not writer.isOpened():
            raise RuntimeError(f"Não foi possível criar o vídeo: {output_path}")
        
        try:
            for filename in frames:
                frame_path = os.path.join(
                    images_path, filename
                )
                frame = cv2.imread(frame_path)

                if frame is None:
                    raise RuntimeError(
                        f"Não foi possível ler a imagem: {frame_path}"
                    )

                if frame.shape[:2] != (height, width):
                    frame = cv2.resize(frame, (width, height))

                if len(frame.shape) == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

                frame_name = os.path.splitext(filename)[0]
                if inference_times and frame_name in inference_times:
                    self._draw_inference_time(frame, model, inference_times[frame_name])

                writer.write(frame)
        finally:
            writer.release()


    def make_segmented_video(self, segmentation_results=None):
        segmentation_results = segmentation_results or {}

        for model in MODELS:
            if not os.path.isdir(os.path.join(self.segmented_images_dir, model)):
                print(f"Pulando vídeo do {model.upper()}: nenhuma imagem segmentada.")
                continue

            inference_times = segmentation_results.get(model, {}).get('inference_times')
            self._build_video(model, inference_times)
