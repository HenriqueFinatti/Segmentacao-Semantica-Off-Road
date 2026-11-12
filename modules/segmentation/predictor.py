import os
import torch
import numpy as np

from PIL import Image

from configs import paths
from modules.models.registry import build_model
from modules.segmentation.transforms import build_image_transform

# Passadas descartadas antes de medir, para não contar a inicialização da GPU/cuDNN
WARMUP_ITERATIONS = 5


class Predictor:
    def __init__(self, model_name, device=None):
        model_path = paths.model_path(model_name)

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo não encontrado: {paths.relative(model_path)}")

        self.model_name = model_name
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.transform = build_image_transform()

        # Os pesos do ImageNet não são baixados: todos são substituídos pelo model.pth
        self.model = build_model(model_name, pretrained=False).to(self.device)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()


    def warmup(self, image, iterations=WARMUP_ITERATIONS):
        batch = image.unsqueeze(0).to(self.device)

        for _ in range(iterations):
            self.predict_tensor(batch)

        if self.device.type == 'cuda':
            torch.cuda.synchronize()


    def predict_tensor(self, images):
        with torch.no_grad():
            outputs = self.model(images.to(self.device))
            return torch.argmax(outputs, dim=1)


    def predict(self, rgb):
        """Recebe um frame RGB uint8 (H, W, 3) e retorna a máscara uint8 (512, 512) com 0 ou 1."""
        image = self.transform(Image.fromarray(rgb)).unsqueeze(0)
        return self.predict_tensor(image)[0].cpu().numpy().astype(np.uint8)
