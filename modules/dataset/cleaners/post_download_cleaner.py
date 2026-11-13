from configs import paths

class PostDownloadCleaner():
    RAW_DATASET = paths.RAW_DIR

    def __init__(self):
        pass


    def delete_raw_dataset(self):
        paths.safe_rmtree(self.RAW_DATASET)


    def delete_unnecessary_folders(self):
        paths.safe_rmtree(paths.dataset_dir('train', 'original_segmentation'))