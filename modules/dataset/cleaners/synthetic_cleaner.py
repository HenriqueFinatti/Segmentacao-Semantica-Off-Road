import os
import shutil

class SyntheticCleaner():
    SYNTHETIC_DATASET = './raw/synthetic_offroad/dataset'
    
    def __init__(self):
        pass


    def delete_raw_mask_labels(self):
        splits = ['test', 'train', 'val']
        
        for split in splits:
            mask_labels_path = os.path.join(self.SYNTHETIC_DATASET, split, 'mask_labels')
            shutil.rmtree(mask_labels_path)