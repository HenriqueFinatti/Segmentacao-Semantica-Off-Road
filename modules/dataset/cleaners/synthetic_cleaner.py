import os

from configs import paths

class SyntheticCleaner():
    SYNTHETIC_DATASET = os.path.join(paths.SYNTHETIC_RAW_DIR, 'dataset')
    def __init__(self):
        pass


    def delete_raw_mask_labels(self):
        splits = ['test', 'train', 'val']

        for split in splits:
            mask_labels_path = os.path.join(self.SYNTHETIC_DATASET, split, 'mask_labels')
            paths.safe_rmtree(mask_labels_path)