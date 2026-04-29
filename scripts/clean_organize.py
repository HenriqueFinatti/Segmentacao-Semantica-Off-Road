import time
import os
import runpy

def create_dataset_folder():
    print('Criando estrutura de pastas')
    
    for split in ['train', 'test']:
        for sub in ['mask', 'mask_labels', 'rgb']:
            os.makedirs(f'data/dataset/{split}/{sub}', exist_ok=True)    

if __name__ == '__main__':
    start = time.perf_counter()
    
    print("======================| Iniciando limpeza dos datasets |======================")
    create_dataset_folder()
    
    scripts = [
        "scripts/cleaners/freiburg_forest.py",
        "scripts/cleaners/synthetic_offroad.py"
    ]

    start = time.perf_counter()
    for script in scripts:
        runpy.run_path(script, run_name="__main__")
    
    end = time.perf_counter()

    print(f"Tempo de limpeza: {end - start:.4f} segundos")