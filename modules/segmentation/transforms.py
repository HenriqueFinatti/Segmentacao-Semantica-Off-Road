from PIL import Image
from torchvision import transforms

# O tamanho vem do settings.json (Image_Size); treino, segmentação e CARLA devem usar o mesmo
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_image_transform(image_size):
    return transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def build_mask_transform(image_size):
    # NEAREST para não criar valores intermediários entre as classes
    return transforms.Resize((image_size, image_size), interpolation=Image.NEAREST)
