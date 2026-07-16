import os
import torch
import numpy as np
from torch.utils.data import Dataset
from torchvision import transforms
from PIL import Image

class OffRoadDataset(Dataset):
    def __init__(self, root_dir, img_transform=None):
        self.rgb_dir  = os.path.join(root_dir, "original")
        self.mask_dir = os.path.join(root_dir, "mask")

        self.images = sorted(os.listdir(self.rgb_dir))
        self.images = [img for img in self.images if 'freiburg' in img.lower()]

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
