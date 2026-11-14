from typing import TypedDict
import numpy as np


class DatasetLabel(TypedDict):
    # Uma ou mais cores que contam como trilha (ex.: CaSSeD tem trilha lisa e trilha irregular)
    colors: np.ndarray
    label: str
    tolerance: int