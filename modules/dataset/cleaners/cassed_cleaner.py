import os

from configs import paths

# O que não usamos do CaSSeD:
#   ROSBAGS        gravações brutas do veículo (~57 GB)
#   Synthetic_Data imagens do simulador MAVS: vegetação densa, rótulos ruidosos e sem trilha clara
#   Train e Test   cópias renumeradas de Main_Trail, Brown_field e Powerline (mesmos pixels e rótulos)
UNUSED_FOLDERS = [
    os.path.join('Real_World_data', 'ROSBAGS'),
    'Synthetic_Data',
    os.path.join('Real_World_data', 'Train'),
    os.path.join('Real_World_data', 'Test'),
]
UNUSED_FILES = ['readme.rtf']


class CaSSeDCleaner():

    def __init__(self):
        pass


    def check_raw_dataset(self):
        # Ainda não há downloader: a pasta precisa ter sido copiada para raw/ antes
        if not os.path.isdir(paths.CASSED_RAW_DIR):
            raise FileNotFoundError(
                f"CaSSeD não encontrado em {paths.relative(paths.CASSED_RAW_DIR)}. Copie para lá a pasta "
                f"CaSSed_Dataset extraída do CaSSeD.tar.gz (basta Real_World_data, sem ROSBAGS)."
            )


    def delete_unused_data(self):
        self.check_raw_dataset()

        # Pastas ausentes são ignoradas, para aceitar uma cópia só com o necessário
        for folder in UNUSED_FOLDERS:
            folder_path = os.path.join(paths.CASSED_RAW_DIR, folder)
            if os.path.isdir(folder_path):
                print(f"Apagando {paths.relative(folder_path)}")
                paths.safe_rmtree(folder_path)

        for file in UNUSED_FILES:
            file_path = os.path.join(paths.CASSED_RAW_DIR, file)
            if os.path.isfile(file_path):
                os.unlink(paths.ensure_inside_root(file_path))
