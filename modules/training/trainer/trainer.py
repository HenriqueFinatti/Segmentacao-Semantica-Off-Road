import os
import gc
import torch
import numpy as np
import torch.nn as nn

from torch.utils.data import DataLoader

from configs import paths
from configs.settings import Settings

from modules.training.dataset.off_road_dataset import OffRoadDataset

from modules.models.registry import build_model, model_name as validate_model_name
from modules.segmentation.transforms import build_image_transform
from modules.training.earlyStopping.early_stopping import EarlyStopping

from modules.metrics.chart import Charts
from modules.metrics.metrics_tracker import MetricsTracker


class Trainer():
    def __init__(self, model: str):
        self.current_model = model.upper()
        self.metrics_tracker = MetricsTracker(self.current_model)
        self.settings = Settings()
        self.charts = Charts()
        self.early_stopping = EarlyStopping()

        self.batch_size = self.settings.get_batch_size()

        print(f"Batch size: {self.batch_size}")
        self.EPOCHS = self.settings.get_epochs()

        img_transform = build_image_transform()

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.class_weights = torch.tensor(self.settings.get_class_weights()).to(self.device)
        self.criterion = nn.CrossEntropyLoss(weight=self.class_weights)

        self.train_dataset = OffRoadDataset(paths.dataset_dir('train'), img_transform)

        use_cuda = torch.cuda.is_available()
        self.train_loader = DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.settings.get_num_workers(),
            pin_memory=use_cuda,
        )

        model_name = validate_model_name(model)
        self.model = build_model(model_name).to(self.device)
        self.final_model_path = paths.model_path(model_name)

        os.makedirs(os.path.dirname(self.final_model_path), exist_ok=True)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.settings.get_learning_rate())

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

        gc.collect()
        if torch.cuda.is_available():
            print(f"Uso de memória da GPU: {torch.cuda.memory_allocated() / (1024 ** 2):.2f} MB")
            torch.cuda.empty_cache()

        self.metrics_tracker.end_epoch(epoch_num)
        self.early_stopping(self.metrics_tracker.avg_miou)


    def train_model(self):

        self.metrics_tracker.start_training(self.get_configuration())
        for epoch in range(self.EPOCHS):
            epoch_num = epoch + 1

            self.train_one_epoch(self.train_loader, epoch_num)
            self.save_best_model()

            if self.settings.is_test_execution_on() and epoch_num == self.settings.get_test_execution_epochs():
                break

            if self.early_stopping.should_stop:
                break

        self.metrics_tracker.end_training()
        self.charts.plot_charts(self.metrics_tracker, self.current_model)


    def get_configuration(self):
        settings = self.settings
        datasets = [
            name for name, is_on in [
                ('Freiburg Forest', settings.is_freiburg_forest_on()),
                ('Synthetic Offroad', settings.is_synthetic_off_road_on()),
            ] if is_on
        ]
        test_execution = (
            f"Sim ({settings.get_test_execution_images()} imagens, {settings.get_test_execution_epochs()} épocas)"
            if settings.is_test_execution_on() else "Não"
        )
        early_stopping = (
            f"Sim (paciência {settings.get_patience()})" if settings.is_early_stopping_on() else "Não"
        )

        return {
            'Modelo': self.current_model,
            'Dispositivo': torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
            'Execução de Teste': test_execution,
            'Datasets': ', '.join(datasets),
            'Imagens de Treino': len(self.train_dataset),
            'Tamanho da Imagem': f"{settings.get_image_size()}x{settings.get_image_size()}",
            'Batch Size': self.batch_size,
            'Épocas (máximo)': self.EPOCHS,
            'Early Stopping': early_stopping,
            'Learning Rate': settings.get_learning_rate(),
            'Pesos das Classes': settings.get_class_weights(),
            'Num Workers': settings.get_num_workers(),
            'Otimizador': type(self.optimizer).__name__,
        }


    def save_best_model(self):
        if self.metrics_tracker.is_best:
            torch.save(self.model.state_dict(), self.final_model_path)