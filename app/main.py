from dataset.dataset_service import DatasetService
from training.training_service import TrainingService

dataset_service = DatasetService()
training_service = TrainingService()

if __name__ == '__main__':
    # dataset_service.download_dataset()
    # dataset_service.build_dataset()

    training_service.train_models()