import os
import torch
import numpy as np
import matplotlib.pyplot as plt
import time
from datetime import datetime
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import torch.nn as nn
import torch.nn.functional as F

# =========================
# CÁLCULO DE MÉTRICAS
# =========================
def calculate_metrics(preds, masks, num_classes=2):
    """
    Calcula Pixel Accuracy e Mean IoU.
    """
    with torch.no_grad():
        # Pixel Accuracy
        correct = (preds == masks).sum().item()
        total = masks.numel()
        acc = correct / total

        # IoU por classe
        iou_list = []
        for cls in range(num_classes):
            intersection = ((preds == cls) & (masks == cls)).sum().item()
            union = ((preds == cls) | (masks == cls)).sum().item()
            
            if union == 0:
                iou_list.append(float('nan'))
            else:
                iou_list.append(intersection / union)
        
        # Média das classes (Mean IoU)
        miou = np.nanmean(iou_list)
        
    return acc, miou, iou_list


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
# CLASSE PARA TRACKING DE MÉTRICAS
# =========================
class MetricsTracker:
    def __init__(self):
        self.losses = []
        self.accuracies = []
        self.mious = []
        self.epochs = []
        self.inference_times = []
        self.training_start_time = None
        self.total_training_time = 0
        
    def add_epoch(self, epoch, loss, acc, miou):
        self.epochs.append(epoch)
        self.losses.append(loss)
        self.accuracies.append(acc)
        self.mious.append(miou)
    
    def add_inference_time(self, time_ms):
        self.inference_times.append(time_ms)
    
    def start_training(self):
        self.training_start_time = time.time()
    
    def end_training(self):
        if self.training_start_time:
            self.total_training_time = time.time() - self.training_start_time
    
    def get_avg_inference_time(self):
        return np.mean(self.inference_times) if self.inference_times else 0
    
    def get_total_training_time(self):
        return self.total_training_time


# =========================
# FUNÇÕES DE VISUALIZAÇÃO
# =========================
def plot_loss(metrics_tracker, save_dir='./metrics'):
    """
    Cria gráfico individual de Loss
    """
    os.makedirs(save_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(metrics_tracker.epochs, metrics_tracker.losses, 'b-', linewidth=2.5, marker='o', markersize=5)
    ax.set_xlabel('Época', fontsize=13, fontweight='bold')
    ax.set_ylabel('Loss', fontsize=13, fontweight='bold')
    ax.set_title('Evolução do Loss ao Longo do Treinamento', fontsize=15, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_facecolor('#f0f0f0')
    
    # Anotação do melhor valor
    best_loss_idx = np.argmin(metrics_tracker.losses)
    ax.annotate(f'Min: {metrics_tracker.losses[best_loss_idx]:.4f}', 
                xy=(metrics_tracker.epochs[best_loss_idx], metrics_tracker.losses[best_loss_idx]),
                xytext=(10, 10), textcoords='offset points', 
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', lw=2))
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, '01_loss.png'), dpi=300, bbox_inches='tight')
    print(f"✓ Gráfico de Loss salvo em: {save_dir}/01_loss.png")
    plt.close()


def plot_accuracy(metrics_tracker, save_dir='./metrics'):
    """
    Cria gráfico individual de Acurácia
    """
    os.makedirs(save_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(metrics_tracker.epochs, metrics_tracker.accuracies, 'c-', linewidth=2.5, marker='s', markersize=5)
    ax.set_xlabel('Época', fontsize=13, fontweight='bold')
    ax.set_ylabel('Acurácia', fontsize=13, fontweight='bold')
    ax.set_title('Evolução da Acurácia ao Longo do Treinamento', fontsize=15, fontweight='bold')
    ax.set_ylim([0, 1.0])
    ax.grid(True, alpha=0.3)
    ax.set_facecolor('#f0f0f0')
    
    # Anotação do melhor valor
    best_acc_idx = np.argmax(metrics_tracker.accuracies)
    ax.annotate(f'Max: {metrics_tracker.accuracies[best_acc_idx]:.4f}', 
                xy=(metrics_tracker.epochs[best_acc_idx], metrics_tracker.accuracies[best_acc_idx]),
                xytext=(10, -20), textcoords='offset points', 
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.8),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', lw=2))
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, '02_accuracy.png'), dpi=300, bbox_inches='tight')
    print(f"✓ Gráfico de Acurácia salvo em: {save_dir}/02_accuracy.png")
    plt.close()


