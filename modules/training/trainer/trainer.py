import os
import gc
import torch
import numpy as np
import torch.nn as nn

from torch.utils.data import DataLoader

from configs import paths

from modules.training.dataset.off_road_dataset import OffRoadDataset
from modules.training.dataset.split import split_train_validation
from modules.metrics.segmentation_metrics import add_counts, compute_metrics, confusion_counts_torch

from modules.models.registry import build_model, model_name as validate_model_name
from modules.segmentation.transforms import build_image_transform
from modules.training.earlyStopping.early_stopping import EarlyStopping

from modules.metrics.chart import Charts
from modules.metrics.metrics_tracker import MetricsTracker


class Trainer():
    def __init__(self, model: str, settings, output_dir=None, on_epoch=None):
        """output_dir: pasta da configuração (model.pth, statistics/ e images/). Sem ela, usa results/<modelo>/.
        on_epoch: chamado ao fim de cada época com as métricas, para a interface acompanhar o treino."""
        self.current_model = model.upper()
        self.output_dir = output_dir
        self.on_epoch = on_epoch
        self.statistics_dir = os.path.join(output_dir, 'statistics') if output_dir else paths.statistics_dir(model.lower())
        self.charts_dir = os.path.join(output_dir, 'images') if output_dir else None
        self.metrics_tracker = MetricsTracker(self.current_model, self.statistics_dir)
        self.settings = settings
        self.charts = Charts(settings)
        self.early_stopping = EarlyStopping(settings)

        self.batch_size = self.settings.get_batch_size()

        print(f"Batch size: {self.batch_size}")
        self.EPOCHS = self.settings.get_epochs()

        img_transform = build_image_transform(self.settings.get_image_size())

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.class_weights = torch.tensor(self.settings.get_class_weights()).to(self.device)
        self.criterion = nn.CrossEntropyLoss(weight=self.class_weights)

        # A validação sai de dentro do treino; o dataset de teste nunca é usado para escolher o modelo
        train_dir = paths.dataset_dir('train')
        all_images = OffRoadDataset(train_dir, self.settings, img_transform).images
        train_images, self.validation_images = split_train_validation(
            all_images, self.settings.get_validation_split(), self.settings.get_seed()
        )

        self.train_dataset = OffRoadDataset(train_dir, self.settings, img_transform, images=train_images)
        self.batch_size = self.check_train_batch_size(len(self.train_dataset))

        use_cuda = torch.cuda.is_available()
        self.train_loader = DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            # Um batch de 1 imagem quebra o BatchNorm do pooling global do ASPP (1 valor por canal).
            # Como o shuffle muda a ordem a cada época, a imagem que sobra não é sempre a mesma.
            drop_last=True,
            num_workers=self.settings.get_num_workers(),
            pin_memory=use_cuda,
        )

        self.validation_loader = None
        if self.validation_images:
            self.validation_dataset = OffRoadDataset(train_dir, self.settings, img_transform, images=self.validation_images)
            self.validation_loader = DataLoader(
                self.validation_dataset,
                batch_size=self.batch_size,
                shuffle=False,
                num_workers=self.settings.get_num_workers(),
                pin_memory=use_cuda,
            )
        else:
            print("[AVISO] Sem validação (Validation_Split = 0): o melhor modelo será escolhido pelo mIoU de treino.")

        model_name = validate_model_name(model)
        self.model = build_model(model_name).to(self.device)
        self.final_model_path = os.path.join(output_dir, 'model.pth') if output_dir else paths.model_path(model_name)

        os.makedirs(os.path.dirname(self.final_model_path), exist_ok=True)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.settings.get_learning_rate())

        print(f"Total de imagens de treino: {len(self.train_dataset)} | validação: {len(self.validation_images)}")

    def check_train_batch_size(self, train_count):
        # O BatchNorm precisa de pelo menos 2 imagens por batch no treino
        if train_count < 2:
            raise ValueError(
                f"Só {train_count} imagem de treino depois de separar a validação; o treino precisa de pelo menos 2 por batch. "
                f"Aumente Test_Execution_Images (mínimo 3: 2 de treino + 1 de validação) ou desligue Test_Execution no settings.json."
            )

        # Com drop_last, um batch maior que o treino não teria nenhum batch completo
        if train_count < self.batch_size:
            print(f"[AVISO] Só {train_count} imagens de treino: batch size reduzido de {self.batch_size} para {train_count}.")
            return train_count

        return self.batch_size


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

        validation = self.validate()

        epoch_metrics = self.metrics_tracker.end_epoch(epoch_num, validation)
        self.early_stopping(self.metrics_tracker.selection_miou)
        return epoch_metrics


    def validate(self):
        if self.validation_loader is None:
            return None

        self.model.eval()
        total_loss = 0.0
        total_images = 0
        counts = {}

        with torch.no_grad():
            for images, masks in self.validation_loader:
                images = images.to(self.device)
                masks = masks.to(self.device)

                outputs = self.model(images)
                total_loss += self.criterion(outputs, masks).item() * images.size(0)
                total_images += images.size(0)

                add_counts(counts, confusion_counts_torch(torch.argmax(outputs, dim=1), masks))

        return {'loss': total_loss / total_images, **compute_metrics(counts)}


    def train_model(self):

        self.metrics_tracker.start_training(self.get_configuration())
        self.save_validation_images()

        # Motivo do término: 'epocas' (chegou ao total), 'early_stopping' ou 'execucao_de_teste'
        reason = 'epocas'
        epoch_num = 0

        for epoch in range(self.EPOCHS):
            epoch_num = epoch + 1

            epoch_metrics = self.train_one_epoch(self.train_loader, epoch_num)
            self.save_best_model()

            if self.on_epoch:
                self.on_epoch({**epoch_metrics, 'total': self.EPOCHS, 'melhor_epoca': self.metrics_tracker.best_epoch})

            if self.settings.is_test_execution_on() and epoch_num == self.settings.get_test_execution_epochs():
                reason = 'execucao_de_teste'
                break

            if self.early_stopping.should_stop:
                reason = 'early_stopping'
                break

        self.metrics_tracker.end_training()
        self.charts.plot_charts(self.metrics_tracker, self.current_model, self.charts_dir)

        return {
            'motivo_termino': reason,
            'epoca_final': epoch_num,
            'melhor_epoca': self.metrics_tracker.best_epoch,
            'tempo_total_s': self.metrics_tracker.total_training_time,
            'modelo': self.final_model_path,
        }


    def get_configuration(self):
        settings = self.settings
        datasets = settings.get_enabled_datasets()
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
            'Imagens de Validação': (
                f"{len(self.validation_images)} ({settings.get_validation_split():.0%} de cada dataset, seed {settings.get_seed()})"
                if self.validation_images else "0 (sem validação)"
            ),
            'Seleção do Modelo': 'mIoU de validação' if self.validation_images else 'mIoU de treino',
            'Tamanho da Imagem': f"{settings.get_image_size()}x{settings.get_image_size()}",
            'Batch Size': self.batch_size,
            'Épocas (máximo)': self.EPOCHS,
            'Early Stopping': early_stopping,
            'Learning Rate': settings.get_learning_rate(),
            'Pesos das Classes': settings.get_class_weights(),
            'Num Workers': settings.get_num_workers(),
            'Otimizador': type(self.optimizer).__name__,
        }


    def save_validation_images(self):
        # Lista das imagens de validação, para saber exatamente com quais imagens o modelo foi escolhido
        os.makedirs(self.statistics_dir, exist_ok=True)
        path = os.path.join(self.statistics_dir, 'validacao_imagens.txt')

        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.validation_images) + ('\n' if self.validation_images else ''))


    def save_best_model(self):
        if self.metrics_tracker.is_best:
            torch.save(self.model.state_dict(), self.final_model_path)