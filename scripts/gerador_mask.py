"""
Script 3 — Gera as máscaras binárias (mask_labels) a partir do GT_color.

Freiburg Forest — cores oficiais das 6 classes:
  Trail      → (170, 170,  170)  ← ESTA é a via que queremos detectar (cinza claro)
  Grass      → (  0, 255,    0)  ← verde puro
  Vegetation → (  0,  60,    0)  ← verde escuro
  Sky        → (  0,   0,  255)  ← azul puro
  Obstacle   → (255,   0,    0)  ← vermelho
  Void       → (  0,   0,    0)  ← preto

Resultado em mask_labels/:
  1 = Trail (via)
  0 = tudo o mais (não-via)
"""

import numpy as np
from PIL import Image
import os
import time

# Cor oficial da classe Trail no Freiburg Forest
TRAIL_COLOR = np.array([170, 170, 170], dtype=np.uint8)

# Tolerância de ±10 por canal para lidar com pequenas variações de compressão PNG
TOLERANCE = 10

def generate_binary_mask(gt_color_path: str, output_path: str):
    """Lê uma imagem GT_color e salva a máscara binária correspondente."""
    img = Image.open(gt_color_path).convert('RGB')
    data = np.array(img, dtype=np.uint8)

    lower = TRAIL_COLOR - TOLERANCE
    upper = TRAIL_COLOR + TOLERANCE

    # Pixels dentro do intervalo de cor da Trail → 1, resto → 0
    is_trail = np.all((data >= lower) & (data <= upper), axis=-1)

    mask = np.zeros(is_trail.shape, dtype=np.uint8)
    mask[is_trail] = 1  # valores 0 e 1 — o dataset lê como long tensor no treino

    Image.fromarray(mask).save(output_path)

def generate_all_masks():
    splits = ['test', 'train']
    total = 0

    for split in splits:
        source_folder = f'./data/dataset/{split}/gt_color'
        dest_folder   = f'./data/dataset/{split}/mask_labels'
        os.makedirs(dest_folder, exist_ok=True)

        images = sorted(os.listdir(source_folder))
        trail_counts = []

        for image_name in images:
            src  = os.path.join(source_folder, image_name)
            dst  = os.path.join(dest_folder, os.path.splitext(image_name)[0] + '.png')

            generate_binary_mask(src, dst)

            # Verifica se a máscara gerada tem pixels de Trail (diagnóstico)
            mask_arr = np.array(Image.open(dst))
            pct = 100 * mask_arr.sum() / mask_arr.size
            trail_counts.append(pct)

        avg_trail = sum(trail_counts) / len(trail_counts) if trail_counts else 0
        print(f"  ✓ {split}: {len(images)} máscaras geradas — Trail médio: {avg_trail:.1f}% por imagem")
        total += len(images)

    return total

if __name__ == '__main__':
    start = time.perf_counter()
    print("\n======================| Gerando mask labels |======================\n")

    total = generate_all_masks()

    end = time.perf_counter()
    print(f"\n✓ Total: {total} máscaras geradas em {end - start:.1f}s")
    print("\nSe o Trail médio aparecer como 0.0%, a cor do Trail no seu dataset")
    print("é diferente de (170,170,170). Abra uma imagem do gt_color/ no Paint,")
    print("use o conta-gotas na região da trilha e me informe a cor RGB.")