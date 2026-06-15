import os
from files.freiburg_forest import FreiburgForest
from files.synthetic_offroad import SyntheticOffroad

def create_dataset_folder():
    os.makedirs("./data/raw", exist_ok=True)

    for split in ['train', 'test']:
        for sub in ['mask', 'new_segmentation', 'original', 'original_segmentation']:
            os.makedirs(f'data/dataset/{split}/{sub}', exist_ok=True)    

if __name__ == '__main__':
    freiburg_forest = FreiburgForest()
    synthetic_offroad = SyntheticOffroad()

    create_dataset_folder()
    
    print('Baixando Freiburg Forest')
    freiburg_forest.download_full_dataset()
    freiburg_forest.delete_unnecessary_files()

    print('Baixando Synthetic Offroad')
    synthetic_offroad.download_full_dataset()

    print('Movendo arquivos para o dataset final')
    synthetic_offroad.move_raw_dataset_to_final_dataset()
    freiburg_forest.move_raw_dataset_to_final_dataset()