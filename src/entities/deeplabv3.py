import torchvision.models as models
import torch
import torch.nn as nn
import torch.nn.functional as F

class DeepLabV3Plus(nn.Module):
    def __init__(self, num_classes):
        super().__init__()

        resnet = models.resnet152(weights='IMAGENET1K_V1')
        self.backbone_low   = nn.Sequential(*list(resnet.children())[:5])
        self.backbone_high  = nn.Sequential(*list(resnet.children())[5:8])
        self.aspp           = ASPP(2048, 256)

        self.low_level_conv = nn.Sequential(
            nn.Conv2d(256, 48, 1, bias=False),
            nn.BatchNorm2d(48), nn.ReLU()
        )
        
        self.final_conv = nn.Sequential(
            nn.Conv2d(304, 256, 3, padding=1, bias=False),
            nn.BatchNorm2d(256), nn.ReLU(),
            nn.Conv2d(256, 256, 3, padding=1, bias=False),
            nn.BatchNorm2d(256), nn.ReLU(),
            nn.Conv2d(256, num_classes, 1)
        )

    def forward(self, x):
        size = x.shape[-2:]
        low  = self.backbone_low(x)
        high = self.backbone_high(low)
        x    = self.aspp(high)
        x    = F.interpolate(x, size=low.shape[-2:], mode='bilinear', align_corners=False)
        low  = self.low_level_conv(low)
        x    = torch.cat([x, low], dim=1)
        x    = self.final_conv(x)
        return F.interpolate(x, size=size, mode='bilinear', align_corners=False)


class ASPP(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=6,  dilation=6,  bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )
        self.conv3 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=12, dilation=12, bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )
        self.conv4 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=18, dilation=18, bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )
        self.pool = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )
        self.project = nn.Sequential(
            nn.Conv2d(out_channels * 5, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )

    def forward(self, x):
        size = x.shape[-2:]
        feats = [
            self.conv1(x),
            self.conv2(x),
            self.conv3(x),
            self.conv4(x),
            F.interpolate(self.pool(x), size=size, mode='bilinear', align_corners=False)
        ]
        return self.project(torch.cat(feats, dim=1))
