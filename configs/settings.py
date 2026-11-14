import json
import numpy as np

from configs import paths
from schemas.dataset_label import DatasetLabel
from schemas.settings_config import SettingsConfig

class Settings():

    def __init__(self):
        with open(paths.SETTINGS_FILE, 'r', encoding='utf-8') as settings:
            self.settings: SettingsConfig = json.load(settings)


    def is_early_stopping_on(self) -> bool:
        return self.settings['EarlyStopping']


    def is_charts_on(self) -> bool:
        return self.settings['Charts']


    def is_test_execution_on(self) -> bool:
        return self.settings['Test_Execution']


    def get_epochs(self) -> int:
        return self.settings['Epochs']


    def get_patience(self) -> int:
        return self.settings['Patience']


    def get_batch_size(self) -> int:
        return self.settings['BATCH_SIZE']


    def get_image_size(self) -> int:
        return self.settings['Image_Size']


    def get_learning_rate(self) -> float:
        return self.settings['Learning_Rate']


    def get_class_weights(self) -> list[float]:
        return self.settings['Class_Weights']


    def get_num_workers(self) -> int:
        return self.settings['Num_Workers']


    def get_test_execution_images(self) -> int:
        return self.settings['Test_Execution_Images']


    def get_test_execution_epochs(self) -> int:
        return self.settings['Test_Execution_Epochs']


    def get_validation_split(self) -> float:
        return self.settings['Validation_Split']


    def get_seed(self) -> int:
        return self.settings['Seed']


    def get_cassed_test_trails(self) -> list[str]:
        return self.settings['CaSSeD_Test_Trails']


    def get_dataset_labels(self) -> dict[str, DatasetLabel]:
        dataset_labels = self.settings['Datasets_Labels']

        for dataset in dataset_labels.values():
            # (N, 3): cada linha é uma cor que conta como trilha
            dataset["colors"] = np.array(dataset["colors"], dtype=np.uint8).reshape(-1, 3)

        return dataset_labels


    def is_dataset_on(self, name) -> bool:
        # Cada dataset de Datasets_Labels é ligado pela chave de mesmo nome no settings.json
        if name not in self.settings:
            raise KeyError(f"Falta a chave '{name}' (true/false) no settings.json para ligar ou desligar esse dataset.")

        return self.settings[name]


    def get_enabled_datasets(self) -> list[str]:
        return [name for name in self.settings['Datasets_Labels'] if self.is_dataset_on(name)]