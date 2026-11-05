import os

from configs import paths
from configs.settings import Settings

from modules.dataset.generators.mask_generator import MaskGenerator
from modules.dataset.cleaners.post_download_cleaner import PostDownloadCleaner

from modules.dataset.cleaners.freiburg_cleaner import FreiburgCleaner
from modules.dataset.converters.freiburg_converter import FreiburgConverter
from modules.dataset.downloaders.freiburg_downloader import FreiburgDownloader

from modules.dataset.cleaners.synthetic_cleaner import SyntheticCleaner
from modules.dataset.converters.synthetic_converter import SyntheticConverter
from modules.dataset.downloaders.synthetic_downloader import SyntheticDownloader

class DatasetService():

    def __init__(self):
        self.maskGenerator = MaskGenerator(Settings())
        self.postDownloadCleaner = PostDownloadCleaner()

        self.freiburgDownloader = FreiburgDownloader()
        self.freiburgCleaner = FreiburgCleaner()
        self.freiburgConverter = FreiburgConverter()

        self.syntheticDownloader = SyntheticDownloader()
        self.syntheticCleaner = SyntheticCleaner()
        self.syntheticConverter = SyntheticConverter()

    def download_all_datasets(self):
        self.download_dataset()
        self.build_dataset()
        self.post_download_clean()


    def download_freiburg_dataset(self):
        print('Baixando Freiburg Forest...')
        self.download_freiburg()
        self.clean_freiburg()

        self.create_final_dataset_folder()

        print('Padronizando e movendo imagens...')
        self.convert_freiburg()

        print('Gerando máscaras...')
        self.generate_dataset_masks()

        self.post_download_clean()


    def download_synthetic_dataset(self):
        print('Baixando Synthetic Offroad...')
        self.download_synthetic()
        self.clean_synthetic()

        self.create_final_dataset_folder()

        print('Padronizando e movendo imagens...')
        self.convert_synthetic()

        print('Gerando máscaras...')
        self.generate_dataset_masks()

        self.post_download_clean()


    def download_dataset(self):
        print('Baixando Freiburg Forest...')
        self.download_freiburg()
        self.clean_freiburg()

        print('Baixando Synthetic Offroad...')
        self.download_synthetic()
        self.clean_synthetic()


    def build_dataset(self):
        self.create_final_dataset_folder()

        print('Padronizando e movendo imagens...')
        self.convert_freiburg()
        self.convert_synthetic()

        print('Gerando máscaras...')
        self.generate_dataset_masks()


    def create_final_dataset_folder(self):
        for split in ['train', 'test']:
            for sub in ['mask', 'original', 'original_segmentation']:
                os.makedirs(paths.dataset_dir(split, sub), exist_ok=True)


    def generate_dataset_masks(self):
        self.maskGenerator.generate_masks()


    def download_freiburg(self):
        self.freiburgDownloader.download_dataset()


    def download_synthetic(self):
        self.syntheticDownloader.download_dataset()


    def clean_freiburg(self):
        self.freiburgCleaner.delete_tar_files()
        self.freiburgCleaner.delete_unused_folders()


    def clean_synthetic(self):
        self.syntheticCleaner.delete_raw_mask_labels()


    def convert_freiburg(self):
        self.freiburgConverter.move_freiburg_files()
        self.freiburgConverter.rename_freiburg_files()


    def convert_synthetic(self):
        self.syntheticConverter.move_synthetic_files()


    def post_download_clean(self):
        print('Apagando arquivos originais...')
        self.postDownloadCleaner.delete_raw_dataset()

        print('Apagando segmentação original do dataset de treino')
        self.postDownloadCleaner.delete_unnecessary_folders()
