import numpy as np

# Métricas de segmentação binária a partir da matriz de confusão (TP, FP, FN, TN), com a trilha como classe positiva.
# Usadas na validação durante o treino e na avaliação do dataset de teste, para as duas serem comparáveis.


def confusion_counts(prediction, truth):
    """prediction e truth: arrays booleanos (numpy) do mesmo tamanho, True = trilha."""
    return {
        'tp': int(np.sum(prediction & truth)),
        'fp': int(np.sum(prediction & ~truth)),
        'fn': int(np.sum(~prediction & truth)),
        'tn': int(np.sum(~prediction & ~truth)),
    }


def confusion_counts_torch(preds, masks):
    """preds e masks: tensores de classes (0 = fundo, 1 = trilha), em qualquer dispositivo."""
    prediction = preds == 1
    truth = masks == 1
    return {
        'tp': int((prediction & truth).sum().item()),
        'fp': int((prediction & ~truth).sum().item()),
        'fn': int((~prediction & truth).sum().item()),
        'tn': int((~prediction & ~truth).sum().item()),
    }


def add_counts(total, counts):
    for key, value in counts.items():
        total[key] = total.get(key, 0) + value
    return total


def divide(numerator, denominator):
    # nan quando a métrica não se aplica (ex.: precisão sem nenhum pixel previsto como trilha)
    return numerator / denominator if denominator > 0 else float('nan')


def compute_metrics(counts):
    tp, fp, fn, tn = counts['tp'], counts['fp'], counts['fn'], counts['tn']

    iou_trail = divide(tp, tp + fp + fn)
    iou_background = divide(tn, tn + fp + fn)

    return {
        'acuracia': divide(tp + tn, tp + fp + fn + tn),
        'iou_trilha': iou_trail,
        'iou_fundo': iou_background,
        'miou': float(np.nanmean([iou_trail, iou_background])),
        'precisao': divide(tp, tp + fp),
        'recall': divide(tp, tp + fn),
        'f1': divide(2 * tp, 2 * tp + fp + fn),
    }
