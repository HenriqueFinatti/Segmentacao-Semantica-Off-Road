import os

import numpy as np
from PIL import Image

class MaskGenerator:

    def __init__(self, settings):
        self.dataset_labels = settings.get_dataset_labels()


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


    def generate_masks(self):
        splits = ["test", "train"]

        total_generated = 0
        total_skipped = 0

        for split in splits:
            source_folder = f"./data/dataset/{split}/original_segmentation"
            dest_folder = f"./data/dataset/{split}/mask"

            os.makedirs(dest_folder, exist_ok=True)

            images = sorted(os.listdir(source_folder))

            results = {prefix: [] for prefix in self.dataset_labels.keys()}
            skipped = []

            for image_name in images:
                prefix, config = self.get_prefix_config(image_name)

                if config is None:
                    skipped.append(image_name)
                    continue

                src = os.path.join(source_folder, image_name)
                dst = os.path.join(
                    dest_folder,
                    os.path.splitext(image_name)[0] + ".png"
                )

                pct = self.generate_binary_mask(src, dst, config)
                results[prefix].append(pct)

            generated_in_split = sum(len(values) for values in results.values())

            total_generated += generated_in_split
            total_skipped += len(skipped)