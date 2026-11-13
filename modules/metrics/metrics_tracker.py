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

        # Uma entrada por época com as métricas de validação (vazio quando não há validação)
        self.validation = []
        self.selection_miou = 0.0
        self.best_epoch = None


    @property
    def has_validation(self):
        return len(self.validation) > 0


    def validation_values(self, key):
        return [epoch[key] for epoch in self.validation]


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


    def add_epoch(self, epoch, duration, validation=None):
        mins, secs = divmod(duration, 60)

        avg_loss, avg_acc, avg_miou = self.calculate_avg()
    
        self.epochs.append(epoch)
        self.losses.append(avg_loss)
        self.accuracies.append(avg_acc)
        self.mious.append(avg_miou)

        # O melhor modelo e o early stopping usam o mIoU de validação; sem validação, o de treino
        if validation is not None:
            self.validation.append(validation)
            self.selection_miou = validation['miou']
        else:
            self.selection_miou = avg_miou

        epoch_header = self.build_epoch_header(self.selection_miou, epoch)
        train_line = f"Treino    | Loss: {avg_loss:.4f} | Acurácia: {avg_acc:.2%} | mIoU: {avg_miou:.4f} | Tempo da Época: {int(mins)}m {secs:.2f}s"

        print(f"{epoch_header}")
        print(train_line)

        self.write_message(f"\n{epoch_header}")
        self.write_message(train_line)

        if validation is not None:
            validation_line = (f"Validação | Loss: {validation['loss']:.4f} | Acurácia: {validation['acuracia']:.2%} | "
                               f"mIoU: {validation['miou']:.4f} | IoU Trilha: {validation['iou_trilha']:.4f} | F1: {validation['f1']:.4f}")
            print(validation_line)
            self.write_message(validation_line)

        self.write_message("")
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
            self.best_epoch = epoch_num

        model = f"{BLUE}{self.current_model}{RESET}"

        if self.is_best:
            epoch = f"{GREEN}Época {epoch_num}{RESET}"
        else:
            epoch = f"Época {epoch_num}"

        return f"{model}: {epoch}"


    def start_epoch(self):
        self.start_epoch_time = time.time()


    def end_epoch(self, epoch_num, validation=None):
        duration = time.time() - self.start_epoch_time
        self.add_epoch(epoch_num, duration, validation)


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
        print("-" * 59)
        print(f"{'Métrica':<16} | {'Melhor':<10} | {'Média':<10} | {'Final':<10}")
        print("-" * 59)
        print(f"{'Loss':<16} | {min_loss:<10.4f} | {mean_loss:<10.4f} | {final_loss:<10.4f}")
        print(f"{'Acurácia':<16} | {max_acc:<10.2%} | {mean_acc:<10.2%} | {final_acc:<10.2%}")
        print(f"{'mIoU':<16} | {max_miou:<10.4f} | {mean_miou:<10.4f} | {final_miou:<10.4f}")

        validation_rows = self.build_validation_rows()
        for name, best, mean, final, fmt in validation_rows:
            print(f"{name:<16} | {best:<10{fmt}} | {mean:<10{fmt}} | {final:<10{fmt}}")

        print(f"{BLUE}======================================================={RESET}")
        print(self.best_epoch_message())

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

        for name, best, mean, final, fmt in validation_rows:
            self.write_message(f"| **{name}** | {best:{fmt}} | {mean:{fmt}} | {final:{fmt}} |")

        self.write_message(f"\n{self.best_epoch_message()}")

        if self.has_validation:
            self.write_message("\n*Treino: média do mIoU de cada batch. Validação: mIoU da matriz de confusão de todo o "
                               "conjunto, como na avaliação do teste.*")


    def build_validation_rows(self):
        if not self.has_validation:
            return []

        rows = []
        for key, name, fmt, lower_is_better in [
            ('loss', 'Loss Val.', '.4f', True),
            ('acuracia', 'Acurácia Val.', '.2%', False),
            ('miou', 'mIoU Val.', '.4f', False),
            ('iou_trilha', 'IoU Trilha Val.', '.4f', False),
            ('f1', 'F1 Val.', '.4f', False),
        ]:
            values = np.array(self.validation_values(key), dtype=np.float64)
            best = np.nanmin(values) if lower_is_better else np.nanmax(values)
            rows.append((name, best, np.nanmean(values), values[-1], fmt))

        return rows


    def best_epoch_message(self):
        source = 'mIoU de validação' if self.has_validation else 'mIoU de treino (sem validação)'
        return f"Modelo salvo: época {self.best_epoch}, escolhida pelo {source} ({self.best_miou:.4f})."


    def get_result_path(self):
        return os.path.join(paths.statistics_dir(self.current_model.lower()), 'stats.md')