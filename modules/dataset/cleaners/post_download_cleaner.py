import os

from configs import paths

class PostDownloadCleaner():

    def __init__(self):
        pass


    def delete_unnecessary_folders(self):
        # raw/ não é mais apagado: guarda os datasets brutos para remontar o dataset sem baixar de novo.
        # Só a segmentação colorida do treino sai, porque as máscaras binárias já foram geradas a partir dela.
        folder = paths.dataset_dir('train', 'original_segmentation')
        if os.path.isdir(folder):
            paths.safe_rmtree(folder)
