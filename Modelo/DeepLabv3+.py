# Importando as "ferramentas" necessárias para o projeto
import os
import torch
import numpy as np
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import torch.nn as nn
import torch.nn.functional as F

# =========================
# DATASET (O Organizador de Arquivos)
# =========================
# Esta classe funciona como um bibliotecário que sabe onde as fotos estão
# e como entregá-las prontas para o computador estudar.
class OffRoadDataset(Dataset):
    def __init__(self, root_dir, transform=None, filter_freiburg=False):
        # Define onde estão as fotos originais (RGB) e os gabaritos (Masks)
        self.rgb_dir = os.path.join(root_dir, "rgb")
        self.mask_dir = os.path.join(root_dir, "mask_labels")

        # Verifica se as pastas realmente existem para evitar erros
        if not os.path.exists(self.rgb_dir):
            raise FileNotFoundError(f"RGB dir não existe: {self.rgb_dir}")
        if not os.path.exists(self.mask_dir):
            raise FileNotFoundError(f"Mask dir não existe: {self.mask_dir}")

        # Cria uma lista com os nomes de todas as imagens disponíveis
        self.images = sorted(os.listdir(self.rgb_dir))

        # Se quisermos focar apenas em um tipo específico de floresta, filtramos aqui
        if filter_freiburg:
            self.images = [img for img in self.images if 'freiburg_forest' in img.lower()]

        self.transform = transform

    def __len__(self):
        # Diz ao computador quantas imagens temos no total
        return len(self.images)

    def __getitem__(self, idx):
        # Pega uma imagem específica da lista pelo seu número de identificação (índice)
        img_name = self.images[idx]
        img_path = os.path.join(self.rgb_dir, img_name)

        # Encontra a "máscara" (o desenho que diz o que é pista e o que não é) correspondente
        base = os.path.splitext(img_name)[0]
        mask_path = os.path.join(self.mask_dir, base + ".png")

        if not os.path.exists(mask_path):
            raise FileNotFoundError(f"Máscara não encontrada: {mask_path}")

        # Abre a imagem colorida e a máscara (em tons de cinza)
        image = Image.open(img_path).convert("RGB")
        mask = Image.open(mask_path).convert("L")

        if self.transform:
            # Padroniza o tamanho e o formato da imagem
            image = self.transform(image)

            # Ajusta a máscara para o mesmo tamanho, sem borrar as bordas
            mask = transforms.Resize((512, 512), interpolation=Image.NEAREST)(mask)
            mask = np.array(mask)

            # Transforma tudo que não é preto em "1" e o que é preto em "0"
            # Isso cria uma separação simples entre o caminho e os obstáculos
            mask = (mask > 0).astype(np.int64)

            # Converte para o formato que o "cérebro" eletrônico entende (Tensor)
            mask = torch.as_tensor(mask, dtype=torch.long)

        return image, mask


# =========================
# TRANSFORM (O Padronizador)
# =========================
# Antes de estudar, todas as fotos precisam ter o mesmo tamanho e "brilho"
# para que o computador não se confunda.
transform = transforms.Compose([
    transforms.Resize((512, 512)), # Deixa todas as fotos com o mesmo tamanho
    transforms.ToTensor(),         # Transforma a imagem em números
    transforms.Normalize(mean=[0.485, 0.456, 0.406], # Ajusta as cores para um padrão mundial
                         std=[0.229, 0.224, 0.225])
])


# =========================
# MODELO (O "Cérebro" da IA)
# =========================

# ASPP: Imagine como várias lentes de aumento diferentes
# Algumas olham detalhes pequenos, outras olham o cenário todo de uma vez.
class ASPP(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()

        # Diferentes tipos de filtros que olham para a imagem com "zooms" variados
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )

        self.conv2 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=6, dilation=6, bias=False),
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

        # Olha para a imagem de uma forma bem genérica (resumo global)
        self.pool = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )

        # Junta todas essas visões diferentes em uma só resposta
        self.project = nn.Sequential(
            nn.Conv2d(out_channels * 5, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels), nn.ReLU()
        )

    def forward(self, x):
        size = x.shape[-2:]

        # Combina o que cada "lente" viu
        feats = [
            self.conv1(x),
            self.conv2(x),
            self.conv3(x),
            self.conv4(x),
            F.interpolate(self.pool(x), size=size, mode='bilinear', align_corners=False)
        ]

        return self.project(torch.cat(feats, dim=1))

