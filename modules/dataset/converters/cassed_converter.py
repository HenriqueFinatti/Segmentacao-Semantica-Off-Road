import os
import csv
import shutil
from collections import Counter, namedtuple

from PIL import Image

from configs import paths

PREFIX = 'CaSSeD'

# Cada trilha do CaSSeD nomeia o par imagem/rótulo de um jeito:
#   Main_Trail   screenshot_rgba_0001.png -> rgba_0001.png
#   Brown_field  image0000.png            -> rgb0000.png
#   demais       mesmo nome (timestamp) nas duas pastas
Trail = namedtuple('Trail', ['images', 'annotations', 'annotation_name'])

TRAILS = {
    'Main_Trail': Trail('raw_images', 'annotations', lambda name: name.replace('screenshot_', '', 1)),
    'Brown_field': Trail('raw_images', 'annotations', lambda name: name.replace('image', 'rgb', 1)),
    'NorthFarm': Trail('raw_images', 'annotations', lambda name: name),
    'Powerline': Trail('raw_images', 'annotations', lambda name: name),
    'Fogdata': Trail('raw_images', 'annotations', lambda name: name),
}

Pair = namedtuple('Pair', ['trail', 'image', 'annotation'])

MANIFEST_COLUMNS = ['arquivo', 'split', 'trilha', 'imagem_original', 'rotulo_original']


class CaSSeDConverter():
    """Copia as imagens reais do CaSSeD para dataset/<split>/original e os rótulos coloridos para
    dataset/<split>/original_segmentation, os dois com o mesmo nome CaSSeD_<n>.

    O split é por trilha (CaSSeD_Test_Trails no settings.json): quadros vizinhos de uma gravação são quase
    iguais, então dividir ao acaso colocaria praticamente a mesma imagem no treino e no teste."""

    def __init__(self, settings):
        self.test_trails = set(settings.get_cassed_test_trails())

        unknown = self.test_trails - set(TRAILS)
        if unknown:
            raise ValueError(f"Trilha(s) desconhecida(s) em CaSSeD_Test_Trails: {', '.join(sorted(unknown))}. "
                             f"Trilhas do CaSSeD: {', '.join(TRAILS)}.")


    def convert(self):
        # Confere todos os pares antes de copiar qualquer arquivo, para não deixar o dataset pela metade
        pairs = self.collect_pairs()
        self.remove_previous_files()

        rows = []
        for index, pair in enumerate(pairs):
            split = 'test' if pair.trail in self.test_trails else 'train'
            new_name = f"{PREFIX}_{index}"

            self.move(pair.image, paths.dataset_dir(split, 'original'), new_name)
            self.move(pair.annotation, paths.dataset_dir(split, 'original_segmentation'), new_name)

            rows.append({
                'arquivo': new_name,
                'split': split,
                'trilha': pair.trail,
                'imagem_original': os.path.basename(pair.image),
                'rotulo_original': os.path.basename(pair.annotation),
            })

        self.save_manifest(rows)
        self.print_summary(rows)
        return rows


    def collect_pairs(self):
        pairs = []
        problems = []

        # Ordem fixa (trilhas na ordem de TRAILS, arquivos em ordem alfabética): a numeração é sempre a mesma
        for trail_name, trail in TRAILS.items():
            trail_dir = os.path.join(paths.CASSED_RAW_DIR, 'Real_World_data', trail_name)
            images_dir = os.path.join(trail_dir, trail.images)
            annotations_dir = os.path.join(trail_dir, trail.annotations)

            if not os.path.isdir(images_dir) or not os.path.isdir(annotations_dir):
                problems.append(f"pasta ausente: {paths.relative(trail_dir)}/{{{trail.images},{trail.annotations}}}")
                continue

            for image_name in sorted(os.listdir(images_dir)):
                image_path = os.path.join(images_dir, image_name)
                annotation_path = os.path.join(annotations_dir, trail.annotation_name(image_name))

                if not os.path.isfile(image_path):
                    continue

                if not os.path.isfile(annotation_path):
                    problems.append(f"{trail_name}/{image_name}: rótulo {os.path.basename(annotation_path)} não encontrado")
                    continue

                # Só lê o cabeçalho das imagens, não os pixels
                with Image.open(image_path) as image, Image.open(annotation_path) as annotation:
                    if image.size != annotation.size:
                        problems.append(f"{trail_name}/{image_name}: imagem {image.size} e rótulo {annotation.size} com tamanhos diferentes")
                        continue

                pairs.append(Pair(trail_name, image_path, annotation_path))

        if problems:
            shown = '\n  - '.join(problems[:10]) + ('\n  ...' if len(problems) > 10 else '')
            raise ValueError(f"CaSSeD com {len(problems)} problema(s), nada foi copiado:\n  - {shown}")

        if not pairs:
            raise ValueError(f"Nenhuma imagem do CaSSeD encontrada em {paths.relative(paths.CASSED_RAW_DIR)}.")

        return pairs


    def remove_previous_files(self):
        # Rodar de novo substitui a conversão anterior em vez de duplicar imagens com outra numeração
        for split in ['train', 'test']:
            for folder in ['original', 'original_segmentation', 'mask']:
                folder_path = paths.dataset_dir(split, folder)
                if not os.path.isdir(folder_path):
                    continue

                for file in os.listdir(folder_path):
                    if file.startswith(f"{PREFIX}_"):
                        os.unlink(paths.ensure_inside_root(os.path.join(folder_path, file)))


    def move(self, source, destination_dir, new_name):
        extension = os.path.splitext(source)[1].lower()
        # Cópia: raw/ guarda o dataset bruto para remontar sem baixar de novo
        shutil.copy2(source, os.path.join(destination_dir, new_name + extension))


    def save_manifest(self, rows):
        os.makedirs(os.path.dirname(paths.CASSED_SOURCE_FILE), exist_ok=True)

        with open(paths.CASSED_SOURCE_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)


    def print_summary(self, rows):
        per_trail = Counter((row['split'], row['trilha']) for row in rows)
        per_split = Counter(row['split'] for row in rows)

        print(f"CaSSeD: {len(rows)} imagens (treino {per_split['train']}, teste {per_split['test']})")
        for (split, trail), count in sorted(per_trail.items()):
            print(f"  {split:<5} {trail:<12} {count}")
        print(f"Origem de cada imagem salva em: {paths.relative(paths.CASSED_SOURCE_FILE)}")
