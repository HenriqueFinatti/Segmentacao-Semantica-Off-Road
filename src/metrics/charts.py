import os
import numpy as np
import matplotlib.pyplot as plt
from entities.settings import Settings

settings = Settings()
def plot_charts(metrics_tracker, save_dir):
    if settings.isChartsOn():
        plot_loss(metrics_tracker, save_dir)
        plot_accuracy(metrics_tracker, save_dir)
        plot_iou(metrics_tracker, save_dir)
        plot_convergence(metrics_tracker, save_dir)
        plot_training_time(metrics_tracker.total_training_time, save_dir)
        plot_best_iou(metrics_tracker, save_dir)
        plot_best_accuracy(metrics_tracker, save_dir)

def plot_loss(metrics_tracker, save_dir):
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(metrics_tracker.epochs, metrics_tracker.losses, 'b-', linewidth=2.5, marker='o', markersize=5)
        ax.set_xlabel('Época', fontsize=13, fontweight='bold')
        ax.set_ylabel('Loss', fontsize=13, fontweight='bold')
        ax.set_title('Evolução do Loss ao Longo do Treinamento', fontsize=15, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#f0f0f0')
        
        # Anotação do melhor valor
        best_loss_idx = np.argmin(metrics_tracker.losses)
        ax.annotate(f'Min: {metrics_tracker.losses[best_loss_idx]:.4f}', 
                        xy=(metrics_tracker.epochs[best_loss_idx], metrics_tracker.losses[best_loss_idx]),
                        xytext=(10, 10), textcoords='offset points', 
                        bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', lw=2))
        
        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, '01_loss.png'), dpi=300, bbox_inches='tight')
        plt.close()

def plot_accuracy(metrics_tracker, save_dir):
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

def plot_iou(metrics_tracker, save_dir):
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

def plot_convergence(metrics_tracker, save_dir):
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

def plot_training_time(training_time, save_dir):
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

def plot_best_iou(metrics_tracker, save_dir):
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

def plot_best_accuracy(metrics_tracker, save_dir):
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