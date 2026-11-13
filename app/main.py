import os
import time

from configs import paths
from modules.dataset.dataset_service import DatasetService
from modules.driving.server import DrivingServer, MODES, RunConfig
from modules.training.training_service import TrainingService
from modules.segmentation.segmentation_service import SegmentationService
from processing.video import Video


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
    return os.path.isdir(paths.IMAGES_TO_SEGMENT_DIR) and len(os.listdir(paths.IMAGES_TO_SEGMENT_DIR)) > 0


class Application:

    def __init__(self):
        self.dataset_service = DatasetService()
        self.training_service = TrainingService()
        self.segmentation_service = SegmentationService()


    # Segmentação

    def segment_video(self):
        video_processing = Video()

        frames = video_processing.extract_video()
        print(f"\nForam extraidos {frames} frames")

        results = self.segmentation_service.segment_video_frames()
        video_processing.make_segmented_video(results)


    # Treinar e segmentar

    def train_and_segment_images(self):
        run_step('Treinamento', self.training_service.train_models)
        run_step('Segmentação de imagens', self.segmentation_service.segment_images)


    def train_and_segment_test_dataset(self):
        run_step('Treinamento', self.training_service.train_models)
        run_step('Segmentação do dataset de teste', self.segmentation_service.segment_test_dataset)


    def train_and_segment_video(self):
        run_step('Treinamento', self.training_service.train_models)
        run_step('Segmentação de vídeo', self.segment_video)


    # Processo completo

    def full_process(self):
        run_step('Download dos datasets', self.dataset_service.download_all_datasets)
        run_step('Treinamento', self.training_service.train_models)
        run_step('Segmentação do dataset de teste', self.segmentation_service.segment_test_dataset)

        if has_images_to_segment():
            run_step('Segmentação de imagens', self.segmentation_service.segment_images)
        else:
            print(f"\nNenhuma imagem em {paths.relative(paths.IMAGES_TO_SEGMENT_DIR)}. Pulando a segmentação de imagens.")

        if os.path.exists(paths.VIDEO_PATH):
            run_step('Segmentação de vídeo', self.segment_video)
        else:
            print(f"\nNenhum vídeo em {paths.relative(paths.VIDEO_PATH)}. Pulando a segmentação de vídeo.")


    # CARLA

    def drive_in_carla(self):
        defaults = RunConfig()
        weather = input(f'Clima [{defaults.weather}]: ').strip() or defaults.weather
        mode = input(f"Modo ({' ou '.join(MODES)}) [{defaults.mode}]: ").strip() or defaults.mode

        if mode not in MODES:
            print(f'Modo inválido: {mode}')
            return

        DrivingServer(RunConfig(weather=weather, mode=mode)).serve()


    def build_menu(self):
        return [
            ('Datasets', [
                ('1', 'Baixar todos os datasets', self.dataset_service.download_all_datasets),
                ('2', 'Baixar Freiburg Forest', self.dataset_service.download_freiburg_dataset),
                ('3', 'Baixar Synthetic Offroad', self.dataset_service.download_synthetic_dataset),
            ]),
            ('Treinamento', [
                ('4', 'Treinar todos os modelos', self.training_service.train_models),
                ('5', 'Treinar FCN', self.training_service.train_fcn),
                ('6', 'Treinar DeepLabV3+', self.training_service.train_deep_lab),
            ]),
            ('Segmentação', [
                ('7', 'Segmentar imagens', self.segmentation_service.segment_images),
                ('8', 'Segmentar dataset de teste', self.segmentation_service.segment_test_dataset),
                ('9', 'Segmentar vídeo', self.segment_video),
            ]),
            ('Treinar e Segmentar', [
                ('10', 'Treinar todos os modelos e segmentar imagens', self.train_and_segment_images),
                ('11', 'Treinar todos os modelos e segmentar dataset de teste', self.train_and_segment_test_dataset),
                ('12', 'Treinar todos os modelos e segmentar vídeo', self.train_and_segment_video),
            ]),
            ('Completo', [
                ('13', 'Processo completo (baixar, treinar e segmentar tudo)', self.full_process),
            ]),
            ('CARLA', [
                ('14', 'Dirigir no CARLA', self.drive_in_carla),
            ]),
        ]


def print_menu(menu):
    print('===================================')
    for section, options in menu:
        print(f'\n{section}')
        for key, label, _ in options:
            print(f'  {key:>2} - {label}')
    print('\n   0 - Sair')
    print('===================================')


def get_options(menu):
    return {key: (label, action) for _, options in menu for key, label, action in options}


def main():
    menu = Application().build_menu()
    options = get_options(menu)

    print_menu(menu)
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


if __name__ == '__main__':
    main()
