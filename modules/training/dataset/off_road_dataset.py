import os
import torch
import numpy as np

from PIL import Image
from torchvision import transforms
from torch.utils.data import Dataset
from configs.settings import Settings

class OffRoadDataset(Dataset):
    def __init__(self, root_dir, img_transform=None):
        self.settings = Settings()
        self.rgb_dir  = os.path.join(root_dir, "original")
        self.mask_dir = os.path.join(root_dir, "mask")

        self.images = self.get_images()

        self.img_transform = img_transform


    def __len__(self):
        return len(self.images)


    def __getitem__(self, idx):
        img_name  = self.images[idx]
        img_path  = os.path.join(self.rgb_dir, img_name)
        base      = os.path.splitext(img_name)[0]
        mask_path = os.path.join(self.mask_dir, base + ".png")

        if not os.path.exists(mask_path):
            raise FileNotFoundError(f"Máscara não encontrada: {mask_path}")

        image = Image.open(img_path).convert("RGB")
        mask  = Image.open(mask_path).convert("L")

        if self.img_transform:
            image = self.img_transform(image)

        mask = transforms.Resize((512, 512), interpolation=Image.NEAREST)(mask)
        mask = np.array(mask)
        mask = (mask > 0).astype(np.int64)
        mask = torch.as_tensor(mask, dtype=torch.long)

        return image, mask


    def get_images(self):
        temp_images = sorted(os.listdir(self.rgb_dir))
        images = []

        if self.settings.is_test_execution_on():
            for i in range(0, 2):
                images.append(temp_images[i])

            return images

        isFreiburgOn = self.settings.is_freiburg_forest_on()
        isSyntheticOn = self.settings.is_synthetic_off_road_on()

        if isSyntheticOn or isFreiburgOn:
            for img in temp_images:
                img_name = img.lower()

                if "freiburg" in img_name and isFreiburgOn:
                    images.append(img)
                    continue

                if "synthetic" in img_name and isSyntheticOn:
                    images.append(img)
                    continue

            return images
