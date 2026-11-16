### Configuração do Treinamento

| Parâmetro | Valor |
|-----------|-------|
| Modelo | FCN |
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
FCN: Época 1
Treino    | Loss: 0.0655 | Acurácia: 96.08% | mIoU: 0.8892 | Tempo da Época: 2m 56.39s
Validação | Loss: 0.0590 | Acurácia: 95.77% | mIoU: 0.8838 | IoU Trilha: 0.8201 | F1: 0.9012


FCN: Época 2
Treino    | Loss: 0.0466 | Acurácia: 97.06% | mIoU: 0.9132 | Tempo da Época: 2m 56.08s
Validação | Loss: 0.0511 | Acurácia: 96.20% | mIoU: 0.8941 | IoU Trilha: 0.8353 | F1: 0.9102


FCN: Época 3
Treino    | Loss: 0.0415 | Acurácia: 97.35% | mIoU: 0.9201 | Tempo da Época: 2m 56.09s
Validação | Loss: 0.0379 | Acurácia: 97.74% | mIoU: 0.9334 | IoU Trilha: 0.8949 | F1: 0.9445


FCN: Época 4
Treino    | Loss: 0.0329 | Acurácia: 97.82% | mIoU: 0.9329 | Tempo da Época: 2m 56.10s
Validação | Loss: 0.0345 | Acurácia: 97.71% | mIoU: 0.9327 | IoU Trilha: 0.8938 | F1: 0.9439


FCN: Época 5
Treino    | Loss: 0.0415 | Acurácia: 97.37% | mIoU: 0.9219 | Tempo da Época: 2m 56.09s
Validação | Loss: 0.0350 | Acurácia: 98.02% | mIoU: 0.9412 | IoU Trilha: 0.9069 | F1: 0.9512


FCN: Época 6
Treino    | Loss: 0.0340 | Acurácia: 97.79% | mIoU: 0.9320 | Tempo da Época: 2m 56.06s
Validação | Loss: 0.0328 | Acurácia: 97.90% | mIoU: 0.9378 | IoU Trilha: 0.9017 | F1: 0.9483


FCN: Época 7
Treino    | Loss: 0.0326 | Acurácia: 97.90% | mIoU: 0.9349 | Tempo da Época: 2m 56.08s
Validação | Loss: 0.0392 | Acurácia: 97.52% | mIoU: 0.9276 | IoU Trilha: 0.8859 | F1: 0.9395


FCN: Época 8
Treino    | Loss: 0.0314 | Acurácia: 97.94% | mIoU: 0.9360 | Tempo da Época: 2m 56.09s
Validação | Loss: 0.0328 | Acurácia: 97.96% | mIoU: 0.9396 | IoU Trilha: 0.9044 | F1: 0.9498


FCN: Época 9
Treino    | Loss: 0.0278 | Acurácia: 98.15% | mIoU: 0.9421 | Tempo da Época: 2m 56.10s
Validação | Loss: 0.0310 | Acurácia: 98.11% | mIoU: 0.9436 | IoU Trilha: 0.9107 | F1: 0.9532


FCN: Época 10
Treino    | Loss: 0.0287 | Acurácia: 98.12% | mIoU: 0.9409 | Tempo da Época: 2m 56.06s
Validação | Loss: 0.0351 | Acurácia: 98.07% | mIoU: 0.9426 | IoU Trilha: 0.9090 | F1: 0.9523


FCN: Época 11
Treino    | Loss: 0.0299 | Acurácia: 98.05% | mIoU: 0.9395 | Tempo da Época: 2m 56.13s
Validação | Loss: 0.0316 | Acurácia: 98.09% | mIoU: 0.9432 | IoU Trilha: 0.9101 | F1: 0.9529


FCN: Época 12
Treino    | Loss: 0.0309 | Acurácia: 98.05% | mIoU: 0.9393 | Tempo da Época: 2m 56.04s
Validação | Loss: 0.0342 | Acurácia: 98.15% | mIoU: 0.9446 | IoU Trilha: 0.9122 | F1: 0.9541


FCN: Época 13
Treino    | Loss: 0.0262 | Acurácia: 98.28% | mIoU: 0.9452 | Tempo da Época: 2m 56.08s
Validação | Loss: 0.0288 | Acurácia: 98.27% | mIoU: 0.9480 | IoU Trilha: 0.9176 | F1: 0.9570


FCN: Época 14
Treino    | Loss: 0.0237 | Acurácia: 98.42% | mIoU: 0.9497 | Tempo da Época: 2m 56.09s
Validação | Loss: 0.0296 | Acurácia: 98.20% | mIoU: 0.9461 | IoU Trilha: 0.9146 | F1: 0.9554


