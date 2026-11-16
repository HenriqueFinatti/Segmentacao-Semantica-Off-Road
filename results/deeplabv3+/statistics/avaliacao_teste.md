### Avaliação no Dataset de Teste - DEEPLABV3+

**Data:** 2026-11-14 17:24:30

Predições comparadas pixel a pixel com as máscaras reais, no tamanho original das imagens. A matriz de confusão é somada em todo o conjunto e as métricas são calculadas a partir dela. A classe positiva é a trilha.

#### Métricas

| Dataset | Imagens | Acurácia | mIoU | IoU Trilha | IoU Fundo | Precisão | Recall | F1 |
|---------|---------|----------|------|------------|-----------|----------|--------|----|
| Freiburg_Forest | 136 | 97.76% | 88.22% | 78.89% | 97.56% | 80.13% | 98.07% | 88.20% |
| Synthetic_Offroad | 1234 | 99.43% | 98.07% | 96.83% | 99.32% | 97.16% | 99.65% | 98.39% |
| CaSSeD | 299 | 96.93% | 86.70% | 76.82% | 96.58% | 92.57% | 81.87% | 86.89% |
| Todos | 1669 | 98.25% | 93.30% | 88.63% | 97.98% | 94.80% | 93.15% | 93.97% |

#### Matriz de Confusão (todos os datasets)

Linhas: classe real. Colunas: classe prevista. Entre parênteses, a fração da linha.

| Real \ Previsto | Trilha | Fundo |
|-----------------|--------|-------|
| Trilha | 110,766,627 (93.15%) | 8,139,602 (6.85%) |
| Fundo | 6,070,307 (0.87%) | 688,057,226 (99.13%) |

#### 5 Piores Imagens (IoU da Trilha)

| Imagem | Dataset | IoU Trilha | Precisão | Recall |
|--------|---------|------------|----------|--------|
| Freiburg_Forest_0.png | Freiburg_Forest | - | - | - |
| Freiburg_Forest_125.png | Freiburg_Forest | - | - | - |
| CaSSeD_170.png | CaSSeD | 0.00% | 0.00% | - |
| CaSSeD_171.png | CaSSeD | 0.00% | 0.00% | - |
| Freiburg_Forest_110.png | Freiburg_Forest | 0.00% | 0.00% | - |

*O mIoU do treino (stats.md) é a média do mIoU de cada batch; aqui ele vem da matriz de confusão de todo o conjunto, que é a forma padrão. Os dois não são diretamente comparáveis.*

Métricas por imagem: `results/deeplabv3+/statistics/avaliacao_teste_por_imagem.csv`
