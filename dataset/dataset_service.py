import os

from configs.settings import Settings

from dataset import (
    FreiburgDownloader,
    FreiburgCleaner,
    FreiburgConverter,
    SyntheticDownloader,
    SyntheticCleaner,
    SyntheticConverter,
    MaskGenerator,
)

settings = Settings()

maskGenerator = MaskGenerator(settings)

freiburgDownloader = FreiburgDownloader()
freiburgCleaner = FreiburgCleaner()
freiburgConverter = FreiburgConverter()

syntheticDownloader = SyntheticDownloader()
syntheticCleaner = SyntheticCleaner()
syntheticConverter = SyntheticConverter()

class DatasetService():

    def __init__(self):
        pass

    def download_dataset(self):
        self.create_raw_dataset_folder()

        self.download_freiburg()
        self.clean_freiburg()

        self.download_synthetic()
        self.clean_synthetic()


    def build_dataset(self):
        self.create_final_dataset_folder()

        self.convert_freiburg()
        self.convert_synthetic()

        self.generate_dataset_masks()


    def create_raw_dataset_folder(self):
        os.makedirs("./data/raw", exist_ok=True)


    def create_final_dataset_folder(self):
        for split in ['train', 'test']:
            for sub in ['mask', 'new_segmentation', 'original', 'original_segmentation']:
                os.makedirs(f'data/dataset/{split}/{sub}', exist_ok=True)


    def generate_dataset_masks(self):
        maskGenerator.generate_masks()


    def download_freiburg(self):
        freiburgDownloader.download_dataset()


    def download_synthetic(self):
        syntheticDownloader.download_dataset()


    def clean_freiburg(self):
        freiburgCleaner.delete_tar_files()
        freiburgCleaner.delete_unused_folders()


    def clean_synthetic(self):
        syntheticCleaner.delete_raw_mask_labels()


    def convert_freiburg(self):
        freiburgConverter.move_freiburg_files()
        freiburgConverter.rename_freiburg_files()


    def convert_synthetic(self):
        syntheticConverter.move_synthetic_files()
