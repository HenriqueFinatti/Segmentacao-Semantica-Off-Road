import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from configs import paths

class Charts:
    def __init__(self, settings):
        self.settings = settings

    def plot_charts(self, metrics_tracker, current_model, save_dir=None):

        save_dir = save_dir or self.get_result_path(current_model.upper())
        os.makedirs(save_dir, exist_ok=True)

        if self.settings.is_charts_on():
            self.plot_loss(metrics_tracker, save_dir)
            self.plot_accuracy(metrics_tracker, save_dir)
            self.plot_iou(metrics_tracker, save_dir)
            self.plot_convergence(metrics_tracker, save_dir)
            self.plot_training_time(metrics_tracker.total_training_time, save_dir)
            self.plot_best_iou(metrics_tracker, save_dir)
            self.plot_best_accuracy(metrics_tracker, save_dir)


    def plot_validation_line(self, ax, metrics_tracker, key):
        # Curva de validação junto da de treino; a distância entre as duas mostra overfitting
        if not metrics_tracker.has_validation:
            return

        ax.plot(metrics_tracker.epochs, metrics_tracker.validation_values(key), color='#FF8F00', linestyle='--',
                linewidth=2.5, marker='D', markersize=5, label='Validação')
        ax.legend(fontsize=12, loc='best')


    def plot_loss(self, metrics_tracker, save_dir):
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(metrics_tracker.epochs, metrics_tracker.losses, 'b-', linewidth=2.5, marker='o', markersize=5, label='Treino')
        self.plot_validation_line(ax, metrics_tracker, 'loss')
        ax.set_xlabel('Época', fontsize=13, fontweight='bold')
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
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
        
        ax.plot(metrics_tracker.epochs, metrics_tracker.accuracies, 'c-', linewidth=2.5, marker='s', markersize=5, label='Treino')
        self.plot_validation_line(ax, metrics_tracker, 'acuracia')
        ax.set_xlabel('Época', fontsize=13, fontweight='bold')
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
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
        
        ax.plot(metrics_tracker.epochs, metrics_tracker.mious, 'r-', linewidth=2.5, marker='^', markersize=5, label='Treino')
        self.plot_validation_line(ax, metrics_tracker, 'miou')
        ax.set_xlabel('Época', fontsize=13, fontweight='bold')
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_ylabel('mIoU', fontsize=13, fontweight='bold')
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
        if metrics_tracker.has_validation:
            ax.plot(metrics_tracker.epochs, metrics_tracker.validation_values('miou'), color='#FF8F00', linestyle='--',
                    linewidth=2.5, marker='D', markersize=5, label='mIoU (validação)', alpha=0.8)
        
        ax.set_xlabel('Época', fontsize=13, fontweight='bold')
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
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
        
        # Com validação, mostra o mIoU que escolheu o modelo salvo
        mious = metrics_tracker.validation_values('miou') if metrics_tracker.has_validation else metrics_tracker.mious
        best_miou_idx = int(np.nanargmax(mious))
        best_miou = mious[best_miou_idx]
        best_epoch = metrics_tracker.epochs[best_miou_idx]
        title = 'Melhor mIoU de Validação' if metrics_tracker.has_validation else 'Melhor mIoU de Treino'
        
        ax.text(0.5, 0.65, f'{best_miou*100:.2f}%', 
                ha='center', va='center', fontsize=72, fontweight='bold', color='#D32F2F')
        ax.text(0.5, 0.35, f'Época {best_epoch}', 
                ha='center', va='center', fontsize=36, fontweight='bold', color='#B71C1C')
        ax.text(0.5, 0.08, title, 
                ha='center', va='center', fontsize=16, fontweight='bold', color='black')
        ax.axis('off')
        ax.set_facecolor('#ffebee')
        
        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, '07_best_iou.png'), dpi=300, bbox_inches='tight')
        plt.close()


    def plot_best_accuracy(self, metrics_tracker, save_dir):
        fig, ax = plt.subplots(figsize=(10, 6))

        accuracies = metrics_tracker.validation_values('acuracia') if metrics_tracker.has_validation else metrics_tracker.accuracies
        best_acc_idx = int(np.nanargmax(accuracies))
        best_acc = accuracies[best_acc_idx]
        best_epoch = metrics_tracker.epochs[best_acc_idx]
        title = 'Melhor Acurácia de Validação (Pixel-wise)' if metrics_tracker.has_validation else 'Melhor Acurácia de Treino (Pixel-wise)'

        ax.text(0.5, 0.65, f'{best_acc*100:.2f}%', 
                ha='center', va='center', fontsize=72, fontweight='bold', color='#7B1FA2')
        ax.text(0.5, 0.35, f'Época {best_epoch}', 
                ha='center', va='center', fontsize=36, fontweight='bold', color='#6A1B9A')
        ax.text(0.5, 0.08, title, 
                ha='center', va='center', fontsize=16, fontweight='bold', color='black')
        ax.axis('off')
        ax.set_facecolor('#f3e5f5')

        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, '08_best_accuracy.png'), dpi=300, bbox_inches='tight')
        plt.close()


    def plot_inference_times(self, result, model, context):
        if not self.settings.is_charts_on():
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
        if not self.settings.is_charts_on():
            return

        save_dir = paths.COMPARISON_DIR
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


    def plot_confusion_matrix(self, evaluation, model):
        if not self.settings.is_charts_on():
            return

        save_dir = self.get_result_path(model)
        os.makedirs(save_dir, exist_ok=True)

        total = evaluation['groups']['Todos']
        counts = np.array([[total['tp'], total['fn']], [total['fp'], total['tn']]], dtype=np.float64)
        # Normalizado por linha: cada linha mostra para onde foram os pixels de uma classe real
        rows = counts.sum(axis=1, keepdims=True)
        normalized = np.divide(counts, rows, out=np.zeros_like(counts), where=rows > 0)

        fig, ax = plt.subplots(figsize=(8, 7))
        image = ax.imshow(normalized, cmap='Blues', vmin=0, vmax=1)
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)

        labels = ['Trilha', 'Fundo']
        ax.set_xticks([0, 1], labels=labels, fontsize=12)
        ax.set_yticks([0, 1], labels=labels, fontsize=12)
        ax.set_xlabel('Previsto', fontsize=13, fontweight='bold')
        ax.set_ylabel('Real', fontsize=13, fontweight='bold')
        ax.set_title(f'Matriz de Confusão no Teste - {model.upper()}', fontsize=15, fontweight='bold')

        for row in range(2):
            for column in range(2):
                color = 'white' if normalized[row, column] > 0.5 else 'black'
                ax.text(column, row, f'{normalized[row, column]:.1%}\n{int(counts[row, column]):,} px',
                        ha='center', va='center', fontsize=13, fontweight='bold', color=color)

        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, '10_matriz_confusao_teste.png'), dpi=300, bbox_inches='tight')
        plt.close()


    def plot_test_comparison(self, evaluations):
        if not self.settings.is_charts_on():
            return

        save_dir = paths.COMPARISON_DIR
        os.makedirs(save_dir, exist_ok=True)

        metrics = [('acuracia', 'Acurácia'), ('miou', 'mIoU'), ('iou_trilha', 'IoU Trilha'),
                   ('precisao', 'Precisão'), ('recall', 'Recall'), ('f1', 'F1')]
        colors = ['#1976D2', '#D32F2F', '#388E3C', '#7B1FA2']
        positions = np.arange(len(metrics))
        width = 0.8 / len(evaluations)

        fig, ax = plt.subplots(figsize=(12, 6))

        for index, (model, evaluation) in enumerate(evaluations.items()):
            values = [np.nan_to_num(evaluation['groups']['Todos'][key]) for key, _ in metrics]
            bars = ax.bar(positions + (index - (len(evaluations) - 1) / 2) * width, values, width,
                          label=model.upper(), color=colors[index % len(colors)], alpha=0.85)
            for bar, value in zip(bars, values):
                ax.annotate(f'{value:.1%}', xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                            xytext=(0, 4), textcoords='offset points', ha='center', fontsize=9, fontweight='bold')

        ax.set_xticks(positions, labels=[label for _, label in metrics], fontsize=12)
        ax.set_ylabel('Valor (0 a 1)', fontsize=13, fontweight='bold')
        ax.set_title('Comparação no Dataset de Teste', fontsize=15, fontweight='bold')
        ax.set_ylim([0, 1.1])
        ax.legend(fontsize=12, loc='upper right')
        ax.grid(True, axis='y', alpha=0.3)
        ax.set_facecolor('#f0f0f0')

        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, 'avaliacao_teste.png'), dpi=300, bbox_inches='tight')
        plt.close()


    def get_result_path(self, model):
        return paths.charts_dir(model.lower())