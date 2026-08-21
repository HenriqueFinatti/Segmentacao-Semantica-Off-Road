import os
import shutil

class SyntheticConverter():
    SYNTHETIC_DATASET = './data/raw/synthetic_offroad/dataset'
    
    def __init__(self):
        pass
            
            
    def move_synthetic_files(self):
        prefix = "Synthetic_Offroad_"
        index = 0
        splits = ['test', 'train', 'val']

        for split in splits:
            root_rgb = os.path.join(self.SYNTHETIC_DATASET, split, 'rgb')
            root_mask = os.path.join(self.SYNTHETIC_DATASET, split, 'mask')

            if split == 'val': 
                split = 'train'
            
            dest_original = os.path.join('data', 'dataset', split, 'original')
            dest_segmentation = os.path.join('data', 'dataset', split, 'original_segmentation')

            for file_rgb in os.listdir(root_rgb):
                src_rgb = os.path.join(root_rgb, file_rgb)
                
                name_rgb, extension = os.path.splitext(file_rgb)
                
                id_part = name_rgb.split('_', 1)[1]
                
                file_mask = f"segmentation_{id_part}{extension}"
                src_mask = os.path.join(root_mask, file_mask)

                new_name = f"{prefix}{index}{extension}"
                
                dest_rgb = os.path.join(dest_original, new_name)
                dest_mask = os.path.join(dest_segmentation, new_name)

                shutil.copy2(src_rgb, dest_rgb)
                shutil.copy2(src_mask, dest_mask)
                
                index += 1