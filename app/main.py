import time
from modules.dataset.dataset_service import DatasetService
from modules.training.training_service import TrainingService
from modules.segmentation.segmentation_service import SegmentationService

dataset_service = DatasetService()
training_service = TrainingService()
segmentation_service = SegmentationService()

def format_time(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:02d}h {mins:02d}m {secs:05.2f}s"

if __name__ == '__main__':

    print('===================')
    print('1 - Baixar Datasets')
    print('2 - Treinar Modelos')
    print('3 - Processo Completo')
    print('4 - Segmentar Imagens')
    print('===================')
    op = input('Digite a operação: ')
    print('\n')

    if op == '1':
        start_time = time.perf_counter()

        dataset_service.download_dataset()
        dataset_service.build_dataset()
        dataset_service.post_download_clean()

        elapsed = time.perf_counter() - start_time
        print(f"\n[METRICA] Tempo total do Dataset: {format_time(elapsed)}")

    elif op == '2':
        start_time = time.perf_counter()

        training_service.train_models()

        elapsed = time.perf_counter() - start_time
        print(f"\n[METRICA] Tempo total do Treinamento: {format_time(elapsed)}")

    elif op == '3':
        total_start = time.perf_counter()

        # Dataset steps
        dataset_start = time.perf_counter()
        dataset_service.download_dataset()
        dataset_service.build_dataset()
        dataset_service.post_download_clean()
        dataset_elapsed = time.perf_counter() - dataset_start
        print(f"\n[METRICA] Etapa do Dataset concluída em: {format_time(dataset_elapsed)}")

        # Training steps
        training_start = time.perf_counter()
        training_service.train_models()
        training_elapsed = time.perf_counter() - training_start
        print(f"\n[METRICA] Etapa de Treinamento concluída em: {format_time(training_elapsed)}")

        total_elapsed = time.perf_counter() - total_start
        print(f"\n[METRICA] Processo Completo finalizado em: {format_time(total_elapsed)}")

    elif op == '4':
        start_time = time.perf_counter()

        segmentation_service.segment_images()

        elapsed = time.perf_counter() - start_time
        print(f"\n[METRICA] Tempo total da Segmentação: {format_time(elapsed)}")