import torch
import numpy as np

class Statistics:
    def __init__(self):
        pass

    def calculate_pixel_accuracy(self, preds, masks):
        with torch.no_grad():
            correct = (preds == masks).sum().item()
            total = masks.numel()
            acc = correct / total
        return acc

    def calculate_mean_iou(self, preds, masks, num_classes=2):
        with torch.no_grad():
            iou_list = []
            for cls in range(num_classes):
                intersection = ((preds == cls) & (masks == cls)).sum().item()
                union = ((preds == cls) | (masks == cls)).sum().item()
                
                if union == 0:
                    iou_list.append(float('nan'))
                else:
                    iou_list.append(intersection / union)
            
            miou = np.nanmean(iou_list)
        return miou