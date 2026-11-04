import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from configs.settings import Settings

settings = Settings()

class Charts:
    def __init__(self):
        pass

    def plot_charts(self, metrics_tracker, current_model):

        save_dir = self.get_result_path(current_model.upper())
        os.makedirs(save_dir, exist_ok=True)

        if settings.is_charts_on():
            self.plot_loss(metrics_tracker, save_dir)
            self.plot_accuracy(metrics_tracker, save_dir)
            self.plot_iou(metrics_tracker, save_dir)
            self.plot_convergence(metrics_tracker, save_dir)
            self.plot_training_time(metrics_tracker.total_training_time, save_dir)
            self.plot_best_iou(metrics_tracker, save_dir)
            self.plot_best_accuracy(metrics_tracker, save_dir)


    def plot_loss(self, metrics_tracker, save_dir):
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(metrics_tracker.epochs, metrics_tracker.losses, 'b-', linewidth=2.5, marker='o', markersize=5)
        ax.set_xlabel('Época', fontsize=13, fontweight='bold')
        ax.set_ylabel('Loss', fontsize=13, fontweight='bold')
        ax.set_title('Evolução do Loss ao Longo do Treinamento', fontsize=15, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#f0f0f0')
        
        best_loss_idx = np.argmin(metrics_tracker.losses)
        ax.annotate(f'Min: {metrics_tracker.losses[best_loss_idx]:.4f}', 
                        xy=(metrics_tracker.epochs[best_loss_idx], metrics_tracker.losses[best_loss_idx]),
                        xytext=(10, 10), textcoords='offset points', 
                        bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', lw=2))
        
        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, '01_loss.png'), dpi=300, bbox_inches='tight')
        plt.close()


    def plot_accuracy(self, metrics_tracker, save_dir):
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
        plt.close()


    def plot_iou(self, metrics_tracker, save_dir):
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
        plt.close()


    def plot_convergence(self, metrics_tracker, save_dir):
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
        plt.close()


    def plot_training_time(self, training_time, save_dir):
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
        plt.close()


    def plot_best_iou(self, metrics_tracker, save_dir):
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
        plt.close()


    def plot_best_accuracy(self, metrics_tracker, save_dir):
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
        plt.close()


    def plot_inference_times(self, result, model, context):
        if not settings.is_charts_on():
            return

        save_dir = self.get_result_path(model.upper())
        os.makedirs(save_dir, exist_ok=True)

        times = list(result['inference_times'].values())
        stats = result['inference_stats']
        frames = range(1, len(times) + 1)

        fig, (ax_line, ax_hist) = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={'width_ratios': [2, 1]})

        ax_line.plot(frames, times, 'b-', linewidth=1, alpha=0.8)
        ax_line.axhline(stats['mean'], color='r', linestyle='--', linewidth=2, label=f"Média: {stats['mean']:.2f} ms ({stats['fps']:.1f} FPS)")
        ax_line.axhline(stats['p95'], color='orange', linestyle=':', linewidth=2, label=f"P95: {stats['p95']:.2f} ms")
        ax_line.set_xlabel('Frame', fontsize=13, fontweight='bold')
        ax_line.set_ylabel('Tempo de Inferência (ms)', fontsize=13, fontweight='bold')
        ax_line.set_title(f'Tempo de Inferência por Frame - {model.upper()}', fontsize=15, fontweight='bold')
        ax_line.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax_line.legend(fontsize=11, loc='best')
        ax_line.grid(True, alpha=0.3)
        ax_line.set_facecolor('#f0f0f0')

        ax_hist.hist(times, bins=30, color='#1976D2', edgecolor='white')
        ax_hist.axvline(stats['mean'], color='r', linestyle='--', linewidth=2)
        ax_hist.set_xlabel('Tempo de Inferência (ms)', fontsize=13, fontweight='bold')
        ax_hist.set_ylabel('Frames', fontsize=13, fontweight='bold')
        ax_hist.set_title('Distribuição', fontsize=15, fontweight='bold')
        ax_hist.grid(True, alpha=0.3)
        ax_hist.set_facecolor('#f0f0f0')

        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, f'09_tempo_inferencia_{context}.png'), dpi=300, bbox_inches='tight')
        plt.close()


    def plot_inference_comparison(self, results, context):
        if not settings.is_charts_on():
            return

        save_dir = os.path.join('results', 'comparacao')
        os.makedirs(save_dir, exist_ok=True)

        models = [model.upper() for model in results]
        means = [result['inference_stats']['mean'] for result in results.values()]
        stds = [result['inference_stats']['std'] for result in results.values()]
        fps = [result['inference_stats']['fps'] for result in results.values()]

        fig, ax = plt.subplots(figsize=(10, 6))

        bars = ax.bar(models, means, yerr=stds, capsize=10, color=['#1976D2', '#D32F2F'][:len(models)], alpha=0.85)
        for bar, mean, model_fps in zip(bars, means, fps):
            ax.annotate(f'{mean:.2f} ms\n{model_fps:.1f} FPS',
                        xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 15), textcoords='offset points', ha='center',
                        fontsize=12, fontweight='bold')

        ax.set_ylabel('Tempo Médio de Inferência (ms)', fontsize=13, fontweight='bold')
        ax.set_title('Comparação do Tempo de Inferência por Frame', fontsize=15, fontweight='bold')
        ax.set_ylim([0, max(m + s for m, s in zip(means, stds)) * 1.35])
        ax.grid(True, axis='y', alpha=0.3)
        ax.set_facecolor('#f0f0f0')

        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, f'tempo_inferencia_{context}.png'), dpi=300, bbox_inches='tight')
        plt.close()


    def get_result_path(self, model):
        if model == 'FCN':
            return 'results/fcn/images'
        
        if model == 'DEEPLABV3+':
            return 'results/deeplabv3+/images'