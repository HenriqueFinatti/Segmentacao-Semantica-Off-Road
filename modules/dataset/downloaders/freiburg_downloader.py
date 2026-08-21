import os
import requests
import tarfile

class FreiburgDownloader():

    BASE_DIR = "./data/raw"
    FINAL_FILE = os.path.join(BASE_DIR, "freiburg_forest_annotated.tar.gz")
    BASE_URL = "https://deepscene.cs.uni-freiburg.de/static/datasets/"

    FILES = [
        "freiburg_forest_annotated.tar.gz.part-aa",
        "freiburg_forest_annotated.tar.gz.part-ab",
        "freiburg_forest_annotated.tar.gz.part-ac"
    ]

    def __init__(self):
        pass


    def download_dataset(self):
        os.makedirs(self.BASE_DIR, exist_ok=True)

        for file_name in self.FILES:
            url = self.BASE_URL + file_name
            dest_path = os.path.join(self.BASE_DIR, file_name)

            self.download_file(url, dest_path)
        self.merge_files()


    def download_file(self, url, dest_path):
        headers = {}
        mode = "wb"

        response = requests.get(url, headers=headers, stream=True)

        with open(dest_path, mode) as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    

    def merge_files(self):
        with open(self.FINAL_FILE, "wb") as outfile:
            for file_name in self.FILES:
                part_path = os.path.join(self.BASE_DIR, file_name)
                with open(part_path, "rb") as infile:
                    outfile.write(infile.read())

        with tarfile.open(self.FINAL_FILE, "r:*") as tar:
            tar.extractall(path=self.BASE_DIR)
