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
        self.metrics_path = os.path.join("results", "segmentation_metrics.md")

        self.img_transform = transforms.Compose([
            transforms.Resize((512, 512)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

    def segment_images(self):
        print("Iniciando segmentação de imagens...")

        if not os.path.exists(self.input_dir):
            print(f"Pasta não encontrada: {self.input_dir}")
            return

        dataset = InferenceDataset(self.input_dir, self.img_transform)

        if len(dataset) == 0:
            print("Nenhuma imagem encontrada na pasta images_to_segment.")
            return

        print(f"Total de imagens encontradas: {len(dataset)}")

        results = []

        print("\nSegmentando com FCN...")
        fcn_result = self._process_model('fcn', FCN, dataset)
        results.append(fcn_result)

        print("\nSegmentando com DeepLabV3+...")
        deeplab_result = self._process_model('deeplabv3+', DeepLabV3Plus, dataset)
        results.append(deeplab_result)

        self._generate_metrics(results)

        print("\nSegmentação concluída!")
        print(f"Resultados salvos em: {self.output_base}")
        print(f"Métricas salvas em: {self.metrics_path}")

    def _process_model(self, model_name, model_class, dataset):
        output_dir = os.path.join(self.output_base, model_name)
        os.makedirs(output_dir, exist_ok=True)

        model_path = os.path.join("results", model_name, "model.pth")

        if not os.path.exists(model_path):
            print(f"Modelo não encontrado: {model_path}")
            return {
                'model': model_name,
                'images': 0,
                'total_time': 0,
                'avg_time_per_image': 0,
                'status': 'modelo não encontrado'
            }

        model = model_class(num_classes=2).to(self.device)
        model.load_state_dict(torch.load(model_path, map_location=self.device))
        model.eval()

        loader = DataLoader(dataset, batch_size=4, shuffle=False, num_workers=0)

        start_time = time.time()
        images_processed = 0

        with torch.no_grad():
            for images, filenames in loader:
                images = images.to(self.device)
                outputs = model(images)
                preds = torch.argmax(outputs, dim=1).cpu().numpy()

                for i in range(preds.shape[0]):
                    base_name = os.path.splitext(filenames[i])[0]
                    output_path = os.path.join(output_dir, base_name + ".png")

                    pred_img = Image.fromarray((preds[i] * 255).astype(np.uint8))
                    pred_img.save(output_path)

                    images_processed += 1
                    print(f"  Processada: {filenames[i]}")

        total_time = time.time() - start_time
        avg_time = total_time / images_processed if images_processed > 0 else 0

        print(f"  Total: {images_processed} imagens em {total_time:.2f}s (média: {avg_time:.2f}s/imagem)")

        return {
            'model': model_name,
            'images': images_processed,
            'total_time': total_time,
            'avg_time_per_image': avg_time,
            'status': 'concluído'
        }

    def _generate_metrics(self, results):
        os.makedirs(os.path.dirname(self.metrics_path), exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        total_images = sum(r['images'] for r in results)

        lines = [
            "### Segmentação de Imagens\n",
            f"**Data:** {timestamp}\n",
            "#### Resumo\n",
            f"- Total de imagens: {total_images}",
            f"- Modelos utilizados: FCN, DeepLabV3+",
            f"- Dispositivo: {self.device}\n",
            "#### Métricas por Modelo\n",
            "| Modelo | Imagens | Tempo Total | Tempo Médio/Imagem | Status |",
            "|--------|---------|-------------|-------------------|--------|"
        ]

        for r in results:
            lines.append(
                f"| {r['model']} | {r['images']} | {r['total_time']:.2f}s | {r['avg_time_per_image']:.2f}s | {r['status']} |"
            )

        lines.append("\n#### Arquivos Gerados\n")
        lines.append("- `images/segmented_images/fcn/*.png`")
        lines.append("- `images/segmented_images/deeplabv3+/*.png`")

        with open(self.metrics_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))