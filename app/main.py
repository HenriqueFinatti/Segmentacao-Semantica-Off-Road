from dataset.dataset_service import DatasetService

datasetService = DatasetService()

if __name__ == '__main__':
    datasetService.download_dataset()
    datasetService.build_dataset()