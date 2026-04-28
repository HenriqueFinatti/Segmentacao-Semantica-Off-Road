import kagglehub
import shutil
import os

DATASETS = {
    "synthetic_offroad": "konrmal94/synthetic-offroad-image-dataset",
    "terrain_attention": "magnumresearchgroup/offroad-terrain-attention-region-images"
}

OUTPUT_DIR = "./data/raw"

def download_and_copy(dataset_name, kaggle_path):
    downloaded_path = kagglehub.dataset_download(kaggle_path)

    destination = os.path.join(OUTPUT_DIR, dataset_name)

    if os.path.exists(destination):
        return

    shutil.copytree(downloaded_path, destination)

def main():
    print("\n======================| Iniciando Downloads do Kaggle |======================\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for name, path in DATASETS.items():
        download_and_copy(name, path)

    print("\n======================| Downloads do Kaggle finalizados |======================\n")

if __name__ == "__main__":
    main()
