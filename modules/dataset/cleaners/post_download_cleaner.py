import os
import shutil

class PostDownloadCleaner():
    RAW_DATASET = './raw/'

    def __init__(self):
        pass


    def delete_raw_dataset(self):
        shutil.rmtree(self.RAW_DATASET)


    def delete_unnecessary_folders(self):
        shutil.rmtree(os.path.join('dataset', 'train', 'original_segmentation'))