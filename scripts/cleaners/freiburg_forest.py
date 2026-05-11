import os
import shutil

OUTPUT_DIR = "./data/raw"
FREIBURG_DATASET = os.path.join(OUTPUT_DIR, 'freiburg_forest_annotated')

# CORREÇÃO: cria todas as pastas necessárias antes de copiar os arquivos
def create_folders():
    for split in ['test', 'train']:
        os.makedirs(f'./data/dataset/{split}/rgb',        exist_ok=True)
        os.makedirs(f'./data/dataset/{split}/gt_color',   exist_ok=True)  # guarda GT original
        os.makedirs(f'./data/dataset/{split}/mask_labels', exist_ok=True)  # gabarito binário (gerado no script 3)

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
        folder_path    = os.path.join(FREIBURG_DATASET, split)
        rgb_path       = os.path.join(folder_path, 'rgb')
        segmented_path = os.path.join(folder_path, 'GT_color')

        index = 0
        for image in sorted(os.listdir(rgb_path)):  # sorted garante ordem consistente
            extension  = os.path.splitext(image)[1]
            image_name = os.path.splitext(image)[0]

            src_rgb  = os.path.join(rgb_path, image)
            src_mask = os.path.join(segmented_path, image_name + '.png')

            dst_rgb  = f'./data/dataset/{split}/rgb/Freiburg_Forest_{index}{extension}'
            # CORREÇÃO: GT_color vai para gt_color/, não para mask/
            # mask_labels/ será gerada pelo script 3 a partir do gt_color/
            dst_mask = f'./data/dataset/{split}/gt_color/Freiburg_Forest_{index}.png'

            if not os.path.exists(src_mask):
                print(f"  ⚠ Máscara não encontrada para {image}, pulando...")
                continue

            shutil.copy(src_rgb,  dst_rgb)
            shutil.copy(src_mask, dst_mask)

            index += 1

        print(f"  ✓ {split}: {index} pares rgb/gt_color copiados")

if __name__ == '__main__':
    print("\n-------------------------| Freiburg Forest |---------------------------\n")
    create_folders()
    delete_files()
    rename_files()
    organize_files()
    print("\nOrganização concluída!")