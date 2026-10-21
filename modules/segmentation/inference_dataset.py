import os
import torch

from PIL import Image
from torchvision import transforms
from torch.utils.data import Dataset


class InferenceDataset(Dataset):
    def __init__(self, root_dir, img_transform=None):
        self.rgb_dir = root_dir
        self.images = self.get_images()
        self.img_transform = img_transform

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_name = self.images[idx]
        img_path = os.path.join(self.rgb_dir, img_name)

        image = Image.open(img_path).convert("RGB")

        if self.img_transform:
            image = self.img_transform(image)

        return image, img_name

    def get_images(self):
        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        images = []

        if not os.path.exists(self.rgb_dir):
            return images

        for img in sorted(os.listdir(self.rgb_dir)):
            ext = os.path.splitext(img)[1].lower()
            if ext in valid_extensions:
                images.append(img)

        return images