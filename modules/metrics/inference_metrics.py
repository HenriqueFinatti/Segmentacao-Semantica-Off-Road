import os
import csv
import numpy as np

BLUE = "\033[94m"
RESET = "\033[0m"


class InferenceMetrics:
    def __init__(self):
        pass


    def summarize(self, times_ms):
        values = np.array(times_ms, dtype=np.float64)
        mean = values.mean()

        return {
            'mean': mean,
            'median': np.median(values),
            'std': values.std(),
            'min': values.min(),
            'max': values.max(),
            'p95': np.percentile(values, 95),
            'fps': 1000.0 / mean if mean > 0 else 0.0,
        }


    def print_summary(self, result):
        inference = result['inference_stats']
        frame = result['frame_stats']

        print(f"\n{BLUE}{result['model'].upper()}{RESET}: {result['images']} imagens segmentadas")
        print(f"Tempo de inferência: média {inference['mean']:.2f} ms | mediana {inference['median']:.2f} ms | "
              f"desvio {inference['std']:.2f} ms | mín {inference['min']:.2f} ms | máx {inference['max']:.2f} ms | "
              f"P95 {inference['p95']:.2f} ms | {inference['fps']:.1f} FPS")
        print(f"Tempo total por frame (carregar + inferir + salvar): média {frame['mean']:.2f} ms | {frame['fps']:.1f} FPS")


    def build_markdown_table(self, result, on_gpu):
        inference = result['inference_stats']
        frame = result['frame_stats']
        sync_note = " e sincronizado com a GPU" if on_gpu else ""

        return [
            "#### Tempo de Inferência por Frame\n",
            f"Tempo apenas do modelo (forward + argmax), medido com batch 1{sync_note}.\n",
            "| Métrica | Tempo de Inferência | Tempo Total por Frame |",
            "|---------|---------------------|-----------------------|",
            f"| Média | {inference['mean']:.2f} ms | {frame['mean']:.2f} ms |",
            f"| Mediana | {inference['median']:.2f} ms | {frame['median']:.2f} ms |",
            f"| Desvio Padrão | {inference['std']:.2f} ms | {frame['std']:.2f} ms |",
            f"| Mínimo | {inference['min']:.2f} ms | {frame['min']:.2f} ms |",
            f"| Máximo | {inference['max']:.2f} ms | {frame['max']:.2f} ms |",
            f"| P95 | {inference['p95']:.2f} ms | {frame['p95']:.2f} ms |",
            f"| FPS (1000 / média) | {inference['fps']:.1f} | {frame['fps']:.1f} |",
            "",
            "*Tempo Total por Frame inclui carregar e pré-processar a imagem, a inferência e salvar a máscara.*",
        ]


    def save_csv(self, result, csv_path):
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['imagem', 'tempo_inferencia_ms', 'tempo_total_frame_ms'])

            for name in result['inference_times']:
                writer.writerow([
                    name,
                    f"{result['inference_times'][name]:.4f}",
                    f"{result['frame_times'][name]:.4f}",
                ])
