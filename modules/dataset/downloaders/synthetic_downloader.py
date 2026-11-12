import shutil
import kagglehub

from configs import paths

class SyntheticDownloader():
    def __init__(self):
        pass


    def download_dataset(self):
        downloaded_path = kagglehub.dataset_download("konrmal94/synthetic-offroad-image-dataset")
        destination = paths.SYNTHETIC_RAW_DIR

        shutil.move(downloaded_path, destination)
