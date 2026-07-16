import os
import torch
import numpy as np
from torch.utils.data import DataLoader
from torchvision import transforms
from PIL import Image
import torch.nn as nn
import time
from models.deeplabv3 import DeepLabV3Plus
from models.dataset import OffRoadDataset

EPOCHS = 2

img_transform = transforms.Compose([
    transforms.Resize((512, 512)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = DeepLabV3Plus(num_classes=2).to(device)

class_weights = torch.tensor([1.0, 9.0]).to(device)
criterion = nn.CrossEntropyLoss(weight=class_weights)

optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

train_dataset = OffRoadDataset('data/dataset/train', img_transform)
train_loader = DataLoader(train_dataset, batch_size=4, shuffle=True, num_workers=0)

print(f"Total de imagens de treino: {len(train_dataset)}")

# =========================
# LOOP DE TREINO
# =========================
def train_one_epoch(loader):
    model.train()
    start_time = time.time()
    for batch_idx, (images, masks) in enumerate(loader):
        images = images.to(device)
        masks = masks.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, masks)
        loss.backward()
        optimizer.step()

    end_time = time.time()
    epoch_duration = end_time - start_time

    mins, secs = divmod(epoch_duration, 60)
    print(f"-> Tempo da Época: {int(mins)}m {secs:.2f}s")

# =========================
# TREINAMENTO COM RASTREAMENTO
# =========================
total_train_start = time.time()
for epoch in range(EPOCHS):
    print(f"\nÉpoca {epoch+1}/{EPOCHS}")
    train_one_epoch(train_loader)    
    
total_train_end = time.time()
total_duration = total_train_end - total_train_start

total_mins, total_secs = divmod(total_duration, 60)

print(f"==========================")
print(f"Tempo total de treinamento: {int(total_mins)}m {total_secs:.2f}s")
print(f"==========================")

# =========================
# INFERÊNCIA E SALVAMENTO
# =========================
output_dir = 'data/dataset/train/new_segmentation'

infer_loader = DataLoader(train_dataset, batch_size=4, shuffle=False, num_workers=0)
global_idx = 0

with torch.no_grad():
    for images, _ in infer_loader:
        images = images.to(device)
        outputs = model(images)
        preds = torch.argmax(outputs, dim=1).cpu().numpy()

        for i in range(preds.shape[0]):
            img_name = train_dataset.images[global_idx]
            base_name = os.path.splitext(img_name)[0]
            output_path = os.path.join(output_dir, base_name + ".png")

            # via = branco (255), não-via = preto (0)
            pred_img = Image.fromarray((preds[i] * 255).astype(np.uint8))
            pred_img.save(output_path)

            global_idx += 1
