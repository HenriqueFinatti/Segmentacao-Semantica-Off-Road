from typing import TypedDict

from schemas.dataset_label import DatasetLabel


class SettingsConfig(TypedDict):
    EarlyStopping: bool
    Charts: bool
    Freiburg_Forest: bool
    Synthetic_Offroad: bool
    Epochs: int
    Patience: int
    Dataset_Labels: dict[str, DatasetLabel]