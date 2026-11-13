from typing import TypedDict

from schemas.dataset_label import DatasetLabel


class SettingsConfig(TypedDict):
    EarlyStopping: bool
    Test_Execution: bool
    Freiburg_Forest: bool
    Synthetic_Offroad: bool
    Charts: bool
    Epochs: int
    Patience: int
    BATCH_SIZE: int
    Image_Size: int
    Learning_Rate: float
    Class_Weights: list[float]
    Num_Workers: int
    Test_Execution_Images: int
    Test_Execution_Epochs: int
    Datasets_Labels: dict[str, DatasetLabel]
