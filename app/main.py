from modules.dataset.dataset_service import DatasetService
from modules.training.training_service import TrainingService

dataset_service = DatasetService()
training_service = TrainingService()

if __name__ == '__main__':

    while True:
        print('===================')
        print('1 - Baixar Datasets')
        print('2 - Treinar Modelos')
        print('3 - Processo Completo')
        print('===================')
        op = input('Digite a operação: ')

        if op == '1':
            dataset_service.download_dataset()
            dataset_service.build_dataset()
            dataset_service.post_download_clean()
        
        elif op == '2':
            training_service.train_models()
        
        elif op == '3':
            dataset_service.download_dataset()
            dataset_service.build_dataset()
            dataset_service.post_download_clean()

            training_service.train_models()