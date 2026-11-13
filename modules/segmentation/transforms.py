from PIL import Image
from torchvision import transforms

from configs.settings import Settings

# Lido do settings.json; treino, segmentação e CARLA usam o mesmo tamanho
IMAGE_SIZE = Settings().get_image_size()
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_image_transform():
    return transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def build_mask_transform():
    # NEAREST para não criar valores intermediários entre as classes
    return transforms.Resize((IMAGE_SIZE, IMAGE_SIZE), interpolation=Image.NEAREST)
