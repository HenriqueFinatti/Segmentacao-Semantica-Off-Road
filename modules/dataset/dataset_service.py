import os
import json
import hashlib
from datetime import datetime

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

# Nome de exibição de cada dataset (a chave é o prefixo dos arquivos e o nome no settings.json)
DATASET_NAMES = {
    'Freiburg_Forest': 'Freiburg Forest',
    'Synthetic_Offroad': 'Synthetic Offroad',
    'CaSSeD': 'CaSSeD',
}

# Datasets que o sistema sabe baixar; o CaSSeD é copiado manualmente para raw/CaSSed_Dataset
DOWNLOADABLE = ('Freiburg_Forest', 'Synthetic_Offroad')


def test_set_fingerprint(mask_names):
    """Identifica um conjunto de teste pelas imagens que ele tem: o mesmo conjunto gera sempre o mesmo id."""
    digest = hashlib.sha1('\n'.join(sorted(mask_names)).encode('utf-8')).hexdigest()
    return digest[:10]


def dataset_of(filename):
    for prefix in DATASET_NAMES:
        if filename.startswith(f"{prefix}_"):
            return prefix
    return None


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


    # Estado

    def is_raw_available(self, name):
        if name == 'Freiburg_Forest':
            return os.path.isdir(os.path.join(paths.FREIBURG_RAW_DIR, 'train', 'rgb'))
        if name == 'Synthetic_Offroad':
            return os.path.isdir(os.path.join(paths.SYNTHETIC_RAW_DIR, 'dataset'))
        if name == 'CaSSeD':
            return os.path.isdir(os.path.join(paths.CASSED_RAW_DIR, 'Real_World_data'))
        raise ValueError(f"Dataset desconhecido: {name}")


    def count_images(self):
        counts = {name: {'train': 0, 'test': 0} for name in DATASET_NAMES}

        for split in ['train', 'test']:
            folder = paths.dataset_dir(split, 'mask')
            if not os.path.isdir(folder):
                continue
            for file in os.listdir(folder):
                prefix = dataset_of(file)
                if prefix:
                    counts[prefix][split] += 1

        return counts


    def status(self):
        counts = self.count_images()
        return {
            'datasets': [
                {
                    'id': name,
                    'nome': label,
                    'bruto_disponivel': self.is_raw_available(name),
                    'pode_baixar': name in DOWNLOADABLE,
                    'imagens_treino': counts[name]['train'],
                    'imagens_teste': counts[name]['test'],
                }
                for name, label in DATASET_NAMES.items()
            ],
            'montagem': self.read_assembly_info(),
        }


    def read_assembly_info(self):
        if not os.path.isfile(paths.dataset_info_file()):
            return None
        with open(paths.dataset_info_file(), encoding='utf-8') as f:
            return json.load(f)


    def current_test_set(self):
        """Conjunto de teste montado agora: id, número de imagens e imagens por dataset. None se não houver."""
        folder = paths.dataset_dir('test', 'mask')
        if not os.path.isdir(folder):
            return None

        names = sorted(f for f in os.listdir(folder) if f.endswith('.png'))
        if not names:
            return None

        per_dataset = {}
        for name in names:
            label = DATASET_NAMES.get(dataset_of(name), 'Outro')
            per_dataset[label] = per_dataset.get(label, 0) + 1

        info = self.read_assembly_info() or {}
        return {
            'id': test_set_fingerprint(names),
            'imagens': len(names),
            'por_dataset': per_dataset,
            'montado_em': info.get('data'),
        }


    # Download (só para raw/; montar o dataset é outro passo)

    def download(self, name, on_progress=None):
        if name not in DOWNLOADABLE:
            raise ValueError(f"O dataset {name} não pode ser baixado pelo sistema.")

        if self.is_raw_available(name):
            return False

        if name == 'Freiburg_Forest':
            print('Baixando Freiburg Forest...')
            self.download_freiburg(on_progress)
            self.clean_freiburg()
        else:
            print('Baixando Synthetic Offroad...')
            self.download_synthetic()
            self.clean_synthetic()

        return True


    def download_all_datasets(self):
        # O CaSSeD ainda não tem downloader: confere a cópia manual antes dos downloads longos
        self.cassedCleaner.check_raw_dataset()

        self.download_dataset()
        self.build_dataset()
        self.post_download_clean()
        self.save_assembly_info([name for name in DATASET_NAMES if self.is_raw_available(name)])


    def download_freiburg_dataset(self):
        self.download('Freiburg_Forest')
        self.rebuild_dataset()


    def download_synthetic_dataset(self):
        self.download('Synthetic_Offroad')
        self.rebuild_dataset()


    def prepare_cassed_dataset(self):
        self.cassedCleaner.check_raw_dataset()
        self.rebuild_dataset()


    def download_dataset(self):
        for name in DOWNLOADABLE:
            self.download(name)

        print(f'Limpando CaSSeD (já copiado para {paths.relative(paths.CASSED_RAW_DIR)})...')
        self.clean_cassed()


    # Montagem

    def rebuild_dataset(self, on_step=None):
        """Monta dataset/ de novo a partir de raw/, com todos os datasets brutos disponíveis. raw/ não é alterado
        (além da limpeza do que o CaSSeD não usa). Retorna os datasets incluídos."""
        available = [name for name in DATASET_NAMES if self.is_raw_available(name)]

        if not available:
            raise FileNotFoundError(f"Nenhum dataset bruto em {paths.relative(paths.RAW_DIR)}. Baixe ou copie os datasets antes de montar.")

        steps = ['Limpando o dataset montado'] + [f'Copiando {DATASET_NAMES[name]}' for name in available] + ['Gerando as máscaras']
        step = iter(range(1, len(steps) + 1))

        def notify(label):
            print(f'{label}...')
            if on_step:
                on_step(next(step), len(steps), label)

        notify(steps[0])
        if os.path.isdir(paths.DATASET_DIR):
            paths.safe_rmtree(paths.DATASET_DIR)
        self.create_final_dataset_folder()

        for name in available:
            notify(f'Copiando {DATASET_NAMES[name]}')
            if name == 'Freiburg_Forest':
                self.convert_freiburg()
            elif name == 'Synthetic_Offroad':
                self.convert_synthetic()
            else:
                self.clean_cassed()
                self.convert_cassed()

        notify(steps[-1])
        self.generate_dataset_masks()
        self.post_download_clean()
        self.save_assembly_info(available)
        return available


    def build_dataset(self):
        self.create_final_dataset_folder()

        print('Padronizando e copiando imagens...')
        self.convert_freiburg()
        self.convert_synthetic()
        self.convert_cassed()

        print('Gerando máscaras...')
        self.generate_dataset_masks()


    def save_assembly_info(self, datasets):
        test_set = self.current_test_set()
        info = {
            'data': datetime.now().isoformat(timespec='seconds'),
            'datasets': [DATASET_NAMES[name] for name in datasets],
            'conjunto_de_teste': test_set['id'] if test_set else None,
        }
        with open(paths.dataset_info_file(), 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)


    def create_final_dataset_folder(self):
        for split in ['train', 'test']:
            for sub in ['mask', 'original', 'original_segmentation']:
                os.makedirs(paths.dataset_dir(split, sub), exist_ok=True)


    def generate_dataset_masks(self):
        self.maskGenerator.generate_masks()


    def download_freiburg(self, on_progress=None):
        self.freiburgDownloader.download_dataset(on_progress)


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
        print('Apagando segmentação original do dataset de treino')
        self.postDownloadCleaner.delete_unnecessary_folders()