def plot_iou(metrics_tracker, save_dir='./metrics'):
    """
    Cria gráfico individual de IoU
    """
    os.makedirs(save_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(metrics_tracker.epochs, metrics_tracker.mious, 'r-', linewidth=2.5, marker='^', markersize=5)
    ax.set_xlabel('Época', fontsize=13, fontweight='bold')
    ax.set_ylabel('mIoU (%)', fontsize=13, fontweight='bold')
    ax.set_title('Evolução do IoU (Intersection over Union) ao Longo do Treinamento', fontsize=15, fontweight='bold')
    ax.set_ylim([0, 1.0])
    ax.grid(True, alpha=0.3)
    ax.set_facecolor('#f0f0f0')
    
    # Anotação do melhor valor
    best_miou_idx = np.argmax(metrics_tracker.mious)
    ax.annotate(f'Max: {metrics_tracker.mious[best_miou_idx]:.4f}', 
                xy=(metrics_tracker.epochs[best_miou_idx], metrics_tracker.mious[best_miou_idx]),
                xytext=(10, -20), textcoords='offset points', 
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightcoral', alpha=0.8),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', lw=2))
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, '03_iou.png'), dpi=300, bbox_inches='tight')
    print(f"✓ Gráfico de IoU salvo em: {save_dir}/03_iou.png")
    plt.close()


def plot_convergence(metrics_tracker, save_dir='./metrics'):
    """
    Cria gráfico individual de Convergência
    """
    os.makedirs(save_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Normalizar para visualização conjunta
    loss_norm = np.array(metrics_tracker.losses) / max(metrics_tracker.losses)
    acc_norm = np.array(metrics_tracker.accuracies)
    miou_norm = np.array(metrics_tracker.mious)
    
    ax.plot(metrics_tracker.epochs, loss_norm, 'b-', linewidth=2.5, marker='o', markersize=5, label='Loss (normalizado)', alpha=0.8)
    ax.plot(metrics_tracker.epochs, acc_norm, 'g-', linewidth=2.5, marker='s', markersize=5, label='Acurácia', alpha=0.8)
    ax.plot(metrics_tracker.epochs, miou_norm, 'r-', linewidth=2.5, marker='^', markersize=5, label='mIoU', alpha=0.8)
    
    ax.set_xlabel('Época', fontsize=13, fontweight='bold')
    ax.set_ylabel('Valor (normalizado)', fontsize=13, fontweight='bold')
    ax.set_title('Convergência - Análise Conjunta de Métricas', fontsize=15, fontweight='bold')
    ax.set_ylim([0, 1.1])
    ax.legend(fontsize=12, loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_facecolor('#f0f0f0')
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, '04_convergence.png'), dpi=300, bbox_inches='tight')
    print(f"✓ Gráfico de Convergência salvo em: {save_dir}/04_convergence.png")
    plt.close()


