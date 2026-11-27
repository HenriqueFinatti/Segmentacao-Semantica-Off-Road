import os
import torch

from PIL import Image
from torchvision import transforms
from torch.utils.data import Dataset


VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}


class InferenceDataset(Dataset):
    def __init__(self, root_dir, img_transform=None, images=None):
        self.rgb_dir = root_dir
        # images restringe a segmentação a alguns arquivos da pasta (ex.: repetir só as imagens que falharam)
        self.images = list(images) if images is not None else self.get_images()
        self.img_transform = img_transform

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_name = self.images[idx]
        img_path = os.path.join(self.rgb_dir, img_name)

        image = Image.open(img_path).convert("RGB")
        # Tamanho original (altura, largura), para a máscara voltar ao tamanho da imagem
        original_size = torch.tensor([image.height, image.width])

        if self.img_transform:
            image = self.img_transform(image)

        return image, img_name, original_size

    def get_images(self):
        valid_extensions = VALID_EXTENSIONS
        images = []

        if not os.path.exists(self.rgb_dir):
            return images

        for img in sorted(os.listdir(self.rgb_dir)):
            ext = os.path.splitext(img)[1].lower()
            if ext in valid_extensions:
                images.append(img)

        return images