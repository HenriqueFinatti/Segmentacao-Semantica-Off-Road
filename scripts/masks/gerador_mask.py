from PIL import Image
import numpy as np
import os
import time

# ─────────────────────────────────────────────────────────────────────────────
# Configuração por prefixo:
#   chave   → prefixo do nome do arquivo (case-sensitive)
#   valor   → dicionário com:
#               "color"     : cor RGB alvo (np.uint8)
#               "label"     : nome legível da classe (para logs)
#               "tolerance" : tolerância ±N por canal (para variações de PNG)
# ─────────────────────────────────────────────────────────────────────────────

PREFIX_CONFIG = {
    "Freiburg_Forest": {
        "color":     np.array([170, 170, 170], dtype=np.uint8),
        "label":     "Trail",
        "tolerance": 10,
    },
    "Synthetic_Offroad": {
        "color":     np.array([207, 149, 30], dtype=np.uint8),
        "label":     "Trail",
        "tolerance": 10,
    }
}

def get_prefix_config(filename: str) -> tuple[str, dict] | tuple[None, None]:
    for prefix, config in PREFIX_CONFIG.items():
        if filename.startswith(prefix):
            return prefix, config
    return None, None

def generate_binary_mask(gt_color_path: str, output_path: str, config: dict) -> float:
    target_color = config["color"]
    tolerance    = config["tolerance"]

    img  = Image.open(gt_color_path).convert("RGB")
    data = np.array(img, dtype=np.uint8)

    lower = np.clip(target_color.astype(int) - tolerance, 0, 255).astype(np.uint8)
    upper = np.clip(target_color.astype(int) + tolerance, 0, 255).astype(np.uint8)

    is_target = np.all((data >= lower) & (data <= upper), axis=-1)

    mask = np.zeros(is_target.shape, dtype=np.uint8)
    mask[is_target] = 1

    Image.fromarray(mask).save(output_path)

    return 100 * mask.sum() / mask.size

def generate_all_masks():
    splits = ["test", "train"]
    total_generated = 0
    total_skipped   = 0

    for split in splits:
        source_folder = f"./data/dataset/{split}/original_segmentation"
        dest_folder   = f"./data/dataset/{split}/mask"
        os.makedirs(dest_folder, exist_ok=True)

        images = sorted(os.listdir(source_folder))

        results: dict[str, list[float]] = {p: [] for p in PREFIX_CONFIG}
        skipped = []

        for image_name in images:
            prefix, config = get_prefix_config(image_name)

            if config is None:
                skipped.append(image_name)
                continue

            src = os.path.join(source_folder, image_name)
            dst = os.path.join(dest_folder, os.path.splitext(image_name)[0] + ".png")

            pct = generate_binary_mask(src, dst, config)
            results[prefix].append(pct)

        generated_in_split = sum(len(v) for v in results.values())
        total_generated += generated_in_split
        total_skipped   += len(skipped)

    return total_generated, total_skipped


if __name__ == "__main__":
    start = time.perf_counter()
    print("\n======================| Gerando mask labels |======================\n")

    total_generated, total_skipped = generate_all_masks()

    elapsed = time.perf_counter() - start
    print(f"\n{total_generated} máscaras geradas em {elapsed:.1f}s")
    if total_skipped:
        print(f"{total_skipped} imagem(ns) ignorada(s) por prefixo não configurado")