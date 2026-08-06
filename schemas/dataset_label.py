from typing import TypedDict
import numpy as np


class DatasetLabel(TypedDict):
    color: np.ndarray
    label: str
    tolerance: int