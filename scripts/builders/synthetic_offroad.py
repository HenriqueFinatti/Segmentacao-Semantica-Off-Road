import os
import shutil

SYNTHETIC_DATASET = './data/raw/synthetic_offroad/dataset'

def rename_synthetic_files():
    prefix = "Synthetic_Offroad_"
    index = 0

    splits = ['test', 'train']
    
    for split in splits:
        path_original = os.path.join('data', 'dataset', split, 'original')
        path_segmentation = os.path.join('data', 'dataset', split, 'original_segmentation')
        
        for file in os.listdir(path_original):
            name, extension = os.path.splitext(file)

            if "Freiburg_Forest_" not in name:
                old_original_file = os.path.join(path_original, file)
                old_segmentation_file = os.path.join(path_segmentation, file)
                
                new_name = f"{prefix}{index}{extension}"
                new_file_original = os.path.join(path_original, new_name)
                new_file_segmentation = os.path.join(path_segmentation, new_name)
                
                os.rename(old_original_file, new_file_original)
                os.rename(old_segmentation_file, new_file_segmentation)
                
                index += 1   

def copy_synthetic_dataset():
    splits = ['test', 'train']
    pastas_mapeadas = {
        'rgb': 'original',
        'mask': 'original_segmentation',
    }

    for split in splits:
        for origem_nome, destino_nome in pastas_mapeadas.items():
            root_path = os.path.join(SYNTHETIC_DATASET, split, origem_nome)
            dest_path = os.path.join('data', 'dataset', split, destino_nome)

            for file in os.listdir(root_path):
                root_file = os.path.join(root_path, file)
                
                name, extension = os.path.splitext(file)                        
                novo_nome_base = name.split('_', 1)[1]
                novo_nome_completo = f"{novo_nome_base}{extension}"

                dest_file = os.path.join(dest_path, novo_nome_completo)
                
                shutil.copy2(root_file, dest_file)


if __name__ == '__main__':

    copy_synthetic_dataset()
    rename_synthetic_files()