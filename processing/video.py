import os
import cv2

class Video:

    def __init__(self, video_path, output_dir):
        self.video_path = video_path
        self.output_dir = output_dir
        self.images_dir = os.path.join("images", "images_to_segment")
        self.segmented_images_dir = os.path.join("images", "segmented_images")

        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.segmented_images_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        self.video_fps = None

    def extract_video(self):
        frame_count = 0
        video = cv2.VideoCapture(self.video_path)

        if not video.isOpened():
            raise FileNotFoundError(f"Não foi possível encontrar o video no caminho especificado: {self.video_path}")

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

    def _build_video(self, model):
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

                writer.write(frame)
        finally:
            writer.release()


    def make_segmented_video(self):
        for model in ["fcn", "deeplabv3+"]:
            if not os.path.isdir(os.path.join(self.segmented_images_dir, model)):
                print(f"Pulando vídeo do {model.upper()}: nenhuma imagem segmentada.")
                continue

            self._build_video(model)
