import numpy as np
from PIL import Image
import os
import shutil
import time

target_color = np.array([207, 149, 30])  
tolerance = 20

dataset_map = [
    ("data/raw/synthetic_offroad/dataset/train/mask/", "data/raw/synthetic_offroad/dataset/train/rgb/", "train"),
    ("data/raw/synthetic_offroad/dataset/test/mask/", "data/raw/synthetic_offroad/dataset/test/rgb/", "test"),
]

def create_dataset_folder():
    print('Criando estrutura de pastas')
    print("""
data/
- dataset/
    - test/
        - mask/
        - mask_labels/
        - rgb/
    - train/
        - mask/
        - mask_labels/
        - rgb/
""") 
    
    for split in ['train', 'test']:
        for sub in ['mask', 'mask_labels', 'rgb']:
            os.makedirs(f'data/dataset/{split}/{sub}', exist_ok=True)

def process_dataset():
    for mask_src, rgb_src, kind in dataset_map:
        print(f'Processando conjunto {kind}...')
        
        dest_rgb = f'data/dataset/{kind}/rgb'
        dest_mask = f'data/dataset/{kind}/mask'
        dest_label = f'data/dataset/{kind}/mask_labels'

        images = os.listdir(mask_src)

        current_id = len(os.listdir(dest_rgb))

        for image_name in images:
            extension = os.path.splitext(image_name)[1]
            new_base_name = f"Synthetic_Offroad_{current_id}"
            
            img_visual = Image.open(os.path.join(mask_src, image_name)).convert('RGB')
            data = np.array(img_visual)
            
            upper_bound = target_color + tolerance
            lower_bound = target_color - tolerance
            mask_road = np.all((data >= lower_bound) & (data <= upper_bound), axis=-1)
            
            new_label = np.zeros(mask_road.shape, dtype=np.uint8)
            new_label[mask_road] = 1
            
            Image.fromarray(new_label).save(os.path.join(dest_label, f"{new_base_name}.png"))

            shutil.copy(os.path.join(mask_src, image_name), os.path.join(dest_mask, f"{new_base_name}{extension}"))

            rgb_file_path = os.path.join(rgb_src, image_name)
            current_id += 1
            if os.path.exists(rgb_file_path):
                shutil.move(rgb_file_path, os.path.join(dest_rgb, f"{new_base_name}{extension}"))

if __name__ == '__main__':
    start = time.perf_counter()
    
    print("\n======================| Gerando mask labels |======================\n")
    create_dataset_folder()
    process_dataset()
    
    print("\n======================| Finalizado com Sucesso |======================\n")
    end = time.perf_counter()
    print(f"Tempo total: {end - start:.4f} segundos")