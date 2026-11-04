import os
import time
from modules.dataset.dataset_service import DatasetService
from modules.training.training_service import TrainingService
from modules.segmentation.segmentation_service import SegmentationService
from processing.video import Video

VIDEO_PATH = os.path.join("video", "video.mp4")
VIDEO_OUTPUT_DIR = os.path.join("video", "output")
IMAGES_TO_SEGMENT_DIR = os.path.join("images", "images_to_segment")

dataset_service = DatasetService()
training_service = TrainingService()
segmentation_service = SegmentationService()


def format_time(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:02d}h {mins:02d}m {secs:05.2f}s"


def run_step(label, step):
    start_time = time.perf_counter()
    step()
    elapsed = time.perf_counter() - start_time
    print(f"\n[METRICA] {label} concluído em: {format_time(elapsed)}")


def has_images_to_segment():
    return os.path.isdir(IMAGES_TO_SEGMENT_DIR) and len(os.listdir(IMAGES_TO_SEGMENT_DIR)) > 0


# Segmentação

def segment_video():
    video_processing = Video(VIDEO_PATH, VIDEO_OUTPUT_DIR)

    frames = video_processing.extract_video()
    print(f"\nForam extraidos {frames} frames")

    results = segmentation_service.segment_images(context='video')
    video_processing.make_segmented_video(results)


# Treinar e segmentar

def train_and_segment_images():
    run_step('Treinamento', training_service.train_models)
    run_step('Segmentação de imagens', segmentation_service.segment_images)


def train_and_segment_test_dataset():
    run_step('Treinamento', training_service.train_models)
    run_step('Segmentação do dataset de teste', segmentation_service.segment_test_dataset)


def train_and_segment_video():
    run_step('Treinamento', training_service.train_models)
    run_step('Segmentação de vídeo', segment_video)


# Processo completo

def full_process():
    run_step('Download dos datasets', dataset_service.download_all_datasets)
    run_step('Treinamento', training_service.train_models)
    run_step('Segmentação do dataset de teste', segmentation_service.segment_test_dataset)

    if os.path.exists(VIDEO_PATH):
        # O vídeo extrai os frames para images_to_segment, então também segmenta as imagens que já estavam lá
        run_step('Segmentação de vídeo', segment_video)
    elif has_images_to_segment():
        run_step('Segmentação de imagens', segmentation_service.segment_images)
    else:
        print(f"\nNenhum vídeo em {VIDEO_PATH} nem imagens em {IMAGES_TO_SEGMENT_DIR}. Pulando essas segmentações.")


MENU = [
    ('Datasets', [
        ('1', 'Baixar todos os datasets', dataset_service.download_all_datasets),
        ('2', 'Baixar Freiburg Forest', dataset_service.download_freiburg_dataset),
        ('3', 'Baixar Synthetic Offroad', dataset_service.download_synthetic_dataset),
    ]),
    ('Treinamento', [
        ('4', 'Treinar todos os modelos', training_service.train_models),
        ('5', 'Treinar FCN', training_service.train_fcn),
        ('6', 'Treinar DeepLabV3+', training_service.train_deep_lab),
    ]),
    ('Segmentação', [
        ('7', 'Segmentar imagens', segmentation_service.segment_images),
        ('8', 'Segmentar dataset de teste', segmentation_service.segment_test_dataset),
        ('9', 'Segmentar vídeo', segment_video),
    ]),
    ('Treinar e Segmentar', [
        ('10', 'Treinar todos os modelos e segmentar imagens', train_and_segment_images),
        ('11', 'Treinar todos os modelos e segmentar dataset de teste', train_and_segment_test_dataset),
        ('12', 'Treinar todos os modelos e segmentar vídeo', train_and_segment_video),
    ]),
    ('Completo', [
        ('13', 'Processo completo (baixar, treinar e segmentar tudo)', full_process),
    ]),
]


def print_menu():
    print('===================================')
    for section, options in MENU:
        print(f'\n{section}')
        for key, label, _ in options:
            print(f'  {key:>2} - {label}')
    print('\n   0 - Sair')
    print('===================================')


def get_options():
    return {key: (label, action) for _, options in MENU for key, label, action in options}


if __name__ == '__main__':
    options = get_options()

    print_menu()
    op = input('Digite a operação: ').strip()
    print('\n')

    if op == '0':
        exit()

    if op not in options:
        print(f'Operação inválida: {op}')
        exit(1)

    label, action = options[op]

    total_start = time.perf_counter()
    action()
    total_elapsed = time.perf_counter() - total_start
    print(f"\n[METRICA] {label} finalizado em: {format_time(total_elapsed)}")
