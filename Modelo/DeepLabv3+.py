import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T
from torchvision.models.segmentation import deeplabv3_resnet101, DeepLabV3_ResNet101_Weights
from PIL import Image
import os
import numpy as np
from pathlib import Path

# ============================================================================
# 1. DEFINIÇÃO DO DATASET
# ============================================================================
class OffRoadSegmentationDataset(Dataset):
    """
    Dataset customizado para segmentação semântica off-road.
    Carrega imagens RGB e suas máscaras de rótulos correspondentes.
    """
    def __init__(self, rgb_dir, mask_dir, transform=None, mask_transform=None):
        self.rgb_dir = Path(rgb_dir)
        self.mask_dir = Path(mask_dir)
        self.transform = transform
        self.mask_transform = mask_transform
        
        # Listar arquivos RGB
        self.rgb_files = sorted([f for f in self.rgb_dir.iterdir() 
                                  if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
        
    def __len__(self):
        return len(self.rgb_files)
    
    def __getitem__(self, idx):
        # Carregar imagem RGB
        rgb_path = self.rgb_files[idx]
        image = Image.open(rgb_path).convert('RGB')
        
        # Carregar máscara (assumindo mesmo nome do arquivo, mas em pasta diferente)
        mask_filename = rgb_path.stem + '.png'  # Usar .png como padrão
        mask_path = self.mask_dir / mask_filename
        
        if not mask_path.exists():
            # Tentar com outras extensões se necessário
            for ext in ['.jpg', '.jpeg', '.tif', '.tiff']:
                mask_path = self.mask_dir / (rgb_path.stem + ext)
                if mask_path.exists():
                    break
        
        if mask_path.exists():
            mask = Image.open(mask_path)
            # Converter para modo single-channel se necessário
            if mask.mode != 'L':
                mask = mask.convert('L')
        else:
            raise FileNotFoundError(f"Máscara não encontrada: {mask_path}")
        
        # Aplicar transformações
        if self.transform:
            image = self.transform(image)
        
        if self.mask_transform:
            mask = self.mask_transform(mask)
        else:
            mask = T.ToTensor()(mask)
        
        # Converter máscara para tensor long (requerido pelo CrossEntropyLoss)
        mask = (mask * 255).long().squeeze(0)  # Converter de [0, 1] para [0, 255]
        
        return image, mask

# ============================================================================
# 2. DEFINIÇÃO DO MODELO
# ============================================================================
def get_deeplab_model(num_classes=5):
    """
    Cria modelo DeepLabV3+ com backbone ResNet101 pré-treinado.
    
    Args:
        num_classes: Número de classes de segmentação
        
    Returns:
        Modelo DeepLabV3+ ajustado para o número de classes
    """
    weights = DeepLabV3_ResNet101_Weights.DEFAULT
    model = deeplabv3_resnet101(weights=weights)
    
    # Ajustar a última camada para o número de classes
    model.classifier[4] = nn.Conv2d(256, num_classes, kernel_size=(1, 1))
    model.aux_classifier[4] = nn.Conv2d(256, num_classes, kernel_size=(1, 1))
    
    return model

# ============================================================================
# 3. FUNÇÃO DE TREINAMENTO
# ============================================================================
def train_epoch(model, train_loader, optimizer, criterion, device):
    """Treina o modelo por uma época."""
    model.train()
    total_loss = 0.0
    
    for batch_idx, (images, masks) in enumerate(train_loader):
        images = images.to(device)
        masks = masks.to(device)
        
        # Forward pass
        outputs = model(images)
        loss = criterion(outputs['out'], masks)
        
        # Adicionar loss auxiliar (se disponível)
        if outputs.get('aux') is not None:
            aux_loss = criterion(outputs['aux'], masks)
            loss = loss + 0.4 * aux_loss
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
        
        if (batch_idx + 1) % 10 == 0:
            print(f"  Batch [{batch_idx + 1}/{len(train_loader)}] - Loss: {loss.item():.4f}")
    
    avg_loss = total_loss / len(train_loader)
    return avg_loss

# ============================================================================
# 4. CONFIGURAÇÃO E TREINAMENTO
# ============================================================================
def main():
    # Configurações
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Usando dispositivo: {device}")
    
    num_classes = 5  # Ajuste conforme suas classes
    batch_size = 4
    learning_rate = 1e-4
    num_epochs = 30
    
    # Caminhos dos dados
    train_rgb_dir = "../data/dataset/train/rgb"
    train_mask_dir = "../data/dataset/train/mask_labels"
    
    # Transformações
    train_transform = T.Compose([
        T.Resize((512, 512)),
        T.RandomHorizontalFlip(p=0.5),
        T.RandomRotation(degrees=10),
        T.ColorJitter(brightness=0.2, contrast=0.2),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    mask_transform = T.Compose([
        T.Resize((512, 512), interpolation=Image.NEAREST),
    ])
    
    # Criar dataset e dataloader
    print(f"Carregando dataset de: {train_rgb_dir}")
    train_dataset = OffRoadSegmentationDataset(
        rgb_dir=train_rgb_dir,
        mask_dir=train_mask_dir,
        transform=train_transform,
        mask_transform=mask_transform
    )
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,  # Ajuste conforme seu sistema
        pin_memory=True if str(device) == 'cuda' else False
    )
    
    print(f"Total de imagens de treinamento: {len(train_dataset)}")
    
    # Modelo, optimizer e loss
    model = get_deeplab_model(num_classes=num_classes).to(device)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.CrossEntropyLoss(ignore_index=255)
    
    # Scheduler de learning rate
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)
    
    # Treinamento
    print("\nIniciando treinamento...")
    for epoch in range(num_epochs):
        print(f"\nÉpoca {epoch + 1}/{num_epochs}")
        avg_loss = train_epoch(model, train_loader, optimizer, criterion, device)
        scheduler.step()
        
        print(f"Loss médio da época: {avg_loss:.4f}")
        
        # Salvar checkpoint a cada 5 épocas
        if (epoch + 1) % 5 == 0:
            checkpoint_path = f"deeplab_checkpoint_epoch_{epoch + 1}.pth"
            torch.save(model.state_dict(), checkpoint_path)
            print(f"Checkpoint salvo: {checkpoint_path}")
    
    # Salvar modelo final
    final_model_path = "deeplab_model_final.pth"
    torch.save(model.state_dict(), final_model_path)
    print(f"\nModelo final salvo: {final_model_path}")

if __name__ == "__main__":
    main()