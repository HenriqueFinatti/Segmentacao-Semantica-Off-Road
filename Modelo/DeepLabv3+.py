import os
import torch
import numpy as np
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import torch.nn as nn
import torch.nn.functional as F

# =========================
# DATASET
# =========================
class OffRoadDataset(Dataset):
    def __init__(self, root_dir, img_transform=None, filter_freiburg=False):
        self.rgb_dir  = os.path.join(root_dir, "rgb")
        self.mask_dir = os.path.join(root_dir, "mask_labels")

        if not os.path.exists(self.rgb_dir):
            raise FileNotFoundError(f"RGB dir não existe: {self.rgb_dir}")
        if not os.path.exists(self.mask_dir):
            raise FileNotFoundError(f"Mask dir não existe: {self.mask_dir}")

        self.images = sorted(os.listdir(self.rgb_dir))

        if filter_freiburg:
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


# =========================
# TRANSFORM
# =========================
img_transform = transforms.Compose([
    transforms.Resize((512, 512)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])


# =========================
# MODELO
# =========================
class ASPP(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=6,  dilation=6,  bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )
        self.conv3 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=12, dilation=12, bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )
        self.conv4 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=18, dilation=18, bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )
        self.pool = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )
        self.project = nn.Sequential(
            nn.Conv2d(out_channels * 5, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )

    def forward(self, x):
        size = x.shape[-2:]
        feats = [
            self.conv1(x),
            self.conv2(x),
            self.conv3(x),
            self.conv4(x),
            F.interpolate(self.pool(x), size=size, mode='bilinear', align_corners=False)
        ]
        return self.project(torch.cat(feats, dim=1))


class DeepLabV3Plus(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        import torchvision.models as models
        resnet = models.resnet152(weights='IMAGENET1K_V1')
        self.backbone_low   = nn.Sequential(*list(resnet.children())[:5])
        self.backbone_high  = nn.Sequential(*list(resnet.children())[5:8])
        self.aspp           = ASPP(2048, 256)
        self.low_level_conv = nn.Sequential(
            nn.Conv2d(256, 48, 1, bias=False),
            nn.BatchNorm2d(48), nn.ReLU()
        )
        self.final_conv = nn.Sequential(
            nn.Conv2d(304, 256, 3, padding=1, bias=False),
            nn.BatchNorm2d(256), nn.ReLU(),
            nn.Conv2d(256, 256, 3, padding=1, bias=False),
            nn.BatchNorm2d(256), nn.ReLU(),
            nn.Conv2d(256, num_classes, 1)
        )

    def forward(self, x):
        size = x.shape[-2:]
        low  = self.backbone_low(x)
        high = self.backbone_high(low)
        x    = self.aspp(high)
        x    = F.interpolate(x, size=low.shape[-2:], mode='bilinear', align_corners=False)
        low  = self.low_level_conv(low)
        x    = torch.cat([x, low], dim=1)
        x    = self.final_conv(x)
        return F.interpolate(x, size=size, mode='bilinear', align_corners=False)


# =========================
# CONFIGURAÇÃO
# =========================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Usando dispositivo: {device}")

model     = DeepLabV3Plus(num_classes=2).to(device)

# AJUSTE 1: peso de classe — penaliza 9x mais errar na trilha (~10% dos pixels)
# evita que a rede aprenda a prever sempre "não-via" para minimizar o loss
class_weights = torch.tensor([1.0, 9.0]).to(device)
criterion     = nn.CrossEntropyLoss(weight=class_weights)

optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

train_dataset = OffRoadDataset('data/dataset/train', img_transform, filter_freiburg=True)
train_loader  = DataLoader(train_dataset, batch_size=4, shuffle=True, num_workers=0)

print(f"Total de imagens de treino: {len(train_dataset)}")


# =========================
# LOOP DE TREINO
# =========================
def train_one_epoch(loader):
    model.train()
    total_loss = 0.0

    for batch_idx, (images, masks) in enumerate(loader):
        images = images.to(device)
        masks  = masks.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss    = criterion(outputs, masks)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

        if (batch_idx + 1) % 10 == 0:
            print(f"  Batch {batch_idx+1}/{len(loader)} — loss: {loss.item():.4f}")

    return total_loss / len(loader)


num_epochs = 100
best_loss  = float('inf')

for epoch in range(num_epochs):
    print(f"\nÉpoca {epoch+1}/{num_epochs}")
    avg_loss = train_one_epoch(train_loader)
    print(f"  Loss médio: {avg_loss:.4f}")

    if avg_loss < best_loss:
        best_loss = avg_loss
        torch.save(model.state_dict(), 'best_model.pth')
        print(f"  ✓ Melhor modelo salvo (loss: {best_loss:.4f})")

print(f"\nTreino finalizado. Melhor loss: {best_loss:.4f}")


# =========================
# AJUSTE 2: DIAGNÓSTICO
# =========================
model.load_state_dict(torch.load('best_model.pth', map_location=device))
model.eval()

print("\n--- Diagnóstico ---")

total_via    = 0
total_pixels = 0
for _, mask in train_dataset:
    total_via    += mask.sum().item()
    total_pixels += mask.numel()
pct_via = 100 * total_via / total_pixels
print(f"Gabarito — via: {pct_via:.1f}%  |  não-via: {100 - pct_via:.1f}%")

with torch.no_grad():
    images, _ = next(iter(DataLoader(train_dataset, batch_size=8, shuffle=False)))
    outputs   = model(images.to(device))
    preds     = torch.argmax(outputs, dim=1).cpu()
    pct_pred  = 100 * preds.sum().item() / preds.numel()
    print(f"Predição  — via: {pct_pred:.1f}%  |  não-via: {100 - pct_pred:.1f}%")

with torch.no_grad():
    images, _ = next(iter(DataLoader(train_dataset, batch_size=1, shuffle=False)))
    output    = model(images.to(device))
    print(f"Logit classe 0 (não-via) — média: {output[0,0].mean().item():.4f}")
    print(f"Logit classe 1 (via)     — média: {output[0,1].mean().item():.4f}")

print("-------------------\n")


# =========================
# INFERÊNCIA E SALVAMENTO
# =========================
output_dir = 'data/dataset/train/mask'
os.makedirs(output_dir, exist_ok=True)

infer_loader = DataLoader(train_dataset, batch_size=4, shuffle=False, num_workers=0)
global_idx   = 0

with torch.no_grad():
    for images, _ in infer_loader:
        images  = images.to(device)
        outputs = model(images)
        preds   = torch.argmax(outputs, dim=1).cpu().numpy()

        for i in range(preds.shape[0]):
            img_name    = train_dataset.images[global_idx]
            base_name   = os.path.splitext(img_name)[0]
            output_path = os.path.join(output_dir, base_name + ".png")

            # via = branco (255), não-via = preto (0)
            pred_img = Image.fromarray((preds[i] * 255).astype(np.uint8))
            pred_img.save(output_path)

            global_idx += 1

print(f"✓ {global_idx} imagens segmentadas salvas em: {output_dir}")