def plot_training_time(training_time, save_dir='./metrics'):
    """
    Cria imagem individual com tempo de treinamento
    """
    os.makedirs(save_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    hours = int(training_time // 3600)
    minutes = int((training_time % 3600) // 60)
    seconds = int(training_time % 60)
    
    ax.text(0.5, 0.6, f'{hours:02d}:{minutes:02d}:{seconds:02d}', 
            ha='center', va='center', fontsize=72, fontweight='bold', color='#1976D2')
    ax.text(0.5, 0.15, 'Tempo Total de Treinamento', 
            ha='center', va='center', fontsize=18, fontweight='bold', color='black')
    ax.axis('off')
    ax.set_facecolor('#e3f2fd')
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, '05_training_time.png'), dpi=300, bbox_inches='tight')
    print(f"✓ Imagem de Tempo de Treinamento salva em: {save_dir}/05_training_time.png")
    plt.close()


def plot_inference_time(metrics_tracker, save_dir='./metrics'):
    """
    Cria imagem individual com tempo de inferência
    """
    os.makedirs(save_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    avg_inference = metrics_tracker.get_avg_inference_time()
    fps = 1000 / avg_inference if avg_inference > 0 else 0
    
    ax.text(0.5, 0.65, f'{avg_inference:.2f} ms', 
            ha='center', va='center', fontsize=60, fontweight='bold', color='#388E3C')
    ax.text(0.5, 0.35, f'{fps:.1f} FPS', 
            ha='center', va='center', fontsize=36, fontweight='bold', color='#2E7D32')
    ax.text(0.5, 0.08, 'Tempo Médio de Inferência', 
            ha='center', va='center', fontsize=16, fontweight='bold', color='black')
    ax.axis('off')
    ax.set_facecolor('#e8f5e9')
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, '06_inference_time.png'), dpi=300, bbox_inches='tight')
    print(f"✓ Imagem de Tempo de Inferência salva em: {save_dir}/06_inference_time.png")
    plt.close()


def plot_best_iou(metrics_tracker, save_dir='./metrics'):
    """
    Cria imagem individual com melhor IoU
    """
    os.makedirs(save_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    best_miou = max(metrics_tracker.mious)
    best_miou_idx = np.argmax(metrics_tracker.mious)
    best_epoch = metrics_tracker.epochs[best_miou_idx]
    
    ax.text(0.5, 0.65, f'{best_miou*100:.2f}%', 
            ha='center', va='center', fontsize=72, fontweight='bold', color='#D32F2F')
    ax.text(0.5, 0.35, f'Época {best_epoch + 1}', 
            ha='center', va='center', fontsize=36, fontweight='bold', color='#B71C1C')
    ax.text(0.5, 0.08, 'Melhor mIoU (Intersection over Union)', 
            ha='center', va='center', fontsize=16, fontweight='bold', color='black')
    ax.axis('off')
    ax.set_facecolor('#ffebee')
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, '07_best_iou.png'), dpi=300, bbox_inches='tight')
    print(f"✓ Imagem de Melhor IoU salva em: {save_dir}/07_best_iou.png")
    plt.close()


def plot_best_accuracy(metrics_tracker, save_dir='./metrics'):
    """
    Cria imagem individual com melhor acurácia
    """
    os.makedirs(save_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    best_acc = max(metrics_tracker.accuracies)
    best_acc_idx = np.argmax(metrics_tracker.accuracies)
    best_epoch = metrics_tracker.epochs[best_acc_idx]
    
    ax.text(0.5, 0.65, f'{best_acc*100:.2f}%', 
            ha='center', va='center', fontsize=72, fontweight='bold', color='#7B1FA2')
    ax.text(0.5, 0.35, f'Época {best_epoch + 1}', 
            ha='center', va='center', fontsize=36, fontweight='bold', color='#6A1B9A')
    ax.text(0.5, 0.08, 'Melhor Acurácia (Pixel-wise)', 
            ha='center', va='center', fontsize=16, fontweight='bold', color='black')
    ax.axis('off')
    ax.set_facecolor('#f3e5f5')
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, '08_best_accuracy.png'), dpi=300, bbox_inches='tight')
    print(f"✓ Imagem de Melhor Acurácia salva em: {save_dir}/08_best_accuracy.png")
    plt.close()


