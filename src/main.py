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
from models.early_stopping import EarlyStopping
from metrics.statistics import Statistics
EPOCHS = 200
stats_calculator = Statistics()

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

def train_one_epoch(loader):
    model.train()
    start_time = time.time()
    
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
        
        preds = torch.argmax(outputs, dim=1)
        
        acc = stats_calculator.calculate_pixel_accuracy(preds, masks)
        miou = stats_calculator.calculate_mean_iou(preds, masks, num_classes=2)
        
        total_acc += acc
        total_miou += miou
        num_batches += 1

    end_time = time.time()
    epoch_duration = end_time - start_time

    avg_loss = total_loss / num_batches
    avg_acc = total_acc / num_batches
    avg_miou = total_miou / num_batches

    return avg_loss, avg_acc, avg_miou, epoch_duration

def train_model():
    total_train_start = time.time()
    best_miou = 0.0
    early_stopping = EarlyStopping(patience=10)
    GREEN = "\033[92m"
    RESET = "\033[0m"

    for epoch in range(EPOCHS):
        epoch_num = epoch + 1
        
        avg_loss, avg_acc, avg_miou, duration = train_one_epoch(train_loader)
        
        is_best = avg_miou > best_miou
        if is_best:
            best_miou = avg_miou
            path = "results\deeplabv3+\model.pth"
            torch.save(model.state_dict(), path)

        if is_best:
            epoch_header = f"{GREEN}Época {epoch_num}/{EPOCHS}{RESET}"
        else:
            epoch_header = f"Época {epoch_num}/{EPOCHS}"

        mins, secs = divmod(duration, 60)
        print(f"\n{epoch_header}")
        print(f"Loss: {avg_loss:.4f} | Acurácia: {avg_acc:.2%} | mIoU: {avg_miou:.4f} | Tempo de Treino: {int(mins)}m {secs:.2f}s")
        
        early_stopping(avg_miou)
        if early_stopping.should_stop:
            break
        
    total_train_end = time.time()
    total_duration = total_train_end - total_train_start
    total_mins, total_secs = divmod(total_duration, 60)

    print(f"\n==========================")
    print(f"Tempo total de treinamento: {int(total_mins)}m {total_secs:.2f}s")
    print(f"Melhor mIoU alcançado: {best_miou:.4f}")
    print(f"==========================")

def save_results():
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

if __name__ == "__main__":
    train_model()
    save_results()