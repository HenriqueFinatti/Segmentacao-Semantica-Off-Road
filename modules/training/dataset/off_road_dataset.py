import os
import torch
import numpy as np

from PIL import Image
from torch.utils.data import Dataset
from configs import paths
from modules.segmentation.transforms import build_mask_transform

class OffRoadDataset(Dataset):
    def __init__(self, root_dir, settings, img_transform=None):
        self.settings = settings
        self.rgb_dir  = os.path.join(root_dir, "original")
        self.mask_dir = os.path.join(root_dir, "mask")

        self.images = self.get_images()
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

        if self.settings.is_test_execution_on():
            images = temp_images[:self.settings.get_test_execution_images()]
        else:
            images = self.filter_enabled_datasets(temp_images)

        # Sem imagens o treino quebraria depois com divisão por zero ao calcular as médias da época
        if not images:
            raise ValueError(f"Nenhuma imagem de treino encontrada em {paths.relative(self.rgb_dir)} para os datasets habilitados no settings.json.")

        return images


    def filter_enabled_datasets(self, temp_images):
        isFreiburgOn = self.settings.is_freiburg_forest_on()
        isSyntheticOn = self.settings.is_synthetic_off_road_on()

        if not (isFreiburgOn or isSyntheticOn):
            raise ValueError("Nenhum dataset habilitado: ative Freiburg_Forest ou Synthetic_Offroad no settings.json.")

        images = []
        for img in temp_images:
            img_name = img.lower()

            if "freiburg" in img_name and isFreiburgOn:
                images.append(img)
                continue

            if "synthetic" in img_name and isSyntheticOn:
                images.append(img)
                continue

        return images
