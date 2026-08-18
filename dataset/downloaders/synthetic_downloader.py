
import os
import shutil
import kagglehub

class SyntheticDownloader():
    BASE_DIR = "./data/raw"
    
    def __init__(self):
        pass


    def download_dataset(self):
        downloaded_path = kagglehub.dataset_download("konrmal94/synthetic-offroad-image-dataset")
        destination = os.path.join(self.BASE_DIR, "synthetic_offroad")

        shutil.move(downloaded_path, destination)
