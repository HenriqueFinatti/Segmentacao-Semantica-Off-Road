import os
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SEG_ROOT redireciona dados e resultados, para testar sem tocar nas pastas reais
ROOT = os.environ.get('SEG_ROOT', REPO_ROOT)

SETTINGS_FILE = os.path.join(REPO_ROOT, 'configs', 'settings.json')
CARLA_CONFIG_DIR = os.path.join(REPO_ROOT, 'configs', 'carla')

RAW_DIR = os.path.join(ROOT, 'raw')
DATASET_DIR = os.path.join(ROOT, 'dataset')
RESULTS_DIR = os.path.join(ROOT, 'results')
COMPARISON_DIR = os.path.join(RESULTS_DIR, 'comparacao')
CARLA_RESULTS_DIR = os.path.join(RESULTS_DIR, 'carla')
DATASET_REPORT_FILE = os.path.join(RESULTS_DIR, 'dataset', 'mascaras.md')
# De onde veio cada imagem do CaSSeD (trilha e nome original), já que o nome final é só CaSSeD_<n>
CASSED_SOURCE_FILE = os.path.join(RESULTS_DIR, 'dataset', 'cassed_origem.csv')

IMAGES_TO_SEGMENT_DIR = os.path.join(ROOT, 'images', 'images_to_segment')
SEGMENTED_IMAGES_DIR = os.path.join(ROOT, 'images', 'segmented_images')
TEST_SEGMENTATION_DIR = os.path.join(DATASET_DIR, 'test', 'new_segmentation')

VIDEO_PATH = os.path.join(ROOT, 'video', 'video.mp4')
VIDEO_OUTPUT_DIR = os.path.join(ROOT, 'video', 'output')
# Frames do vídeo ficam separados de images_to_segment, para não misturar com as imagens avulsas
VIDEO_FRAMES_DIR = os.path.join(ROOT, 'video', 'frames')
VIDEO_SEGMENTED_FRAMES_DIR = os.path.join(ROOT, 'video', 'segmented_frames')

# Interface: cada configuração treinada tem a própria pasta; cada sessão de segmentação também
CONFIGURATIONS_DIR = os.path.join(RESULTS_DIR, 'configuracoes')
REGISTRY_FILE = os.path.join(RESULTS_DIR, 'registro.json')
INTERFACE_LOG_FILE = os.path.join(RESULTS_DIR, 'interface.log')
SESSIONS_DIR = os.path.join(ROOT, 'sessoes')

FREIBURG_RAW_DIR = os.path.join(RAW_DIR, 'freiburg_forest_annotated')
SYNTHETIC_RAW_DIR = os.path.join(RAW_DIR, 'synthetic_offroad')
# Ainda sem downloader: a pasta extraída do CaSSeD.tar.gz é copiada manualmente para cá
CASSED_RAW_DIR = os.path.join(RAW_DIR, 'CaSSed_Dataset')


def dataset_dir(split, folder=''):
    return os.path.join(DATASET_DIR, split, folder)


def dataset_info_file():
    # Quando e com quais datasets o dataset foi montado. Função para acompanhar DATASET_DIR (testes o redirecionam)
    return os.path.join(DATASET_DIR, 'montagem.json')


def configuration_dir(configuration_id):
    return os.path.join(CONFIGURATIONS_DIR, configuration_id)


def session_dir(session_id):
    return os.path.join(SESSIONS_DIR, session_id)


def model_path(model):
    # Caminho padrão de cada modelo, usado pelo CARLA e pelo treino fora da interface
    return os.path.join(RESULTS_DIR, model, 'model.pth')


def statistics_dir(model):
    return os.path.join(RESULTS_DIR, model, 'statistics')


def charts_dir(model):
    return os.path.join(RESULTS_DIR, model, 'images')


def relative(path):
    # Mantém relatórios e mensagens sem o caminho absoluto da máquina
    return os.path.relpath(path, ROOT)


def ensure_inside_root(path):
    # Proteção para as rotinas que apagam arquivos: nunca apagar fora de ROOT nem o próprio ROOT
    real_path = os.path.realpath(path)
    real_root = os.path.realpath(ROOT)

    if os.path.commonpath([real_path, real_root]) != real_root or real_path == real_root:
        raise ValueError(f"Caminho fora do projeto (ou a própria raiz), operação cancelada: {path}")

    return real_path


def safe_rmtree(path):
    shutil.rmtree(ensure_inside_root(path))
