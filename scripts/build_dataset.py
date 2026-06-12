import time
import os
import runpy

def create_dataset_folder():
    for split in ['train', 'test']:
        for sub in ['mask', 'new_segmentation', 'original', 'original_segmentation']:
            os.makedirs(f'data/dataset/{split}/{sub}', exist_ok=True)    

if __name__ == '__main__':
    start = time.perf_counter()
    
    print("======================| Montando Dataset |======================")
    create_dataset_folder()
    
    scripts = [
        "scripts/cleaners/freiburg_forest.py",
        "scripts/cleaners/synthetic_offroad.py",
    ]

    start = time.perf_counter()
    for script in scripts:
        runpy.run_path(script, run_name="__main__")
    
    end = time.perf_counter()

    print(f"Finalizado em: {end - start:.4f} segundos")