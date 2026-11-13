import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from PIL import Image

from configs import paths

# Abaixo disso a cor/tolerância do settings.json provavelmente não bate com o dataset
MIN_EXPECTED_TRAIL_PCT = 1.0

class MaskGenerator:

    def __init__(self, settings):
        self.dataset_labels = settings.get_dataset_labels()
        self.class_weights = settings.get_class_weights()


    def get_prefix_config(self, filename):
        for prefix, config in self.dataset_labels.items():
            if filename.startswith(prefix):
                return prefix, config

        return None, None


    def generate_binary_mask(self, gt_color_path, output_path, config):
        target_color = config["color"]
        tolerance = config["tolerance"]

        img = Image.open(gt_color_path).convert("RGB")
        data = np.array(img, dtype=np.uint8)

        lower = np.clip(target_color.astype(int) - tolerance, 0, 255).astype(np.uint8)
        upper = np.clip(target_color.astype(int) + tolerance, 0, 255).astype(np.uint8)

        is_target = np.all((data >= lower) & (data <= upper), axis=-1)

        mask = np.zeros(is_target.shape, dtype=np.uint8)
        mask[is_target] = 1

        Image.fromarray(mask).save(output_path)

        return 100 * mask.sum() / mask.size


    def _process_image(self, source_folder, dest_folder, image_name):
        prefix, config = self.get_prefix_config(image_name)
        if config is None:
            return None, None

        src = os.path.join(source_folder, image_name)
        dst = os.path.join(
            dest_folder,
            os.path.splitext(image_name)[0] + ".png"
        )

        pct = self.generate_binary_mask(src, dst, config)
        return prefix, pct


    def generate_masks(self):
        splits = ["test", "train"]
        summary = {}

        for split in splits:
            source_folder = paths.dataset_dir(split, 'original_segmentation')
            dest_folder = paths.dataset_dir(split, 'mask')

            os.makedirs(dest_folder, exist_ok=True)

            images = sorted(os.listdir(source_folder))

            results = {prefix: [] for prefix in self.dataset_labels.keys()}
            skipped = []

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(self._process_image, source_folder, dest_folder, img): img
                    for img in images
                }

                for future in as_completed(futures):
                    prefix, pct = future.result()
                    if prefix is None:
                        skipped.append(futures[future])
                    else:
                        results[prefix].append(pct)

            summary[split] = {'results': results, 'skipped': sorted(skipped)}

        lines = self.build_report(summary)
        print('\n'.join(lines))
        self.save_report(lines)
        self.warn_about_problems(summary)


    def build_report(self, summary):
        lines = [
            "### Máscaras Geradas\n",
            f"**Data:** {datetime.now():%Y-%m-%d %H:%M:%S}\n",
            "Porcentagem de pixels marcados como trilha em cada máscara (média por imagem).\n",
            "| Split | Dataset | Máscaras | Trilha Média | Mínimo | Máximo | Sem Trilha |",
            "|-------|---------|----------|--------------|--------|--------|------------|",
        ]

        for split, data in summary.items():
            for prefix, values in data['results'].items():
                if not values:
                    continue

                no_trail = sum(1 for value in values if value == 0)
                lines.append(
                    f"| {split} | {prefix} | {len(values)} | {np.mean(values):.1f}% | "
                    f"{np.min(values):.1f}% | {np.max(values):.1f}% | {no_trail} |"
                )

        train_values = [value for values in summary['train']['results'].values() for value in values]
        if train_values:
            # Proporção fundo/trilha no treino, para comparar com os pesos usados na loss
            trail = np.mean(train_values)
            ratio = (100 - trail) / trail if trail > 0 else float('inf')
            lines += [
                "",
                f"**Treino:** {trail:.1f}% de trilha, proporção fundo/trilha de {ratio:.1f} : 1 "
                f"(Class_Weights atual: {self.class_weights}).",
            ]

        for split, data in summary.items():
            skipped = data['skipped']
            if skipped:
                shown = ', '.join(skipped[:10]) + (' ...' if len(skipped) > 10 else '')
                lines += ["", f"**Ignorados em {split}** ({len(skipped)}, sem prefixo de dataset conhecido): {shown}"]

        return lines


    def save_report(self, lines):
        os.makedirs(os.path.dirname(paths.DATASET_REPORT_FILE), exist_ok=True)

        with open(paths.DATASET_REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')

        print(f"\nRelatório das máscaras salvo em: {paths.relative(paths.DATASET_REPORT_FILE)}")


    def warn_about_problems(self, summary):
        for split, data in summary.items():
            for prefix, values in data['results'].items():
                if not values:
                    continue

                no_trail = sum(1 for value in values if value == 0)

                # Uma cor errada ainda pode casar com alguns pixels soltos, então 0% exato não basta
                if np.mean(values) < MIN_EXPECTED_TRAIL_PCT:
                    print(f"\n[AVISO] {prefix} ({split}) tem só {np.mean(values):.1f}% de trilha em média. "
                          f"Confira 'color' e 'tolerance' de {prefix} no settings.json.")
                elif no_trail:
                    print(f"\n[AVISO] {no_trail} máscara(s) de {prefix} ({split}) sem nenhum pixel de trilha.")
