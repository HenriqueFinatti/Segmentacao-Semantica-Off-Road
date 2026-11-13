import os
import re
import time
import torch
import numpy as np

from configs import paths

BLUE = "\033[94m"
GREEN = "\033[92m"
RESET = "\033[0m"

class MetricsTracker:
    def __init__(self, current_model):
        self.current_model = current_model

        self.results_path = self.get_result_path()
        os.makedirs(os.path.dirname(self.results_path), exist_ok=True)

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


    def write_message(self, message):
        clean_message = re.sub(r'\033\[[0-9;]*m', '', message)

        with open(self.results_path, 'a', encoding='utf-8') as f:
            f.write(clean_message + "\n")


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
        
        print(f"{epoch_header}")
        print(f"Loss: {avg_loss:.4f} | Acurácia: {avg_acc:.2%} | mIoU: {avg_miou:.4f} | Tempo de Treino: {int(mins)}m {secs:.2f}s")

        self.write_message(f"\n{epoch_header}")
        self.write_message(f"Loss: {avg_loss:.4f} | Acurácia: {avg_acc:.2%} | mIoU: {avg_miou:.4f} | Tempo de Treino: {int(mins)}m {secs:.2f}s\n")

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

        model = f"{BLUE}{self.current_model}{RESET}"

        if self.is_best:
            epoch = f"{GREEN}Época {epoch_num}{RESET}"
        else:
            epoch = f"Época {epoch_num}"

        return f"{model}: {epoch}"


    def start_epoch(self):
        self.start_epoch_time = time.time()


    def end_epoch(self, epoch_num):
        duration = time.time() - self.start_epoch_time
        self.add_epoch(epoch_num, duration)


    def start_training(self, configuration):
        # Registra com quais configurações o resultado foi gerado
        lines = [
            "### Configuração do Treinamento\n",
            "| Parâmetro | Valor |",
            "|-----------|-------|",
            *[f"| {name} | {value} |" for name, value in configuration.items()],
            "",
            "### Épocas",
        ]

        with open(self.results_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        self.training_start_time = time.time()
  
    
    def end_training(self):
        self.total_training_time = time.time() - self.training_start_time
        total_mins, total_secs = divmod(self.total_training_time, 60)
        
        total_epochs = len(self.epochs)
        
        avg_time_per_epoch = self.total_training_time / total_epochs
        avg_mins, avg_secs = divmod(avg_time_per_epoch, 60)
        
        min_loss, mean_loss, final_loss = min(self.losses), np.mean(self.losses), self.losses[-1]
        max_acc, mean_acc, final_acc = max(self.accuracies), np.mean(self.accuracies), self.accuracies[-1]
        max_miou, mean_miou, final_miou = max(self.mious), np.mean(self.mious), self.mious[-1]

        print(f"\n{BLUE}==========| RESULTADOS FINAIS: {self.current_model.upper()} |=========={RESET}")
        print(f"Total de Épocas: {total_epochs}")
        print(f"Tempo Total: {int(total_mins)}m {total_secs:.2f}s (Média/época: {int(avg_mins)}m {avg_secs:.2f}s)")
        print("-" * 55)
        print(f"{'Métrica':<12} | {'Melhor':<10} | {'Média':<10} | {'Final':<10}")
        print("-" * 55)
        print(f"{'Loss':<12} | {min_loss:<10.4f} | {mean_loss:<10.4f} | {final_loss:<10.4f}")
        print(f"{'Acurácia':<12} | {max_acc:<10.2%} | {mean_acc:<10.2%} | {final_acc:<10.2%}")
        print(f"{'mIoU':<12} | {max_miou:<10.4f} | {mean_miou:<10.4f} | {final_miou:<10.4f}")
        print(f"{BLUE}======================================================={RESET}")

        self.write_message(f"\n### Resultados Finais {self.current_model.upper()}")
        self.write_message("---")
        
        self.write_message("\n#### Resumo de Tempo e Épocas")
        self.write_message(f"- **Total de Épocas:** {total_epochs}")
        self.write_message(f"- **Tempo Total:** {int(total_mins)}m {int(total_secs)}s")
        self.write_message(f"- **Tempo Médio por Época:** {int(avg_mins)}m {int(avg_secs)}s")
        
        self.write_message("\n#### Tabela de Métricas")
        self.write_message("| Métrica | Melhor | Média | Final (Última) |")
        self.write_message("|---|---|---|---|")
        self.write_message(f"| **Loss** | {min_loss:.4f} | {mean_loss:.4f} | {final_loss:.4f} |")
        self.write_message(f"| **Acurácia** | {max_acc:.2%} | {mean_acc:.2%} | {final_acc:.2%} |")
        self.write_message(f"| **mIoU** | {max_miou:.4f} | {mean_miou:.4f} | {final_miou:.4f} |")


    def get_result_path(self):
        return os.path.join(paths.statistics_dir(self.current_model.lower()), 'stats.md')