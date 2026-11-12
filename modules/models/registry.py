from modules.models.deeplabv3 import DeepLabV3Plus
from modules.models.fcn import FCN

NUM_CLASSES = 2

MODELS = {
    'fcn': FCN,
    'deeplabv3+': DeepLabV3Plus,
}


def build_model(name, pretrained=True):
    return MODELS[name](num_classes=NUM_CLASSES, pretrained=pretrained)