# DeepLabV3Plus: É o mestre que combina os detalhes finos (bordas) 
# com o entendimento geral (onde está o caminho).
class DeepLabV3Plus(nn.Module):
    def __init__(self, num_classes):
        super().__init__()

        import torchvision.models as models
        # Usa um modelo ResNet152 (um cérebro já pré-treinado muito potente)
        resnet = models.resnet152(weights='IMAGENET1K_V1')

        # Divide o cérebro em duas partes: uma que vê detalhes e outra que vê conceitos
        self.backbone_low = nn.Sequential(*list(resnet.children())[:5])
        self.backbone_high = nn.Sequential(*list(resnet.children())[5:8])

        self.aspp = ASPP(2048, 256) # Analisa a imagem em várias escalas

        self.low_level_conv = nn.Sequential(
            nn.Conv2d(256, 48, 1, bias=False),
            nn.BatchNorm2d(48), nn.ReLU()
        )

        # Camada final que decide a qual classe cada pixel pertence (ex: estrada ou árvore)
        self.final_conv = nn.Sequential(
            nn.Conv2d(304, 256, 3, padding=1, bias=False),
            nn.BatchNorm2d(256), nn.ReLU(),
            nn.Conv2d(256, 256, 3, padding=1, bias=False),
            nn.BatchNorm2d(256), nn.ReLU(),
            nn.Conv2d(256, num_classes, 1)
        )

    def forward(self, x):
        size = x.shape[-2:]

        # Extrai características da imagem em níveis diferentes
        low = self.backbone_low(x)
        high = self.backbone_high(low)

        # Processa a visão de alto nível e aumenta o tamanho para combinar com a de baixo nível
        x = self.aspp(high)
        x = F.interpolate(x, size=low.shape[-2:], mode='bilinear', align_corners=False)

        low = self.low_level_conv(low)

        # Junta as texturas detalhadas com a localização dos objetos
        x = torch.cat([x, low], dim=1)
        x = self.final_conv(x)

        # Devolve a imagem com o "mapa" colorido no tamanho original
        return F.interpolate(x, size=size, mode='bilinear', align_corners=False)


# =========================
# TREINO (A Sessão de Estudo)
# =========================
# Verifica se o computador tem uma placa de vídeo (GPU) para estudar mais rápido
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Cria a inteligência artificial para distinguir 2 coisas (chão ou não-chão)
model = DeepLabV3Plus(num_classes=2).to(device)

# Define como a IA será punida pelos erros (Criterion) e como ela vai melhorar (Optimizer)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)


# Prepara o dataset e o DataLoader antes do treinamento e teste
dataset = OffRoadDataset('data/dataset/train', transform, filter_freiburg=True)
loader = DataLoader(dataset, batch_size=4, shuffle=True)

def train_one_epoch(loader):
    # Coloca o modelo em "modo de aprendizado"
    model.train()

    for images, masks in loader:
        images = images.to(device)
        masks = masks.to(device)

        # Limpa o que aprendeu no passo anterior para não confundir
        optimizer.zero_grad()

        # Faz uma tentativa de adivinhar onde está a pista
        outputs = model(images)
        # Calcula o quão longe a tentativa foi do gabarito real
        loss = criterion(outputs, masks)

        # Aprende com o erro e ajusta os "neurônios"
        loss.backward()
        optimizer.step()


# =========================
# TREINAR POR 5 ÉPOCAS
# =========================
num_epochs = 5
for epoch in range(num_epochs):
    print(f"Epoch {epoch + 1}/{num_epochs}")
    train_one_epoch(loader)


# =========================
# TESTE (O Exame Final)
# =========================
# Prepara os dados de treinamento e teste
dataset = OffRoadDataset('data/dataset/train', transform, filter_freiburg=True)
loader = DataLoader(dataset, batch_size=4, shuffle=True)

print(f"Total imagens: {len(dataset)}")

# Coloca o modelo em "modo de prova" (apenas executa, não aprende mais)
model.eval()

# Desliga o aprendizado para economizar memória
with torch.no_grad():
    for images, masks in loader:
        images = images.to(device)

        # Pede para a IA classificar uma imagem que ela nunca viu
        outputs = model(images)  
        # Pega a classe com maior pontuação para cada pixel (a aposta da IA)
        preds = torch.argmax(outputs, dim=1)  

        # Mostra o tamanho das informações processadas
        print("Input:", images.shape) # Foto original
        print("Output:", outputs.shape) # Mapa de probabilidades
        print("Pred:", preds.shape) # Mapa final decidido
        break # Para após o primeiro teste apenas para demonstração

# =========================
# SALVAR IMAGENS SEGMENTADAS (Versão Corrigida)
# =========================
output_dir = 'data/dataset/train/mask'
os.makedirs(output_dir, exist_ok=True)

model.eval()
global_idx = 0 # Contador para saber exatamente qual foto estamos processando

with torch.no_grad():
    # Usamos shuffle=False aqui para manter a ordem da lista do dataset
    test_loader = DataLoader(dataset, batch_size=4, shuffle=False)
    
    for images, _ in test_loader:
        images = images.to(device)
        outputs = model(images)
        preds = torch.argmax(outputs, dim=1).cpu().numpy()

        for i in range(preds.shape[0]):
            # Pega o nome real da imagem usando o contador global
            img_name = dataset.images[global_idx]
            output_path = os.path.join(output_dir, img_name)

            # Transforma o resultado (0 e 1) em algo visível (0 e 255)
            # Se você tiver mais de 2 classes, multiplique por (255 // num_classes)
            rescale_factor = 255 if model.final_conv[-1].out_channels == 2 else 30
            pred_img = Image.fromarray((preds[i] * rescale_factor).astype(np.uint8))
            
            pred_img.save(output_path)
            global_idx += 1 

    print(f"Sucesso! {global_idx} imagens segmentadas salvas em: {output_dir}")