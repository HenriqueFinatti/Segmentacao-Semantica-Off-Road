import os
import time
import torch
import numpy as np

from PIL import Image
from datetime import datetime
from torchvision import transforms
from torch.utils.data import DataLoader

from modules.metrics.chart import Charts
from modules.metrics.inference_metrics import InferenceMetrics
from modules.training.trainer.model.fcn import FCN
from modules.training.trainer.model.deeplabv3 import DeepLabV3Plus
from modules.segmentation.inference_dataset import InferenceDataset

# Passadas descartadas antes de medir, para não contar a inicialização da GPU/cuDNN
WARMUP_ITERATIONS = 5

CONTEXT_TITLES = {
    'imagens': 'Imagens',
    'teste': 'Dataset de Teste',
    'video': 'Vídeo',
}


class SegmentationService():
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
        self.input_dir = os.path.join("images", "images_to_segment")
        self.output_base = os.path.join("images", "segmented_images")
        self.test_output_base = os.path.join("dataset", "test", "new_segmentation")

        self.charts = Charts()
        self.inference_metrics = InferenceMetrics()

        self.img_transform = transforms.Compose([
            transforms.Resize((512, 512)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

    def segment_images(self, context='imagens'):
        print("Iniciando segmentação de imagens...")
        self.validate_input_dir(self.input_dir)

        dataset = InferenceDataset(self.input_dir, self.img_transform)
        self.validate_dataset(dataset)

        results = self.segment_with_all_models(dataset, self.output_base, context)
        self.print_summary(self.output_base, context)
        return results

    def segment_test_dataset(self):
        print("Iniciando segmentação do dataset de teste...")
        test_dir = os.path.join("dataset", "test", "original")
        self.validate_input_dir(test_dir)

        dataset = InferenceDataset(test_dir, self.img_transform)
        self.validate_dataset(dataset)

        results = self.segment_with_all_models(dataset, self.test_output_base, 'teste')
        self.print_summary(self.test_output_base, 'teste')
        return results

    def segment_with_all_models(self, dataset, output_base, context):
        models = [('fcn', FCN), ('deeplabv3+', DeepLabV3Plus)]
        results = {}

        for model_name, model_class in models:
            result = self.segment_with_model(model_name, model_class, dataset, output_base)

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
            raise FileNotFoundError(f"Pasta não encontrada: {input_dir}")

    def validate_dataset(self, dataset):
        if len(dataset) == 0:
            raise ValueError("Nenhuma imagem encontrada na pasta de entrada.")

    def segment_with_model(self, model_name, model_class, dataset, output_base):
        model = self.load_model(model_name, model_class)

        if model is None:
            return None

        output_dir = os.path.join(output_base, model_name)
        os.makedirs(output_dir, exist_ok=True)

        return self.run_inference(model, dataset, output_dir, model_name)

    def load_model(self, model_name, model_class):
        model_path = os.path.join("results", model_name, "model.pth")

        if not os.path.exists(model_path):
            print(f"Modelo não encontrado: {model_path}")
            return None

        model = model_class(num_classes=2).to(self.device)
        model.load_state_dict(torch.load(model_path, map_location=self.device))
        model.eval()
        return model

    def synchronized_time(self):
        # As chamadas na GPU são assíncronas; sem sincronizar o tempo medido seria só o de enfileirar
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        return time.perf_counter()

    def warmup(self, model, dataset):
        image, _ = dataset[0]
        image = image.unsqueeze(0).to(self.device)

        with torch.no_grad():
            for _ in range(WARMUP_ITERATIONS):
                model(image)

        self.synchronized_time()

    def run_inference(self, model, dataset, output_dir, model_name):
        # Batch 1 para medir o tempo real de cada frame, como em um vídeo
        loader = DataLoader(dataset, batch_size=1, shuffle=False, num_workers=0)
        self.warmup(model, dataset)

        inference_times = {}
        frame_times = {}

        start_time = time.perf_counter()
        frame_start = start_time

        with torch.no_grad():
            for images, filenames in loader:
                images = images.to(self.device)

                inference_start = self.synchronized_time()
                outputs = model(images)
                preds = torch.argmax(outputs, dim=1)
                inference_end = self.synchronized_time()

                base_name = os.path.splitext(filenames[0])[0]
                self.save_prediction(preds[0].cpu().numpy(), filenames[0], output_dir)

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


    def save_prediction(self, prediction, filename, output_dir):
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, base_name + ".png")
        pred_img = Image.fromarray((prediction * 255).astype(np.uint8))
        pred_img.save(output_path)


    def get_metrics_path(self, model_name, context):
        return os.path.join("results", model_name, "statistics", f"segmentation_{context}.md")


    def get_csv_path(self, model_name, context):
        return os.path.join("results", model_name, "statistics", f"tempos_inferencia_{context}.csv")


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
            f"| Resolução de Entrada | 512x512 |",
            f"| Batch | 1 |",
            f"| Passadas de Aquecimento | {WARMUP_ITERATIONS} |",
            f"| Status | {result['status']} |",
            "",
            *self.inference_metrics.build_markdown_table(result, self.device.type == 'cuda'),
            "",
            f"Tempos por frame: `{self.get_csv_path(model_name, context)}`",
        ]

        with open(metrics_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def print_summary(self, output_base, context):
        print("\nSegmentação concluída!")
        print(f"Resultados salvos em: {output_base}")
        print("Métricas salvas em:")
        for model_name in ['fcn', 'deeplabv3+']:
            print(f"  - {self.get_metrics_path(model_name, context)}")
            print(f"  - {self.get_csv_path(model_name, context)}")