def print_metrics_report(metrics_tracker, training_time):
    """
    Imprime um relatório detalhado das métricas
    """
    print("\n" + "="*70)
    print("RELATÓRIO FINAL DE TREINAMENTO".center(70))
    print("="*70)
    
    # Tempo de treinamento
    hours = int(training_time // 3600)
    minutes = int((training_time % 3600) // 60)
    seconds = int(training_time % 60)
    print(f"\n⏱️  TEMPO DE TREINAMENTO:")
    print(f"   Total: {hours:02d}:{minutes:02d}:{seconds:02d}")
    
    # Métricas finais
    print(f"\n📊 MÉTRICAS FINAIS (Última Época):")
    print(f"   Loss:      {metrics_tracker.losses[-1]:.6f}")
    print(f"   Acurácia:  {metrics_tracker.accuracies[-1]*100:.2f}%")
    print(f"   mIoU:      {metrics_tracker.mious[-1]*100:.2f}%")
    
    # Melhores métricas
    best_loss_idx = np.argmin(metrics_tracker.losses)
    best_acc_idx = np.argmax(metrics_tracker.accuracies)
    best_miou_idx = np.argmax(metrics_tracker.mious)
    
    print(f"\n🏆 MELHORES MÉTRICAS:")
    print(f"   Melhor Loss:     {metrics_tracker.losses[best_loss_idx]:.6f} (Época {metrics_tracker.epochs[best_loss_idx]+1})")
    print(f"   Melhor Acurácia: {metrics_tracker.accuracies[best_acc_idx]*100:.2f}% (Época {metrics_tracker.epochs[best_acc_idx]+1})")
    print(f"   Melhor mIoU:     {metrics_tracker.mious[best_miou_idx]*100:.2f}% (Época {metrics_tracker.epochs[best_miou_idx]+1})")
    
    # Tempo de inferência
    avg_inference = metrics_tracker.get_avg_inference_time()
    print(f"\n⚡ TEMPO DE INFERÊNCIA:")
    print(f"   Tempo Médio: {avg_inference:.2f} ms")
    print(f"   FPS Estimado: {1000/avg_inference:.1f} fps (assumindo CPU/GPU único)")
    
    # Progresso
    loss_improvement = ((metrics_tracker.losses[0] - metrics_tracker.losses[-1]) / metrics_tracker.losses[0]) * 100
    acc_improvement = ((metrics_tracker.accuracies[-1] - metrics_tracker.accuracies[0]) / metrics_tracker.accuracies[0]) * 100 if metrics_tracker.accuracies[0] > 0 else 0
    
    print(f"\n📈 PROGRESSO:")
    print(f"   Redução de Loss: {loss_improvement:.2f}%")
    print(f"   Melhoria de Acurácia: {acc_improvement:.2f}%")
    
    print("\n" + "="*70 + "\n")


# =========================
# CONFIGURAÇÃO
# =========================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Usando dispositivo: {device}")

model = DeepLabV3Plus(num_classes=2).to(device)

class_weights = torch.tensor([1.0, 9.0]).to(device)
criterion = nn.CrossEntropyLoss(weight=class_weights)

optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

train_dataset = OffRoadDataset('data/dataset/train', img_transform, filter_freiburg=True)
train_loader = DataLoader(train_dataset, batch_size=4, shuffle=True, num_workers=0)

print(f"Total de imagens de treino: {len(train_dataset)}")

# Inicializar tracker de métricas
metrics_tracker = MetricsTracker()


# =========================
# LOOP DE TREINO
# =========================
def train_one_epoch(loader):
    """
    Treina uma época e retorna loss médio, acurácia e mIoU.
    """
    model.train()
    total_loss = 0.0
    total_acc = 0.0
    total_miou = 0.0
    num_batches = 0

    for batch_idx, (images, masks) in enumerate(loader):
        images = images.to(device)
        masks = masks.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, masks)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

        # Calcular métricas
        preds = torch.argmax(outputs, dim=1)
        acc, miou, _ = calculate_metrics(preds, masks, num_classes=2)
        total_acc += acc
        total_miou += miou
        num_batches += 1

        if (batch_idx + 1) % 10 == 0:
            print(f"  Batch {batch_idx+1}/{len(loader)} — Loss: {loss.item():.4f} | Acc: {acc:.2%} | mIoU: {miou:.4f}")

    # Retornar médias
    avg_loss = total_loss / len(loader)
    avg_acc = total_acc / num_batches
    avg_miou = total_miou / num_batches

    return avg_loss, avg_acc, avg_miou


# =========================
# TREINAMENTO COM RASTREAMENTO
# =========================
num_epochs = 80
best_miou = 0.0

metrics_tracker.start_training()

for epoch in range(num_epochs):
    print(f"\nÉpoca {epoch+1}/{num_epochs}")
    avg_loss, avg_acc, avg_miou = train_one_epoch(train_loader)
    print(f"  Loss: {avg_loss:.4f} | Acurácia: {avg_acc:.2%} | mIoU: {avg_miou:.4f}")
    
    # Adicionar ao tracker
    metrics_tracker.add_epoch(epoch, avg_loss, avg_acc, avg_miou)

    if avg_miou > best_miou:
        best_miou = avg_miou
        torch.save(model.state_dict(), 'DeepLabV3.pth')
        print(f"  ✓ Melhor modelo salvo! (mIoU: {best_miou:.4f})")

metrics_tracker.end_training()

print(f"\nTreino finalizado. Melhor mIoU: {best_miou:.4f}")


# =========================
# MEDIR TEMPO DE INFERÊNCIA
# =========================
print("\n--- Medindo tempo de inferência ---")
model.load_state_dict(torch.load('DeepLabV3.pth', map_location=device))
model.eval()

inference_times = []
num_test_samples = min(50, len(train_dataset))

with torch.no_grad():
    for idx in range(num_test_samples):
        image, _ = train_dataset[idx]
        image = image.unsqueeze(0).to(device)
        
        start_time = time.time()
        _ = model(image)
        end_time = time.time()
        
        inference_time_ms = (end_time - start_time) * 1000
        metrics_tracker.add_inference_time(inference_time_ms)
        inference_times.append(inference_time_ms)

avg_inference_time = np.mean(inference_times)
print(f"Tempo médio de inferência: {avg_inference_time:.2f} ms")
print(f"FPS estimado: {1000/avg_inference_time:.1f}")


# =========================
# GERAR GRÁFICOS
# =========================
print("\n--- Gerando gráficos ---")
plot_loss(metrics_tracker)
plot_accuracy(metrics_tracker)
plot_iou(metrics_tracker)
plot_convergence(metrics_tracker)
plot_training_time(metrics_tracker.get_total_training_time())
plot_inference_time(metrics_tracker)
plot_best_iou(metrics_tracker)
plot_best_accuracy(metrics_tracker)
print_metrics_report(metrics_tracker, metrics_tracker.get_total_training_time())


# =========================
# DIAGNÓSTICO
# =========================
print("\n--- Diagnóstico ---")

total_via = 0
total_pixels = 0
for _, mask in train_dataset:
    total_via += mask.sum().item()
    total_pixels += mask.numel()
pct_via = 100 * total_via / total_pixels
print(f"Gabarito — via: {pct_via:.1f}%  |  não-via: {100 - pct_via:.1f}%")

with torch.no_grad():
    images, _ = next(iter(DataLoader(train_dataset, batch_size=8, shuffle=False)))
    outputs = model(images.to(device))
    preds = torch.argmax(outputs, dim=1).cpu()
    pct_pred = 100 * preds.sum().item() / preds.numel()
    print(f"Predição  — via: {pct_pred:.1f}%  |  não-via: {100 - pct_pred:.1f}%")

with torch.no_grad():
    images, _ = next(iter(DataLoader(train_dataset, batch_size=1, shuffle=False)))
    output = model(images.to(device))
    print(f"Logit classe 0 (não-via) — média: {output[0,0].mean().item():.4f}")
    print(f"Logit classe 1 (via)     — média: {output[0,1].mean().item():.4f}")

print("-------------------\n")


# =========================
# INFERÊNCIA E SALVAMENTO
# =========================
output_dir = 'data/dataset/train/mask'
os.makedirs(output_dir, exist_ok=True)

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

print(f"✓ {global_idx} imagens segmentadas salvas em: {output_dir}")
print("\n✓ Treinamento completo! Verifique a pasta './metrics' para os gráficos.")