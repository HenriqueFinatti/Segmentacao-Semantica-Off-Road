import os
import shutil

DATASET = './data/raw/synthetic_offroad/dataset'

def clean_files():
    cache_path = os.path.expanduser("~/.cache/kagglehub")

    if os.path.exists(cache_path):
        shutil.rmtree(cache_path, ignore_errors=True)

    for split in ['train', 'test', 'val']:
        shutil.rmtree(f'data/raw/synthetic_offroad/dataset/{split}/mask_labels', ignore_errors=True)

def rename_files():
    splits = ['test', 'train']
    subfolders = ['rgb', 'mask']
    
    for split in splits:
        for subfolder in subfolders:
            current_path = os.path.join(DATASET, split, subfolder)
                        
            for filename in os.listdir(current_path):
                old_file_path = os.path.join(current_path, filename)
                
                name_part, extension = os.path.splitext(filename)

                new_name_part = (name_part.replace("segmentation_", "")
                                         .replace("rgb_", ""))
                
                new_filename = f"{new_name_part}{extension}"
                new_file_path = os.path.join(current_path, new_filename)

                os.rename(old_file_path, new_file_path)

def organize_files():

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
    print("\n-------------------------| Synthetic Offroad |---------------------------\n")

    clean_files()

    rename_files()

    organize_files()