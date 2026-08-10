import torch
import numpy as np
import time
from configs.settings import Settings
GREEN = "\033[92m"
RESET = "\033[0m"

class MetricsTracker:
    def __init__(self):
        self.settings = Settings()
        self.total_loss = 0.0
        self.total_acc = 0.0
        self.total_miou = 0.0
        self.best_miou = 0.0
        
        self.num_batches = 0
        self.start_epoch_time = 0
        self.training_start_time = 0
        self.total_training_time = 0

        self.epochs = []
        self.losses = []
        self.accuracies = []
        self.mious = []
        pass

    def calculate_pixel_accuracy(self, preds, masks):
        with torch.no_grad():
            correct = (preds == masks).sum().item()
            total = masks.numel()
            acc = correct / total
        return acc

    def calculate_mean_iou(self, preds, masks, num_classes=2):
        with torch.no_grad():
            iou_list = []
            for cls in range(num_classes):
                intersection = ((preds == cls) & (masks == cls)).sum().item()
                union = ((preds == cls) | (masks == cls)).sum().item()
                
                if union == 0:
                    iou_list.append(float('nan'))
                else:
                    iou_list.append(intersection / union)
            
            miou = np.nanmean(iou_list)
        return miou
    
    def update_metrics(self, loss, outputs, masks):
        self.total_loss += loss
        
        preds = torch.argmax(outputs, dim=1)
        
        self.total_acc += self.calculate_pixel_accuracy(preds, masks)
        self.total_miou += self.calculate_mean_iou(preds, masks, num_classes=2)
        self.num_batches += 1

    def add_epoch(self, epoch, duration):
        mins, secs = divmod(duration, 60)

        avg_loss, avg_acc, avg_miou = self.calculate_avg()
    
        self.epochs.append(epoch)
        self.losses.append(avg_loss)
        self.accuracies.append(avg_acc)
        self.mious.append(avg_miou)

        epoch_header = self.build_epoch_header(avg_miou, epoch)
        
        print(f"\n{epoch_header}")
        print(f"Loss: {avg_loss:.4f} | Acurácia: {avg_acc:.2%} | mIoU: {avg_miou:.4f} | Tempo de Treino: {int(mins)}m {secs:.2f}s")

        self.reset_values(avg_miou)

    def calculate_avg(self):
        avg_loss = self.total_loss / self.num_batches
        avg_acc = self.total_acc / self.num_batches
        avg_miou = self.total_miou / self.num_batches

        return avg_loss, avg_acc, avg_miou
    
    def reset_values(self, avg_miou):
        self.avg_miou = avg_miou
        self.total_loss = 0.0
        self.total_acc = 0.0
        self.total_miou = 0.0
        self.num_batches = 0

    def build_epoch_header(self, avg_miou, epoch_num):
        self.is_best = avg_miou > self.best_miou

        if self.is_best:
            self.best_miou = avg_miou
            return f"{GREEN}Época {epoch_num}{RESET}"

        return f"Época {epoch_num}"

    def start_epoch(self):
        self.start_epoch_time = time.time()

    def end_epoch(self, epoch_num):
        duration = time.time() - self.start_epoch_time
        self.add_epoch(epoch_num, duration)

    def start_training(self):
        self.training_start_time = time.time()
    
    def end_training(self):
        self.total_training_time = time.time() - self.training_start_time
        total_mins, total_secs = divmod(self.total_training_time, 60)

        print(f"\n==========================")
        print(f"Tempo total de treinamento: {int(total_mins)}m {total_secs:.2f}s")
        print(f"Melhor mIoU alcançado: {self.best_miou:.4f}")
        print(f"==========================")
