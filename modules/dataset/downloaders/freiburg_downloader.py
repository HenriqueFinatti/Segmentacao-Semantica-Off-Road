import os
import requests
import tarfile

from configs import paths

class FreiburgDownloader():

    BASE_DIR = paths.RAW_DIR
    FINAL_FILE = os.path.join(BASE_DIR, "freiburg_forest_annotated.tar.gz")
    BASE_URL = "https://deepscene.cs.uni-freiburg.de/static/datasets/"

    FILES = [
        "freiburg_forest_annotated.tar.gz.part-aa",
        "freiburg_forest_annotated.tar.gz.part-ab",
        "freiburg_forest_annotated.tar.gz.part-ac"
    ]

    def __init__(self):
        pass


    def download_dataset(self, on_progress=None):
        """on_progress(parte, total_de_partes, bytes_baixados, bytes_da_parte) acompanha o download."""
        os.makedirs(self.BASE_DIR, exist_ok=True)

        for index, file_name in enumerate(self.FILES):
            url = self.BASE_URL + file_name
            dest_path = os.path.join(self.BASE_DIR, file_name)

            part_progress = None
            if on_progress:
                part_progress = lambda done, total, index=index: on_progress(index + 1, len(self.FILES), done, total)

            self.download_file(url, dest_path, part_progress)
        self.merge_files()


    def download_file(self, url, dest_path, on_progress=None):
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        total = int(response.headers.get('content-length', 0))
        done = 0

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    done += len(chunk)
                    if on_progress:
                        on_progress(done, total)


    def merge_files(self):
        with open(self.FINAL_FILE, "wb") as outfile:
            for file_name in self.FILES:
                part_path = os.path.join(self.BASE_DIR, file_name)
                with open(part_path, "rb") as infile:
                    outfile.write(infile.read())

        with tarfile.open(self.FINAL_FILE, "r:*") as tar:
            tar.extractall(path=self.BASE_DIR)
