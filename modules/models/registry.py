from modules.models.deeplabv3 import DeepLabV3Plus
from modules.models.fcn import FCN

NUM_CLASSES = 2

MODELS = {
    'fcn': FCN,
    'deeplabv3+': DeepLabV3Plus,
}


def model_name(name):
    # Aceita 'FCN' ou 'fcn' e falha com uma mensagem clara para nomes desconhecidos
    normalized = name.lower()

    if normalized not in MODELS:
        raise ValueError(f"Modelo desconhecido: {name}. Modelos disponíveis: {', '.join(MODELS)}")

    return normalized


def build_model(name, pretrained=True):
    return MODELS[model_name(name)](num_classes=NUM_CLASSES, pretrained=pretrained)