FCN: Época 15
Treino    | Loss: 0.0229 | Acurácia: 98.48% | mIoU: 0.9511 | Tempo da Época: 2m 56.06s
Validação | Loss: 0.0362 | Acurácia: 98.22% | mIoU: 0.9467 | IoU Trilha: 0.9154 | F1: 0.9558


FCN: Época 16
Treino    | Loss: 0.0269 | Acurácia: 98.26% | mIoU: 0.9448 | Tempo da Época: 2m 56.06s
Validação | Loss: 0.0445 | Acurácia: 97.05% | mIoU: 0.9153 | IoU Trilha: 0.8672 | F1: 0.9289


FCN: Época 17
Treino    | Loss: 0.0262 | Acurácia: 98.30% | mIoU: 0.9460 | Tempo da Época: 2m 56.04s
Validação | Loss: 0.0308 | Acurácia: 98.13% | mIoU: 0.9442 | IoU Trilha: 0.9116 | F1: 0.9538


FCN: Época 18
Treino    | Loss: 0.0221 | Acurácia: 98.52% | mIoU: 0.9525 | Tempo da Época: 2m 56.00s
Validação | Loss: 0.0296 | Acurácia: 98.42% | mIoU: 0.9524 | IoU Trilha: 0.9243 | F1: 0.9607


FCN: Época 19
Treino    | Loss: 0.0209 | Acurácia: 98.60% | mIoU: 0.9550 | Tempo da Época: 2m 56.08s
Validação | Loss: 0.0309 | Acurácia: 98.51% | mIoU: 0.9548 | IoU Trilha: 0.9281 | F1: 0.9627


FCN: Época 20
Treino    | Loss: 0.0233 | Acurácia: 98.48% | mIoU: 0.9514 | Tempo da Época: 2m 56.03s
Validação | Loss: 0.0346 | Acurácia: 98.04% | mIoU: 0.9417 | IoU Trilha: 0.9077 | F1: 0.9516


FCN: Época 21
Treino    | Loss: 0.0230 | Acurácia: 98.48% | mIoU: 0.9514 | Tempo da Época: 2m 56.07s
Validação | Loss: 0.0301 | Acurácia: 98.31% | mIoU: 0.9494 | IoU Trilha: 0.9196 | F1: 0.9581


FCN: Época 22
Treino    | Loss: 0.0205 | Acurácia: 98.63% | mIoU: 0.9555 | Tempo da Época: 2m 56.08s
Validação | Loss: 0.0415 | Acurácia: 97.63% | mIoU: 0.9305 | IoU Trilha: 0.8903 | F1: 0.9420


FCN: Época 23
Treino    | Loss: 0.0243 | Acurácia: 98.43% | mIoU: 0.9502 | Tempo da Época: 2m 56.07s
Validação | Loss: 0.0324 | Acurácia: 98.13% | mIoU: 0.9442 | IoU Trilha: 0.9116 | F1: 0.9537


FCN: Época 24
Treino    | Loss: 0.0211 | Acurácia: 98.58% | mIoU: 0.9543 | Tempo da Época: 2m 56.04s
Validação | Loss: 0.0300 | Acurácia: 98.30% | mIoU: 0.9489 | IoU Trilha: 0.9188 | F1: 0.9577


### Resultados Finais FCN
---

#### Resumo de Tempo e Épocas
- **Total de Épocas:** 24
- **Tempo Total:** 70m 29s
- **Tempo Médio por Época:** 2m 56s

#### Tabela de Métricas
| Métrica | Melhor | Média | Final (Última) |
|---|---|---|---|
| **Loss** | 0.0205 | 0.0302 | 0.0211 |
| **Acurácia** | 98.63% | 98.05% | 98.58% |
| **mIoU** | 0.9555 | 0.9395 | 0.9543 |
| **Loss Val.** | 0.0288 | 0.0355 | 0.0300 |
| **Acurácia Val.** | 98.51% | 97.85% | 98.30% |
| **mIoU Val.** | 0.9548 | 0.9369 | 0.9489 |
| **IoU Trilha Val.** | 0.9281 | 0.9005 | 0.9188 |
| **F1 Val.** | 0.9627 | 0.9474 | 0.9577 |

Modelo salvo: época 19, escolhida pelo mIoU de validação (0.9548).

*Treino: média do mIoU de cada batch. Validação: mIoU da matriz de confusão de todo o conjunto, como na avaliação do teste.*
