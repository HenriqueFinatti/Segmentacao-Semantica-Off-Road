import os
import time
import torch
import numpy as np

from PIL import Image
from datetime import datetime
from torchvision import transforms
from torch.utils.data import DataLoader

from modules.training.trainer.model.fcn import FCN
from modules.training.trainer.model.deeplabv3 import DeepLabV3Plus
from modules.segmentation.inference_dataset import InferenceDataset


class SegmentationService():
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.input_dir = os.path.join("images", "images_to_segment")
        self.output_base = os.path.join("images", "segmented_images")
        self.test_output_base = os.path.join("dataset", "test", "new_segmentation")

        self.img_transform = transforms.Compose([
            transforms.Resize((512, 512)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

    def segment_images(self):
        print("Iniciando segmentação de imagens...")
        self.validate_input_dir(self.input_dir)

        dataset = InferenceDataset(self.input_dir, self.img_transform)
        self.validate_dataset(dataset)

        fcn_result = self.segment_with_model('fcn', FCN, dataset, self.output_base)
        self.generate_metrics(fcn_result, 'fcn')

        deeplab_result = self.segment_with_model('deeplabv3+', DeepLabV3Plus, dataset, self.output_base)
        self.generate_metrics(deeplab_result, 'deeplabv3+')

        self.print_summary()

    def segment_test_dataset(self):
        print("Iniciando segmentação do dataset de teste...")
        test_dir = os.path.join("dataset", "test", "original")
        self.validate_input_dir(test_dir)

        dataset = InferenceDataset(test_dir, self.img_transform)
        self.validate_dataset(dataset)

        fcn_result = self.segment_with_model('fcn', FCN, dataset, self.test_output_base)
        self.generate_metrics(fcn_result, 'fcn')

        deeplab_result = self.segment_with_model('deeplabv3+', DeepLabV3Plus, dataset, self.test_output_base)
        self.generate_metrics(deeplab_result, 'deeplabv3+')

        self.print_summary()

    def validate_input_dir(self, input_dir):
        if not os.path.exists(input_dir):
            raise FileNotFoundError(f"Pasta não encontrada: {input_dir}")

    def validate_dataset(self, dataset):
        if len(dataset) == 0:
            raise ValueError("Nenhuma imagem encontrada na pasta de entrada.")

    def segment_with_model(self, model_name, model_class, dataset, output_base):
        output_dir = os.path.join(output_base, model_name)
        os.makedirs(output_dir, exist_ok=True)

        model = self.load_model(model_name, model_class)

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

    def run_inference(self, model, dataset, output_dir, model_name):
        loader = DataLoader(dataset, batch_size=4, shuffle=False, num_workers=0)
        start_time = time.time()
        images_processed = 0

        with torch.no_grad():
            for images, filenames in loader:
                images = images.to(self.device)
                outputs = model(images)
                preds = torch.argmax(outputs, dim=1).cpu().numpy()

                for i in range(preds.shape[0]):
                    self.save_prediction(preds[i], filenames[i], output_dir)
                    images_processed += 1

        total_time = time.time() - start_time
        avg_time = total_time / images_processed if images_processed > 0 else 0
        return {
            'model': model_name,
            'images': images_processed,
            'total_time': total_time,
            'avg_time_per_image': avg_time,
            'status': "concluído"
        }


    def save_prediction(self, prediction, filename, output_dir):
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, base_name + ".png")
        pred_img = Image.fromarray((prediction * 255).astype(np.uint8))
        pred_img.save(output_path)


    def generate_metrics(self, result, model_name):
        metrics_dir = os.path.join("results", model_name, "statistics")
        os.makedirs(metrics_dir, exist_ok=True)
        metrics_path = os.path.join(metrics_dir, "segmentation.md")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"### Segmentação de Imagens - {model_name.upper()}\n",
            f"**Data:** {timestamp}\n",
            "#### Métricas\n",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Imagens Processadas | {result['images']} |",
            f"| Tempo Total | {result['total_time']:.2f}s |",
            f"| Tempo Médio/Imagem | {result['avg_time_per_image']:.2f}s |",
            f"| Dispositivo | {self.device} |",
            f"| Status | {result['status']} |"
        ]

        with open(metrics_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def print_summary(self):
        print("\nSegmentação concluída!")
        print(f"Resultados salvos em: {self.output_base}")
        print("Métricas salvas em:")
        print(f"  - results/fcn/statistics/segmentation.md")
        print(f"  - results/deeplabv3+/statistics/segmentation.md")