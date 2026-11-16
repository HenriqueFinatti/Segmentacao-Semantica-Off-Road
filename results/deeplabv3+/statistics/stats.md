### Configuração do Treinamento

| Parâmetro | Valor |
|-----------|-------|
| Modelo | DEEPLABV3+ |
| Dispositivo | NVIDIA GeForce RTX 3080 |
| Execução de Teste | Não |
| Datasets | Freiburg_Forest, Synthetic_Offroad, CaSSeD |
| Imagens de Treino | 5053 |
| Imagens de Validação | 891 (15% de cada dataset, seed 42) |
| Seleção do Modelo | mIoU de validação |
| Tamanho da Imagem | 512x512 |
| Batch Size | 4 |
| Épocas (máximo) | 200 |
| Early Stopping | Sim (paciência 5) |
| Learning Rate | 0.0001 |
| Pesos das Classes | [1.0, 9.0] |
| Num Workers | 2 |
| Otimizador | Adam |

### Épocas
DEEPLABV3+: Época 1
Treino    | Loss: 0.0586 | Acurácia: 96.82% | mIoU: 0.9094 | Tempo da Época: 3m 34.74s
Validação | Loss: 0.0308 | Acurácia: 98.01% | mIoU: 0.9410 | IoU Trilha: 0.9067 | F1: 0.9511


DEEPLABV3+: Época 2
Treino    | Loss: 0.0349 | Acurácia: 97.95% | mIoU: 0.9377 | Tempo da Época: 3m 34.68s
Validação | Loss: 0.0519 | Acurácia: 96.22% | mIoU: 0.8948 | IoU Trilha: 0.8364 | F1: 0.9109


DEEPLABV3+: Época 3
Treino    | Loss: 0.0308 | Acurácia: 98.18% | mIoU: 0.9441 | Tempo da Época: 3m 34.61s
Validação | Loss: 0.0244 | Acurácia: 98.57% | mIoU: 0.9567 | IoU Trilha: 0.9311 | F1: 0.9643


DEEPLABV3+: Época 4
Treino    | Loss: 0.0243 | Acurácia: 98.51% | mIoU: 0.9536 | Tempo da Época: 3m 34.71s
Validação | Loss: 0.0230 | Acurácia: 98.49% | mIoU: 0.9543 | IoU Trilha: 0.9274 | F1: 0.9623


DEEPLABV3+: Época 5
Treino    | Loss: 0.0225 | Acurácia: 98.61% | mIoU: 0.9568 | Tempo da Época: 3m 34.59s
Validação | Loss: 0.0293 | Acurácia: 98.46% | mIoU: 0.9535 | IoU Trilha: 0.9261 | F1: 0.9616


DEEPLABV3+: Época 6
Treino    | Loss: 0.0251 | Acurácia: 98.44% | mIoU: 0.9522 | Tempo da Época: 3m 34.45s
Validação | Loss: 0.0212 | Acurácia: 98.85% | mIoU: 0.9646 | IoU Trilha: 0.9436 | F1: 0.9710


DEEPLABV3+: Época 7
Treino    | Loss: 0.0199 | Acurácia: 98.74% | mIoU: 0.9609 | Tempo da Época: 3m 34.47s
Validação | Loss: 0.0312 | Acurácia: 98.06% | mIoU: 0.9422 | IoU Trilha: 0.9085 | F1: 0.9520


DEEPLABV3+: Época 8
Treino    | Loss: 0.0193 | Acurácia: 98.78% | mIoU: 0.9616 | Tempo da Época: 3m 34.46s
Validação | Loss: 0.0195 | Acurácia: 98.75% | mIoU: 0.9620 | IoU Trilha: 0.9394 | F1: 0.9687


DEEPLABV3+: Época 9
Treino    | Loss: 0.0166 | Acurácia: 98.93% | mIoU: 0.9661 | Tempo da Época: 3m 34.53s
Validação | Loss: 0.0202 | Acurácia: 98.61% | mIoU: 0.9579 | IoU Trilha: 0.9330 | F1: 0.9653


DEEPLABV3+: Época 10
Treino    | Loss: 0.0221 | Acurácia: 98.66% | mIoU: 0.9588 | Tempo da Época: 3m 34.48s
Validação | Loss: 0.0219 | Acurácia: 98.84% | mIoU: 0.9644 | IoU Trilha: 0.9432 | F1: 0.9708


DEEPLABV3+: Época 11
Treino    | Loss: 0.0160 | Acurácia: 98.96% | mIoU: 0.9673 | Tempo da Época: 3m 34.41s
Validação | Loss: 0.0198 | Acurácia: 99.08% | mIoU: 0.9716 | IoU Trilha: 0.9545 | F1: 0.9767


DEEPLABV3+: Época 12
Treino    | Loss: 0.0170 | Acurácia: 98.93% | mIoU: 0.9660 | Tempo da Época: 3m 34.47s
Validação | Loss: 0.0194 | Acurácia: 98.87% | mIoU: 0.9655 | IoU Trilha: 0.9449 | F1: 0.9717


DEEPLABV3+: Época 13
Treino    | Loss: 0.0145 | Acurácia: 99.05% | mIoU: 0.9698 | Tempo da Época: 3m 34.35s
Validação | Loss: 0.0205 | Acurácia: 98.63% | mIoU: 0.9585 | IoU Trilha: 0.9339 | F1: 0.9658


DEEPLABV3+: Época 14
Treino    | Loss: 0.0149 | Acurácia: 99.03% | mIoU: 0.9693 | Tempo da Época: 3m 34.30s
Validação | Loss: 0.0222 | Acurácia: 98.78% | mIoU: 0.9629 | IoU Trilha: 0.9408 | F1: 0.9695


DEEPLABV3+: Época 15
Treino    | Loss: 0.0168 | Acurácia: 98.97% | mIoU: 0.9672 | Tempo da Época: 3m 34.38s
Validação | Loss: 0.0206 | Acurácia: 98.89% | mIoU: 0.9659 | IoU Trilha: 0.9456 | F1: 0.9721


DEEPLABV3+: Época 16
Treino    | Loss: 0.0127 | Acurácia: 99.17% | mIoU: 0.9733 | Tempo da Época: 3m 34.39s
Validação | Loss: 0.0243 | Acurácia: 98.93% | mIoU: 0.9671 | IoU Trilha: 0.9475 | F1: 0.9730


### Resultados Finais DEEPLABV3+
---

#### Resumo de Tempo e Épocas
- **Total de Épocas:** 16
- **Tempo Total:** 57m 13s
- **Tempo Médio por Época:** 3m 34s

#### Tabela de Métricas
| Métrica | Melhor | Média | Final (Última) |
|---|---|---|---|
| **Loss** | 0.0127 | 0.0229 | 0.0127 |
| **Acurácia** | 99.17% | 98.61% | 99.17% |
| **mIoU** | 0.9733 | 0.9571 | 0.9733 |
| **Loss Val.** | 0.0194 | 0.0250 | 0.0243 |
| **Acurácia Val.** | 99.08% | 98.50% | 98.93% |
| **mIoU Val.** | 0.9716 | 0.9552 | 0.9671 |
| **IoU Trilha Val.** | 0.9545 | 0.9289 | 0.9475 |
| **F1 Val.** | 0.9767 | 0.9629 | 0.9730 |

Modelo salvo: época 11, escolhida pelo mIoU de validação (0.9716).

*Treino: média do mIoU de cada batch. Validação: mIoU da matriz de confusão de todo o conjunto, como na avaliação do teste.*
