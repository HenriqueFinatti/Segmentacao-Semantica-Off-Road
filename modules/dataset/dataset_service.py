import os

from configs import paths

from modules.dataset.generators.mask_generator import MaskGenerator
from modules.dataset.cleaners.post_download_cleaner import PostDownloadCleaner

from modules.dataset.cleaners.freiburg_cleaner import FreiburgCleaner
from modules.dataset.converters.freiburg_converter import FreiburgConverter
from modules.dataset.downloaders.freiburg_downloader import FreiburgDownloader

from modules.dataset.cleaners.synthetic_cleaner import SyntheticCleaner
from modules.dataset.converters.synthetic_converter import SyntheticConverter
from modules.dataset.downloaders.synthetic_downloader import SyntheticDownloader

from modules.dataset.cleaners.cassed_cleaner import CaSSeDCleaner
from modules.dataset.converters.cassed_converter import CaSSeDConverter

class DatasetService():

    def __init__(self, settings):
        self.maskGenerator = MaskGenerator(settings)
        self.postDownloadCleaner = PostDownloadCleaner()

        self.freiburgDownloader = FreiburgDownloader()
        self.freiburgCleaner = FreiburgCleaner()
        self.freiburgConverter = FreiburgConverter(settings)

        self.syntheticDownloader = SyntheticDownloader()
        self.syntheticCleaner = SyntheticCleaner()
        self.syntheticConverter = SyntheticConverter()

        self.cassedCleaner = CaSSeDCleaner()
        self.cassedConverter = CaSSeDConverter(settings)

    def download_all_datasets(self):
        # O CaSSeD ainda não tem downloader: confere a cópia manual antes dos downloads longos
        self.cassedCleaner.check_raw_dataset()

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


    def prepare_cassed_dataset(self):
        # Sem downloader por enquanto: usa a pasta já copiada para raw/CaSSed_Dataset
        print('Limpando CaSSeD...')
        self.clean_cassed()

        self.create_final_dataset_folder()

        print('Padronizando e movendo imagens...')
        self.convert_cassed()

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

        print(f'Limpando CaSSeD (já copiado para {paths.relative(paths.CASSED_RAW_DIR)})...')
        self.clean_cassed()


    def build_dataset(self):
        self.create_final_dataset_folder()

        print('Padronizando e movendo imagens...')
        self.convert_freiburg()
        self.convert_synthetic()
        self.convert_cassed()

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


    def clean_cassed(self):
        self.cassedCleaner.delete_unused_data()


    def convert_cassed(self):
        self.cassedConverter.convert()


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
