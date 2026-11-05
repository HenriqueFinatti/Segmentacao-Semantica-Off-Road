import os
import shutil

from configs import paths

class FreiburgCleaner():

    BASE_DIR = paths.RAW_DIR

    def __init__(self):
        pass


    def delete_tar_files(self):
        for filename in os.listdir(self.BASE_DIR):
            file_path = os.path.join(self.BASE_DIR, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)


    def delete_unused_folders(self):
        for split in ['test', 'train']:
            split_path = os.path.join(paths.FREIBURG_RAW_DIR, split)

            for folder in os.listdir(split_path):
                full_folder_path = os.path.join(split_path, folder)

                if folder not in ['rgb', 'GT_color']:
                    shutil.rmtree(full_folder_path)


