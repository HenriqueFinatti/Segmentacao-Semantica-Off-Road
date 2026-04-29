import os
import shutil

OUTPUT_DIR = "./data/raw"
FREIBURG_DATASET = os.path.join(OUTPUT_DIR, 'freiburg_forest_annotated')

def delete_files():
    for filename in os.listdir(OUTPUT_DIR):
        file_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.isfile(file_path):
            os.unlink(file_path)

    for split in ['test', 'train']:
        split_path = os.path.join(FREIBURG_DATASET, split)
        
        for folder in os.listdir(split_path):
            full_folder_path = os.path.join(split_path, folder)
            
            if os.path.isdir(full_folder_path) and folder not in ['rgb', 'GT_color']:
                shutil.rmtree(full_folder_path)

def rename_files():    
    splits = ['test', 'train']
    subfolders = ['rgb', 'GT_color']
    
    for split in splits:
        for subfolder in subfolders:
            current_path = os.path.join(FREIBURG_DATASET, split, subfolder)
                        
            for filename in os.listdir(current_path):
                old_file_path = os.path.join(current_path, filename)
                
                name_part, extension = os.path.splitext(filename)

                new_name_part = (name_part.replace("_mask", "")
                                         .replace("_Clipped", "")
                                         .replace("_clipped", ""))
                
                new_filename = f"{new_name_part}{extension}"
                new_file_path = os.path.join(current_path, new_filename)

                os.rename(old_file_path, new_file_path)

def organize_files():

    splits = ['test', 'train']
    
    for split in splits:

        folder_path = os.path.join(FREIBURG_DATASET, split)
        rgb_path = os.path.join(folder_path, 'rgb')
        segmented_path = os.path.join(folder_path, 'GT_color')

        index = 0
        for image in os.listdir(rgb_path):
            extension = os.path.splitext(image)[1]
            image_name = os.path.splitext(image)[0]

            shutil.copy(os.path.join(rgb_path, image), os.path.join(f'./data/dataset/{split}/rgb', f"Freiburg_Forest_{index}{extension}"))
            shutil.copy(os.path.join(segmented_path, (image_name + '.png')), os.path.join(f'./data/dataset/{split}/mask', f"Freiburg_Forest_{index}.png"))

            index += 1

if __name__ == '__main__':
    print("\n-------------------------| Freiburg Forest |---------------------------\n")

    delete_files()

    rename_files()
    
    organize_files()