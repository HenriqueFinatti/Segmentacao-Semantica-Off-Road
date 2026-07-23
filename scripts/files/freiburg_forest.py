import os
import requests
import tarfile
import shutil

class FreiburgForest():

    OUTPUT_DIR = "./data/raw"
    FINAL_FILE = os.path.join(OUTPUT_DIR, "freiburg_forest_annotated.tar.gz")
    BASE_URL = "https://deepscene.cs.uni-freiburg.de/static/datasets/"

    FILES = [
        "freiburg_forest_annotated.tar.gz.part-aa",
        "freiburg_forest_annotated.tar.gz.part-ab",
        "freiburg_forest_annotated.tar.gz.part-ac"
    ]

    def __init__(self):
        pass

    def download_full_dataset(self):
        for file_name in self.FILES:
            url = self.BASE_URL + file_name
            dest_path = os.path.join(self.OUTPUT_DIR, file_name)

            self.download_file(url, dest_path)
        self.merge_files()

    def move_raw_dataset_to_final_dataset(self):
        self.copy_freiburg_dataset()
        self.rename_freiburg_files()
        
    def delete_unnecessary_files(self):
        for filename in os.listdir(self.OUTPUT_DIR):
            file_path = os.path.join(self.OUTPUT_DIR, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)

        for split in ['test', 'train']:
            split_path = os.path.join("./data/raw/freiburg_forest_annotated", split)
            for folder in os.listdir(split_path):
                full_folder_path = os.path.join(split_path, folder)
                if folder not in ['rgb', 'GT_color']:
                    shutil.rmtree(full_folder_path)
                    
    def download_file(self, url, dest_path):
        headers = {}
        mode = "wb"

        response = requests.get(url, headers=headers, stream=True)

        with open(dest_path, mode) as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    
    def merge_files(self):
        with open(self.FINAL_FILE, "wb") as outfile:
            for file_name in self.FILES:
                part_path = os.path.join(self.OUTPUT_DIR, file_name)
                with open(part_path, "rb") as infile:
                    outfile.write(infile.read())

        with tarfile.open(self.FINAL_FILE, "r:*") as tar:
            tar.extractall(path=self.OUTPUT_DIR)

    def rename_freiburg_files(self):
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
                
    def copy_freiburg_dataset(self):
        splits = ['test', 'train']
        pastas_mapeadas = {
            'rgb': 'original',
            'GT_color': 'original_segmentation',
        }

        for split in splits:
            for origem_nome, destino_nome in pastas_mapeadas.items():
                root_path = os.path.join('./data/raw/freiburg_forest_annotated', split, origem_nome)
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
