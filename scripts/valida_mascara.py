import numpy as np
from PIL import Image
import os

folder = './data/dataset/train/mask_labels'

images = sorted(os.listdir(folder))[:5]  # verifica as 5 primeiras

for img_name in images:
    arr = np.array(Image.open(os.path.join(folder, img_name)))
    unique = np.unique(arr)
    pct_trail = 100 * (arr == 1).sum() / arr.size
    print(f"{img_name} — valores únicos: {unique} — Trail: {pct_trail:.1f}%")