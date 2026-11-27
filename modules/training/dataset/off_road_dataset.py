import os
import torch
import numpy as np

from PIL import Image
from torch.utils.data import Dataset
from configs import paths
from modules.segmentation.transforms import build_mask_transform

class OffRoadDataset(Dataset):
    def __init__(self, root_dir, settings, img_transform=None, images=None):
        self.settings = settings
        self.rgb_dir  = os.path.join(root_dir, "original")
        self.mask_dir = os.path.join(root_dir, "mask")

        # images permite montar o treino e a validação com listas já divididas
        self.images = list(images) if images is not None else self.get_images()
        self.mask_paths = [
            os.path.join(self.mask_dir, os.path.splitext(img)[0] + ".png")
            for img in self.images
        ]

        self.img_transform = img_transform
        self.mask_transform = build_mask_transform(settings.get_image_size())


    def __len__(self):
        return len(self.images)


    def __getitem__(self, idx):
        img_path  = os.path.join(self.rgb_dir, self.images[idx])
        mask_path = self.mask_paths[idx]

        if not os.path.exists(mask_path):
            raise FileNotFoundError(f"Máscara não encontrada: {mask_path}")

        image = Image.open(img_path).convert("RGB")
        mask  = Image.open(mask_path).convert("L")

        if self.img_transform:
            image = self.img_transform(image)

        mask = self.mask_transform(mask)
        mask = (np.asarray(mask) > 0).astype(np.int64)
        mask = torch.as_tensor(mask, dtype=torch.long)

        return image, mask


    def get_images(self):
        temp_images = sorted(os.listdir(self.rgb_dir))

        images = self.filter_enabled_datasets(temp_images)

        # Execução de teste: só as primeiras imagens dos datasets escolhidos, para o treino caber num computador modesto
        if self.settings.is_test_execution_on():
            images = images[:self.settings.get_test_execution_images()]

        # Sem imagens o treino quebraria depois com divisão por zero ao calcular as médias da época
        if not images:
            raise ValueError(f"Nenhuma imagem de treino encontrada em {paths.relative(self.rgb_dir)} para os datasets habilitados no settings.json.")

        return images


    def filter_enabled_datasets(self, temp_images):
        # Os datasets vêm de Datasets_Labels; cada um é ligado pela chave de mesmo nome no settings.json
        enabled = self.settings.get_enabled_datasets()

        if not enabled:
            names = ', '.join(self.settings.get_dataset_labels())
            raise ValueError(f"Nenhum dataset habilitado: ative pelo menos um destes no settings.json: {names}.")

        prefixes = tuple(f"{name}_" for name in enabled)
        return [img for img in temp_images if img.startswith(prefixes)]
