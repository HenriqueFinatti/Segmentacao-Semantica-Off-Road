import os
import torch
import numpy as np
import torch.nn as nn

from PIL import Image
from torchvision import transforms
from torch.utils.data import DataLoader

from ..dataset import OffRoadDataset
from ..earlyStopping import EarlyStopping
from .model.fcn import FCN 

from configs.settings import Settings
from metrics import MetricsTracker, Charts

settings = Settings()
charts = Charts()
early_stopping = EarlyStopping()

EPOCHS = settings.get_epochs()

img_transform = transforms.Compose([
    transforms.Resize((512, 512)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = FCN(num_classes=2).to(device)
class_weights = torch.tensor([1.0, 9.0]).to(device)
criterion = nn.CrossEntropyLoss(weight=class_weights)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
train_dataset = OffRoadDataset('data/dataset/train', img_transform)
train_loader = DataLoader(train_dataset, batch_size=4, shuffle=True, num_workers=0)

print(f"Total de imagens de treino: {len(train_dataset)}")

# 3. Alterando o nome da classe do treinador
class FCNTrainer():
    def __init__(self):
        self.metrics_tracker = MetricsTracker()
        pass
        
    def train_one_epoch(self, loader, epoch_num):
        model.train()

        self.metrics_tracker.start_epoch()
        for batch_idx, (images, masks) in enumerate(loader):
            images = images.to(device)
            masks = masks.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, masks)
            loss.backward()
            optimizer.step()

            self.metrics_tracker.update_metrics(loss.item(), outputs, masks)
            
        self.metrics_tracker.end_epoch(epoch_num)
        early_stopping(self.metrics_tracker.avg_miou)


    def train_model(self):

        self.metrics_tracker.start_training()
        for epoch in range(EPOCHS):
            epoch_num = epoch + 1
            
            self.train_one_epoch(train_loader, epoch_num)
            self.save_best_model()
            
            if early_stopping.should_stop:
                break
            
        self.metrics_tracker.end_training()


    def save_best_model(self):
        if self.metrics_tracker.is_best:
            # 4. Alterando a pasta de destino para "fcn"
            path = os.path.join("results", "fcn", "model.pth")
            
            # Garante que a pasta 'results/fcn' exista antes de salvar
            os.makedirs(os.path.dirname(path), exist_ok=True) 
            
            torch.save(model.state_dict(), path)


    def save_results(self):
        # 5. Alterando o diretório de inferência para "fcn"
        output_dir = 'data/dataset/train/new_segmentation/fcn'
        
        # Garante que a pasta de resultados da inferência exista
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