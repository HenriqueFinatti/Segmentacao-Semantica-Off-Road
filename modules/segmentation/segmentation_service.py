import os
import time
import torch
import numpy as np

from PIL import Image
from datetime import datetime
from torch.utils.data import DataLoader

from configs import paths
from modules.metrics.chart import Charts
from modules.metrics.inference_metrics import InferenceMetrics
from modules.metrics.test_evaluator import TestEvaluator
from modules.models.registry import MODELS
from modules.segmentation.inference_dataset import InferenceDataset
from modules.segmentation.predictor import Predictor, WARMUP_ITERATIONS
from modules.segmentation.transforms import build_image_transform

CONTEXT_TITLES = {
    'imagens': 'Imagens',
    'teste': 'Dataset de Teste',
    'video': 'Vídeo',
}


class SegmentationService():
    def __init__(self, settings):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
        self.input_dir = paths.IMAGES_TO_SEGMENT_DIR
        self.output_base = paths.SEGMENTED_IMAGES_DIR
        self.test_output_base = paths.TEST_SEGMENTATION_DIR

        self.charts = Charts(settings)
        self.inference_metrics = InferenceMetrics()
        self.test_evaluator = TestEvaluator(settings, self.charts)

        self.image_size = settings.get_image_size()
        self.img_transform = build_image_transform(self.image_size)

    def segment_images(self):
        print("Iniciando segmentação de imagens...")
        return self.segment_folder(self.input_dir, self.output_base, 'imagens')

    def segment_test_dataset(self):
        print("Iniciando segmentação do dataset de teste...")
        results = self.segment_folder(paths.dataset_dir('test', 'original'), self.test_output_base, 'teste')

        # Avalia só os modelos que acabaram de segmentar, para não misturar predições antigas
        self.test_evaluator.evaluate_all_models(list(results))
        return results

    def evaluate_test_dataset(self):
        # Avalia as predições que já estão salvas, sem segmentar de novo
        return self.test_evaluator.evaluate_all_models()

    def segment_video_frames(self):
        print("Iniciando segmentação do vídeo...")
        return self.segment_folder(paths.VIDEO_FRAMES_DIR, paths.VIDEO_SEGMENTED_FRAMES_DIR, 'video')

    def segment_folder(self, input_dir, output_base, context):
        self.validate_input_dir(input_dir)

        dataset = InferenceDataset(input_dir, self.img_transform)
        self.validate_dataset(dataset)

        results = self.segment_with_all_models(dataset, output_base, context)
        self.print_summary(results, output_base, context)
        return results

    def segment_with_all_models(self, dataset, output_base, context):
        results = {}

        for model_name in MODELS:
            result = self.segment_with_model(model_name, dataset, output_base)

            if result is None:
                print(f"Pulando {model_name.upper()}: modelo ainda não foi treinado.")
                continue

            self.inference_metrics.print_summary(result)
            self.generate_metrics(result, model_name, context)
            self.inference_metrics.save_csv(result, self.get_csv_path(model_name, context))
            self.charts.plot_inference_times(result, model_name, context)
            results[model_name] = result

        if not results:
            raise FileNotFoundError("Nenhum modelo treinado encontrado em results/. Treine pelo menos um modelo antes de segmentar.")

        if len(results) > 1:
            self.charts.plot_inference_comparison(results, context)

        return results

    def validate_input_dir(self, input_dir):
        if not os.path.exists(input_dir):
            raise FileNotFoundError(f"Pasta não encontrada: {paths.relative(input_dir)}")

    def validate_dataset(self, dataset):
        if len(dataset) == 0:
            raise ValueError("Nenhuma imagem encontrada na pasta de entrada.")

    def segment_with_model(self, model_name, dataset, output_base):
        predictor = self.load_predictor(model_name)

        if predictor is None:
            return None

        output_dir = os.path.join(output_base, model_name)
        os.makedirs(output_dir, exist_ok=True)

        return self.run_inference(predictor, dataset, output_dir, model_name)

    def load_predictor(self, model_name):
        try:
            return Predictor(model_name, self.image_size, self.device)
        except FileNotFoundError as error:
            print(error)
            return None

    def synchronized_time(self):
        # As chamadas na GPU são assíncronas; sem sincronizar o tempo medido seria só o de enfileirar
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        return time.perf_counter()

    def run_inference(self, predictor, dataset, output_dir, model_name):
        # Batch 1 para medir o tempo real de cada frame, como em um vídeo
        loader = DataLoader(dataset, batch_size=1, shuffle=False, num_workers=0)
        predictor.warmup(dataset[0][0])

        inference_times = {}
        frame_times = {}

        start_time = time.perf_counter()
        frame_start = start_time

        with torch.no_grad():
            for images, filenames, original_sizes in loader:
                images = images.to(self.device)

                inference_start = self.synchronized_time()
                preds = predictor.predict_tensor(images)
                inference_end = self.synchronized_time()

                base_name = os.path.splitext(filenames[0])[0]
                self.save_prediction(preds[0].cpu().numpy(), filenames[0], output_dir, original_sizes[0].tolist())

                frame_end = time.perf_counter()
                inference_times[base_name] = (inference_end - inference_start) * 1000
                frame_times[base_name] = (frame_end - frame_start) * 1000
                frame_start = frame_end

        total_time = time.perf_counter() - start_time
        images_processed = len(inference_times)

        return {
            'model': model_name,
            'images': images_processed,
            'total_time': total_time,
            'avg_time_per_image': total_time / images_processed if images_processed > 0 else 0,
            'inference_times': inference_times,
            'frame_times': frame_times,
            'inference_stats': self.inference_metrics.summarize(list(inference_times.values())),
            'frame_stats': self.inference_metrics.summarize(list(frame_times.values())),
            'status': "concluído"
        }


    def save_prediction(self, prediction, filename, output_dir, original_size):
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, base_name + ".png")
        height, width = original_size

        # O modelo trabalha em image_size x image_size; a máscara volta ao tamanho da imagem original.
        # NEAREST para continuar só com 0 e 255
        pred_img = Image.fromarray((prediction * 255).astype(np.uint8))
        pred_img = pred_img.resize((width, height), Image.NEAREST)
        pred_img.save(output_path)


    def get_metrics_path(self, model_name, context):
        return os.path.join(paths.statistics_dir(model_name), f"segmentation_{context}.md")


    def get_csv_path(self, model_name, context):
        return os.path.join(paths.statistics_dir(model_name), f"tempos_inferencia_{context}.csv")


    def generate_metrics(self, result, model_name, context):
        metrics_path = self.get_metrics_path(model_name, context)
        os.makedirs(os.path.dirname(metrics_path), exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"### Segmentação de {CONTEXT_TITLES[context]} - {model_name.upper()}\n",
            f"**Data:** {timestamp}\n",
            "#### Métricas\n",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Imagens Processadas | {result['images']} |",
            f"| Tempo Total | {result['total_time']:.2f}s |",
            f"| Tempo Médio de Inferência/Frame | {result['inference_stats']['mean']:.2f} ms |",
            f"| FPS de Inferência | {result['inference_stats']['fps']:.1f} |",
            f"| Dispositivo | {self.device_name} |",
            f"| Resolução de Entrada | {self.image_size}x{self.image_size} |",
            f"| Batch | 1 |",
            f"| Passadas de Aquecimento | {WARMUP_ITERATIONS} |",
            f"| Status | {result['status']} |",
            "",
            *self.inference_metrics.build_markdown_table(result, self.device.type == 'cuda'),
            "",
            f"Tempos por frame: `{paths.relative(self.get_csv_path(model_name, context))}`",
        ]

        with open(metrics_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def print_summary(self, results, output_base, context):
        print("\nSegmentação concluída!")
        print(f"Resultados salvos em: {paths.relative(output_base)}")
        print("Métricas salvas em:")
        for model_name in results:
            print(f"  - {paths.relative(self.get_metrics_path(model_name, context))}")
            print(f"  - {paths.relative(self.get_csv_path(model_name, context))}")
