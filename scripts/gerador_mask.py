import numpy as np
from PIL import Image
import os
import time
import shutil

tolerance = 20

def final_clean():
    splits = ['test', 'train']

    for split in splits:
        folder = f'./data/dataset/{split}/mask'
        shutil.rmtree(folder)
        os.makedirs(folder, exist_ok=True)

def get_target_color(image):
    if 'Freiburg_Forest' in image:
        return np.array([207, 149, 30])
    
    if 'Synthetic_Offroad' in image:
        return np.array([170, 170, 170])
    
def generate_masks():
    splits = ['test', 'train']

    for split in splits:
        source_folder = f'./data/dataset/{split}/mask'
        destination_folder = f'./data/dataset/{split}/mask_labels'
        images = os.listdir(source_folder)

        for image in images:
            img_visual = Image.open(os.path.join(source_folder, image)).convert('RGB')
            data = np.array(img_visual)

            target_color = get_target_color(image)

            upper_bound = target_color + tolerance
            lower_bound = target_color - tolerance
            mask_road = np.all((data >= lower_bound) & (data <= upper_bound), axis=-1)
            
            new_label = np.zeros(mask_road.shape, dtype=np.uint8)
            new_label[mask_road] = 1
            
            Image.fromarray(new_label).save(os.path.join(destination_folder, image))

if __name__ == '__main__':
    start = time.perf_counter()
    
    print("\n======================| Gerando mask labels |======================\n")
    generate_masks()
    
    final_clean()
    print("\n======================| Finalizado com Sucesso |======================\n")
    end = time.perf_counter()
    print(f"Tempo total: {end - start:.4f} segundos")