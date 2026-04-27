import numpy as np
from PIL import Image
import os

# Caminho para uma imagem da pasta mask_label
path = 'new_labels/segmentation_102.png'
mask_label = np.array(Image.open(path))

# Encontra todos os valores únicos de pixels
classes_encontradas = np.unique(mask_label)

print(f"IDs das classes encontrados nesta imagem: {classes_encontradas}")


import matplotlib.pyplot as plt

# Carrega as duas máscaras do mesmo arquivo
m_visual = np.array(Image.open('data/raw/synthetic_offroad/dataset/train/mask/segmentation_102.png'))
m_label = np.array(Image.open('new_labels/segmentation_102.png'))
for id_classe in classes_encontradas:
    coords = np.where(m_label == id_classe)
    y, x = coords[0][0], coords[1][0] # Pega a primeira ocorrência
    cor = m_visual[y, x]
    print(f"ID {id_classe} está associado à cor {cor} na máscara visual.")