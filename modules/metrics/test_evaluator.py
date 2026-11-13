import os
import csv
from datetime import datetime

import numpy as np
from PIL import Image

from configs import paths
from modules.models.registry import MODELS
from modules.metrics.segmentation_metrics import compute_metrics, confusion_counts, divide

BLUE = "\033[94m"
RESET = "\033[0m"

ALL_DATASETS = 'Todos'
WORST_IMAGES = 5


class TestEvaluator:
    """Compara as predições salvas em dataset/test/new_segmentation/<modelo> com as máscaras reais
    de dataset/test/mask, pixel a pixel, e soma a matriz de confusão de todo o dataset de teste.
    A classe positiva é a trilha."""

    def __init__(self, settings, charts):
        self.dataset_names = list(settings.get_dataset_labels().keys())
        self.charts = charts
        self.masks_dir = paths.dataset_dir('test', 'mask')


    def evaluate_all_models(self, model_names=None):
        print("\nAvaliando as predições no dataset de teste...")
        evaluations = {}

        for model_name in model_names or MODELS:
            predictions_dir = os.path.join(paths.TEST_SEGMENTATION_DIR, model_name)

            if not os.path.isdir(predictions_dir):
                print(f"Pulando {model_name.upper()}: sem predições em {paths.relative(predictions_dir)}. Segmente o dataset de teste antes.")
                continue

            evaluation = self.evaluate_model(model_name, predictions_dir)
            if evaluation is None:
                continue

            self.print_summary(evaluation)
            self.save_report(evaluation)
            self.save_csv(evaluation)
            self.charts.plot_confusion_matrix(evaluation, model_name)
            evaluations[model_name] = evaluation

        if not evaluations:
            raise FileNotFoundError("Nenhuma predição do dataset de teste encontrada para avaliar.")

        if len(evaluations) > 1:
            self.charts.plot_test_comparison(evaluations)

        self.print_paths(evaluations)
        return evaluations


    def evaluate_model(self, model_name, predictions_dir):
        mask_files = sorted(f for f in os.listdir(self.masks_dir) if f.endswith('.png'))
        totals = {}
        images = []
        missing = []
        resized = 0

        for mask_file in mask_files:
            prediction_path = os.path.join(predictions_dir, mask_file)

            if not os.path.exists(prediction_path):
                missing.append(mask_file)
                continue

            truth = np.array(Image.open(os.path.join(self.masks_dir, mask_file))) > 0
            prediction_image = Image.open(prediction_path)

            # Predições antigas ficaram em 512x512; a máscara real manda no tamanho
            if prediction_image.size != (truth.shape[1], truth.shape[0]):
                prediction_image = prediction_image.resize((truth.shape[1], truth.shape[0]), Image.NEAREST)
                resized += 1

            prediction = np.array(prediction_image.convert('L')) > 0
            counts = self.confusion(prediction, truth)
            dataset = self.dataset_of(mask_file)

            images.append({'imagem': mask_file, 'dataset': dataset, **counts, **self.compute_metrics(counts)})

            for group in [dataset, ALL_DATASETS]:
                group_totals = totals.setdefault(group, {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 0, 'images': 0})
                for key, value in counts.items():
                    group_totals[key] += value
                group_totals['images'] += 1

        if missing:
            print(f"[AVISO] {model_name.upper()}: {len(missing)} máscara(s) sem predição correspondente, ignoradas.")
        if resized:
            print(f"[AVISO] {model_name.upper()}: {resized} predição(ões) em tamanho diferente da máscara foram redimensionadas. Segmente o teste de novo.")

        if not images:
            print(f"Pulando {model_name.upper()}: nenhuma predição corresponde às máscaras de {paths.relative(self.masks_dir)}.")
            return None

        groups = {group: {**counts, **self.compute_metrics(counts)} for group, counts in totals.items()}

        return {
            'model': model_name,
            'groups': groups,
            'images': images,
            'missing': missing,
        }


    def confusion(self, prediction, truth):
        return confusion_counts(prediction, truth)


    def compute_metrics(self, counts):
        return compute_metrics(counts)


    def divide(self, numerator, denominator):
        return divide(numerator, denominator)


    def dataset_of(self, filename):
        for name in self.dataset_names:
            if filename.startswith(name):
                return name
        return 'Outro'


    def ordered_groups(self, evaluation):
        groups = evaluation['groups']
        return [g for g in self.dataset_names if g in groups] + [g for g in groups if g not in self.dataset_names and g != ALL_DATASETS] + [ALL_DATASETS]


    def format_pct(self, value):
        return '-' if np.isnan(value) else f"{value:.2%}"


    def print_summary(self, evaluation):
        print(f"\n{BLUE}{evaluation['model'].upper()}{RESET}: avaliação no dataset de teste")
        print(f"{'Dataset':<20} | {'Imagens':>7} | {'Acurácia':>9} | {'mIoU':>8} | {'IoU Trilha':>10} | {'Precisão':>9} | {'Recall':>8} | {'F1':>8}")
        print("-" * 101)

        for group in self.ordered_groups(evaluation):
            m = evaluation['groups'][group]
            print(f"{group:<20} | {m['images']:>7} | {self.format_pct(m['acuracia']):>9} | {self.format_pct(m['miou']):>8} | "
                  f"{self.format_pct(m['iou_trilha']):>10} | {self.format_pct(m['precisao']):>9} | "
                  f"{self.format_pct(m['recall']):>8} | {self.format_pct(m['f1']):>8}")


    def get_report_path(self, model_name):
        return os.path.join(paths.statistics_dir(model_name), 'avaliacao_teste.md')


    def get_csv_path(self, model_name):
        return os.path.join(paths.statistics_dir(model_name), 'avaliacao_teste_por_imagem.csv')


    def save_report(self, evaluation):
        model_name = evaluation['model']
        report_path = self.get_report_path(model_name)
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        lines = [
            f"### Avaliação no Dataset de Teste - {model_name.upper()}\n",
            f"**Data:** {datetime.now():%Y-%m-%d %H:%M:%S}\n",
            "Predições comparadas pixel a pixel com as máscaras reais, no tamanho original das imagens. "
            "A matriz de confusão é somada em todo o conjunto e as métricas são calculadas a partir dela. "
            "A classe positiva é a trilha.\n",
            "#### Métricas\n",
            "| Dataset | Imagens | Acurácia | mIoU | IoU Trilha | IoU Fundo | Precisão | Recall | F1 |",
            "|---------|---------|----------|------|------------|-----------|----------|--------|----|",
        ]

        for group in self.ordered_groups(evaluation):
            m = evaluation['groups'][group]
            lines.append(
                f"| {group} | {m['images']} | {self.format_pct(m['acuracia'])} | {self.format_pct(m['miou'])} | "
                f"{self.format_pct(m['iou_trilha'])} | {self.format_pct(m['iou_fundo'])} | "
                f"{self.format_pct(m['precisao'])} | {self.format_pct(m['recall'])} | {self.format_pct(m['f1'])} |"
            )

        total = evaluation['groups'][ALL_DATASETS]
        trail_pixels = total['tp'] + total['fn']
        background_pixels = total['tn'] + total['fp']

        lines += [
            "",
            "#### Matriz de Confusão (todos os datasets)\n",
            "Linhas: classe real. Colunas: classe prevista. Entre parênteses, a fração da linha.\n",
            "| Real \\ Previsto | Trilha | Fundo |",
            "|-----------------|--------|-------|",
            f"| Trilha | {total['tp']:,} ({self.format_pct(self.divide(total['tp'], trail_pixels))}) | "
            f"{total['fn']:,} ({self.format_pct(self.divide(total['fn'], trail_pixels))}) |",
            f"| Fundo | {total['fp']:,} ({self.format_pct(self.divide(total['fp'], background_pixels))}) | "
            f"{total['tn']:,} ({self.format_pct(self.divide(total['tn'], background_pixels))}) |",
            "",
            f"#### {WORST_IMAGES} Piores Imagens (IoU da Trilha)\n",
            "| Imagem | Dataset | IoU Trilha | Precisão | Recall |",
            "|--------|---------|------------|----------|--------|",
        ]

        worst = sorted(evaluation['images'], key=lambda image: np.nan_to_num(image['iou_trilha'], nan=-1))[:WORST_IMAGES]
        for image in worst:
            lines.append(
                f"| {image['imagem']} | {image['dataset']} | {self.format_pct(image['iou_trilha'])} | "
                f"{self.format_pct(image['precisao'])} | {self.format_pct(image['recall'])} |"
            )

        lines += [
            "",
            "*O mIoU do treino (stats.md) é a média do mIoU de cada batch; aqui ele vem da matriz de confusão "
            "de todo o conjunto, que é a forma padrão. Os dois não são diretamente comparáveis.*",
            "",
            f"Métricas por imagem: `{paths.relative(self.get_csv_path(model_name))}`",
        ]

        if evaluation['missing']:
            lines.append(f"\n**Máscaras sem predição (ignoradas):** {len(evaluation['missing'])}")

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')


    def save_csv(self, evaluation):
        csv_path = self.get_csv_path(evaluation['model'])
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

        columns = ['imagem', 'dataset', 'tp', 'fp', 'fn', 'tn', 'acuracia', 'iou_trilha', 'iou_fundo', 'miou', 'precisao', 'recall', 'f1']

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()

            for image in evaluation['images']:
                writer.writerow({
                    key: (f"{value:.6f}" if isinstance(value, float) else value)
                    for key, value in image.items()
                })


    def print_paths(self, evaluations):
        print("\nAvaliação salva em:")
        for model_name in evaluations:
            print(f"  - {paths.relative(self.get_report_path(model_name))}")
            print(f"  - {paths.relative(self.get_csv_path(model_name))}")
