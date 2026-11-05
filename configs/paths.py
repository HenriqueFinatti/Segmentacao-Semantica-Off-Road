import os

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

IMAGES_TO_SEGMENT_DIR = os.path.join(ROOT, 'images', 'images_to_segment')
SEGMENTED_IMAGES_DIR = os.path.join(ROOT, 'images', 'segmented_images')
TEST_SEGMENTATION_DIR = os.path.join(DATASET_DIR, 'test', 'new_segmentation')

VIDEO_PATH = os.path.join(ROOT, 'video', 'video.mp4')
VIDEO_OUTPUT_DIR = os.path.join(ROOT, 'video', 'output')

FREIBURG_RAW_DIR = os.path.join(RAW_DIR, 'freiburg_forest_annotated')
SYNTHETIC_RAW_DIR = os.path.join(RAW_DIR, 'synthetic_offroad')


def dataset_dir(split, folder=''):
    return os.path.join(DATASET_DIR, split, folder)


def model_path(model):
    return os.path.join(RESULTS_DIR, model, 'model.pth')


def statistics_dir(model):
    return os.path.join(RESULTS_DIR, model, 'statistics')


def charts_dir(model):
    return os.path.join(RESULTS_DIR, model, 'images')


def relative(path):
    # Mantém relatórios e mensagens sem o caminho absoluto da máquina
    return os.path.relpath(path, ROOT)
