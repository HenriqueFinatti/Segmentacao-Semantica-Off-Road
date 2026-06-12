import os
import shutil

FREIBURG_DATASET = './data/raw/freiburg_forest_annotated'

def rename_freiburg_files():
    prefix = "Freiburg_Forest_"
    index = 0

    splits = ['test', 'train']
    
    for split in splits:
        path_original = os.path.join('data', 'dataset', split, 'original')
        path_segmentation = os.path.join('data', 'dataset', split, 'original_segmentation')
        
        mapa_segmentation = {
            os.path.splitext(f)[0]: f 
            for f in os.listdir(path_segmentation) 
            if os.path.isfile(os.path.join(path_segmentation, f))
        }

        for file in os.listdir(path_original):
            old_original_file = os.path.join(path_original, file)
            
            name, extension_orig = os.path.splitext(file)
            
            nome_completo_seg = mapa_segmentation[name]
            old_segmentation_file = os.path.join(path_segmentation, nome_completo_seg)
            
            _, extension_seg = os.path.splitext(nome_completo_seg)
            
            new_name_orig = f"{prefix}{index}{extension_orig}"
            new_name_seg = f"{prefix}{index}{extension_seg}"
            
            new_file_original = os.path.join(path_original, new_name_orig)
            new_file_segmentation = os.path.join(path_segmentation, new_name_seg)
            
            os.rename(old_original_file, new_file_original)
            os.rename(old_segmentation_file, new_file_segmentation)
            
            index += 1        
                
def copy_freiburg_dataset():
    splits = ['test', 'train']
    pastas_mapeadas = {
        'rgb': 'original',
        'GT_color': 'original_segmentation',
    }

    for split in splits:
        for origem_nome, destino_nome in pastas_mapeadas.items():
            root_path = os.path.join(FREIBURG_DATASET, split, origem_nome)
            dest_path = os.path.join('data', 'dataset', split, destino_nome)
            
            for file in os.listdir(root_path):
                root_file = os.path.join(root_path, file)
                dest_file = os.path.join(dest_path, file)
                
                name, extension = os.path.splitext(file)

                new_name = name
                new_name = new_name.replace("_mask", "")
                new_name = new_name.replace("_Clipped", "")
                new_name = new_name.replace("_clipped", "")
                new_name = f"{new_name}{extension}"

                dest_file = os.path.join(dest_path, new_name)
                shutil.copy2(root_file, dest_file)

if __name__ == '__main__':
    copy_freiburg_dataset()
    rename_freiburg_files()