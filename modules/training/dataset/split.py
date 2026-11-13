import random
from collections import defaultdict


def dataset_prefix(filename):
    # Freiburg_Forest_12.jpg -> Freiburg_Forest
    return filename.rsplit('_', 1)[0]


def split_train_validation(images, fraction, seed):
    """Separa a validação de dentro do treino, por dataset, para os dois aparecerem na validação.

    A semente fixa garante a mesma divisão em toda execução e para todos os modelos,
    então a comparação entre FCN e DeepLabV3+ usa exatamente as mesmas imagens.
    """
    if fraction <= 0:
        return list(images), []

    groups = defaultdict(list)
    for image in sorted(images):
        groups[dataset_prefix(image)].append(image)

    rng = random.Random(seed)
    train, validation = [], []

    for prefix in sorted(groups):
        group = groups[prefix]
        rng.shuffle(group)

        # Pelo menos uma imagem de validação por dataset, e pelo menos uma de treino
        count = min(max(1, round(len(group) * fraction)), len(group) - 1)

        validation += group[:count]
        train += group[count:]

    return sorted(train), sorted(validation)
