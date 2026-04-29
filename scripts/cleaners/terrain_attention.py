import os
import shutil

DATASET = './data/raw/terrain_attention/TrainingImages/TrainingImages/EnumMasks/png_0_1'

def clean_files():
    # TODO arrumar essa função
    cache_path = os.path.expanduser("~/.cache/kagglehub")

    if os.path.exists(cache_path):
        shutil.rmtree(cache_path, ignore_errors=True)

    for split in ['train', 'test', 'val']:
        shutil.rmtree(f'data/raw/synthetic_offroad/dataset/{split}/mask_labels', ignore_errors=True)

def rename_files():
                    
    for filename in os.listdir(DATASET):
        old_file_path = os.path.join(DATASET, filename)
        
        name_part, extension = os.path.splitext(filename)

        new_name_part = name_part.replace("_P", "")
        
        new_filename = f"{new_name_part}{extension}"
        new_file_path = os.path.join('./data/raw/terrain_attention/TrainingImages/TrainingImages/EnumMasks', new_filename)

        os.rename(old_file_path, new_file_path)

def organize_files():
    # TODO
    splits = ['test', 'train']
    
    for split in splits:

        folder_path = os.path.join(DATASET, split)
        rgb_path = os.path.join(folder_path, 'rgb')
        segmented_path = os.path.join(folder_path, 'mask')

        index = 0
        for image in os.listdir(rgb_path):
            image_name = os.path.splitext(image)[0]

            shutil.copy(os.path.join(rgb_path, image), os.path.join(f'./data/dataset/{split}/rgb', f"Synthetic_Offroad_{index}.png"))
            shutil.copy(os.path.join(segmented_path, (image_name + '.png')), os.path.join(f'./data/dataset/{split}/mask', f"Synthetic_Offroad_{index}.png"))

            index += 1

if __name__ == '__main__':
    print("\n-------------------------| Terrain Attention |---------------------------\n")

    clean_files()

    rename_files()

    # organize_files()