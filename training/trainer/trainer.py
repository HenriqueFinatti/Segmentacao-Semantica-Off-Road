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
from .model.deeplabv3 import DeepLabV3Plus

from configs.settings import Settings
from metrics import MetricsTracker, Charts


class Trainer():
    def __init__(self, model):
        self.metrics_tracker = MetricsTracker()
        self.settings = Settings()
        self.charts = Charts()
        self.early_stopping = EarlyStopping()

        self.EPOCHS = self.settings.get_epochs()

        img_transform = transforms.Compose([
            transforms.Resize((512, 512)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                std=[0.229, 0.224, 0.225]),
        ])

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.class_weights = torch.tensor([1.0, 9.0]).to(self.device)
        self.criterion = nn.CrossEntropyLoss(weight=self.class_weights)
        self.train_dataset = OffRoadDataset('data/dataset/train', img_transform)
        self.train_loader = DataLoader(self.train_dataset, batch_size=4, shuffle=True, num_workers=0)

        if model.upper() == 'FCN':
            self.model = FCN(num_classes=2).to(self.device)
            self.final_model_path = os.path.join("results", "fcn", "model.pth")
            self.output_dir = os.path.join("data", "dataset", "train", "new_segmentation", "fcn")
        else:
            self.model = DeepLabV3Plus(num_classes=2).to(self.device)
            self.final_model_path = os.path.join("results", "deeplabv3+", "model.pth")
            self.output_dir = os.path.join("data", "dataset", "train", "new_segmentation", "deeplabv3+")

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.final_model_path), exist_ok=True) 
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-4)
        
        print(f"Total de imagens de treino: {len(self.train_dataset)}")

    def train_one_epoch(self, loader, epoch_num):
        self.model.train()

        self.metrics_tracker.start_epoch()
        for batch_idx, (images, masks) in enumerate(loader):
            images = images.to(self.device)
            masks = masks.to(self.device)

            self.optimizer.zero_grad()
            outputs = self.model(images)
            loss = self.criterion(outputs, masks)
            loss.backward()
            self.optimizer.step()

            self.metrics_tracker.update_metrics(loss.item(), outputs, masks)
            
        self.metrics_tracker.end_epoch(epoch_num)
        self.early_stopping(self.metrics_tracker.avg_miou)


    def train_model(self):

        self.metrics_tracker.start_training()
        for epoch in range(self.EPOCHS):
            epoch_num = epoch + 1
            
            self.train_one_epoch(self.train_loader, epoch_num)
            self.save_best_model()
            
            if self.early_stopping.should_stop:
                break
            
        self.metrics_tracker.end_training()


    def save_best_model(self):
        if self.metrics_tracker.is_best:
            torch.save(self.model.state_dict(), self.final_model_path)


    def save_results(self):
        infer_loader = DataLoader(self.train_dataset, batch_size=4, shuffle=False, num_workers=0)
        global_idx = 0

        with torch.no_grad():
            for images, _ in infer_loader:
                images = images.to(self.device)
                outputs = self.model(images)
                preds = torch.argmax(outputs, dim=1).cpu().numpy()

                for i in range(preds.shape[0]):
                    img_name = self.train_dataset.images[global_idx]
                    base_name = os.path.splitext(img_name)[0]
                    output_path = os.path.join(self.output_dir, base_name + ".png")

                    # via = branco (255), não-via = preto (0)
                    pred_img = Image.fromarray((preds[i] * 255).astype(np.uint8))
                    pred_img.save(output_path)

                    global_idx += 1