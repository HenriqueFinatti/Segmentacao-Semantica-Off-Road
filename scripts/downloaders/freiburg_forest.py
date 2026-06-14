from tqdm import tqdm
import os
import requests
import tarfile
import shutil

OUTPUT_DIR = "./data/raw"
FINAL_FILE = os.path.join(OUTPUT_DIR, "freiburg_forest_annotated.tar.gz")
BASE_URL = "https://deepscene.cs.uni-freiburg.de/static/datasets/"

FILES = [
    "freiburg_forest_annotated.tar.gz.part-aa",
    "freiburg_forest_annotated.tar.gz.part-ab",
    "freiburg_forest_annotated.tar.gz.part-ac"
]

def download_file(url, dest_path):
    headers = {}
    mode = "wb"

    if os.path.exists(dest_path):
        existing_size = os.path.getsize(dest_path)
        headers["Range"] = f"bytes={existing_size}-"
        mode = "ab"
    else:
        existing_size = 0

    response = requests.get(url, headers=headers, stream=True)
    total_size = int(response.headers.get("content-length", 0)) + existing_size

    with open(dest_path, mode) as f, tqdm(
        total=total_size,
        initial=existing_size,
        unit="B",
        unit_scale=True,
        desc=os.path.basename(dest_path),
        bar_format='{desc}: {percentage:3.0f}% |{bar}|'
    ) as pbar:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
                pbar.update(len(chunk))

def merge_files():
    print("Criando arquivo final")

    with open(FINAL_FILE, "wb") as outfile:
        for file_name in FILES:
            part_path = os.path.join(OUTPUT_DIR, file_name)
            with open(part_path, "rb") as infile:
                outfile.write(infile.read())

    print("Descompactando arquivo final")

    with tarfile.open(FINAL_FILE, "r:*") as tar:
        tar.extractall(path=OUTPUT_DIR)

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\n-------------------------| Freiburg Forest |---------------------------\n")
    for file_name in FILES:
        url = BASE_URL + file_name
        dest_path = os.path.join(OUTPUT_DIR, file_name)

        download_file(url, dest_path)

    merge_files()