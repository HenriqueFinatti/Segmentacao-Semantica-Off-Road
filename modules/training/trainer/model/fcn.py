import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models

class FCN(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        
        resnet = models.resnet152(weights='IMAGENET1K_V1')
        
        self.backbone = nn.Sequential(*list(resnet.children())[:-2])
        
        self.classifier = nn.Sequential(
            nn.Conv2d(2048, 512, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1),
            nn.Conv2d(512, num_classes, kernel_size=1)
        )

    def forward(self, x):
        input_size = x.shape[-2:]
        
        x = self.backbone(x)
        x = self.classifier(x)
        x = F.interpolate(x, size=input_size, mode='bilinear', align_corners=False)
        
        return x