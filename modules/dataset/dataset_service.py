import os

from configs.settings import Settings

from modules.dataset.generators.mask_generator import MaskGenerator
from modules.dataset.cleaners.post_download_cleaner import PostDownloadCleaner

from modules.dataset.cleaners.freiburg_cleaner import FreiburgCleaner
from modules.dataset.converters.freiburg_converter import FreiburgConverter
from modules.dataset.downloaders.freiburg_downloader import FreiburgDownloader

from modules.dataset.cleaners.synthetic_cleaner import SyntheticCleaner
from modules.dataset.converters.synthetic_converter import SyntheticConverter
from modules.dataset.downloaders.synthetic_downloader import SyntheticDownloader

from modules.dataset.converters.yamaha_converter import YamahaConverter

settings = Settings()

maskGenerator = MaskGenerator(settings)
postDownloadCleaner = PostDownloadCleaner()

freiburgDownloader = FreiburgDownloader()
freiburgCleaner = FreiburgCleaner()
freiburgConverter = FreiburgConverter()

syntheticDownloader = SyntheticDownloader()
syntheticCleaner = SyntheticCleaner()
syntheticConverter = SyntheticConverter()

yamahaConverter = YamahaConverter()

class DatasetService():

    def __init__(self):
        pass

    def download_dataset(self):
        print('Baixando Freiburg Forest...')
        # self.download_freiburg()
        # self.clean_freiburg()

        print('Baixando Synthetic Offroad...')
        # self.download_synthetic()
        # self.clean_synthetic()


    def build_dataset(self):
        self.create_final_dataset_folder()

        print('Padronizando e movendo imagens...')
        # self.convert_freiburg()
        # self.convert_synthetic()
        # self.convert_yamaha()

        print('Gerando máscaras...')
        self.generate_dataset_masks()


    def create_final_dataset_folder(self):
        for split in ['train', 'test']:
            for sub in ['mask', 'original', 'original_segmentation']:
                os.makedirs(f'dataset/{split}/{sub}', exist_ok=True)


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


    def convert_yamaha(self):
        yamahaConverter.move_yamaha_files()

        
    def convert_freiburg(self):
        freiburgConverter.move_freiburg_files()
        freiburgConverter.rename_freiburg_files()


    def convert_synthetic(self):
        syntheticConverter.move_synthetic_files()


    def post_download_clean(self):
        print('Apagando arquivos originais...')
        postDownloadCleaner.delete_raw_dataset()

        print('Apagando segmentação original do dataset de treino')
        postDownloadCleaner.delete_unnecessary_folders()
