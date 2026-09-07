import shutil

class PostDownloadCleaner():
    RAW_DATASET = './raw/'

    def __init__(self):
        pass


    def delete_raw_dataset(self):
        shutil.rmtree(self.RAW_DATASET)