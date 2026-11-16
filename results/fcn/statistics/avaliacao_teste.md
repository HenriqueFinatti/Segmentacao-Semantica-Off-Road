### Avaliação no Dataset de Teste - FCN

**Data:** 2026-11-14 17:24:26

Predições comparadas pixel a pixel com as máscaras reais, no tamanho original das imagens. A matriz de confusão é somada em todo o conjunto e as métricas são calculadas a partir dela. A classe positiva é a trilha.

#### Métricas

| Dataset | Imagens | Acurácia | mIoU | IoU Trilha | IoU Fundo | Precisão | Recall | F1 |
|---------|---------|----------|------|------------|-----------|----------|--------|----|
| Freiburg_Forest | 136 | 97.64% | 87.72% | 78.02% | 97.42% | 79.13% | 98.24% | 87.65% |
| Synthetic_Offroad | 1234 | 98.71% | 95.72% | 93.01% | 98.44% | 93.45% | 99.50% | 96.38% |
| CaSSeD | 299 | 95.78% | 81.70% | 68.03% | 95.36% | 92.19% | 72.19% | 80.97% |
| Todos | 1669 | 97.39% | 90.19% | 83.38% | 96.99% | 92.34% | 89.58% | 90.94% |

#### Matriz de Confusão (todos os datasets)

Linhas: classe real. Colunas: classe prevista. Entre parênteses, a fração da linha.

| Real \ Previsto | Trilha | Fundo |
|-----------------|--------|-------|
| Trilha | 106,511,470 (89.58%) | 12,394,759 (10.42%) |
| Fundo | 8,840,052 (1.27%) | 685,287,481 (98.73%) |

#### 5 Piores Imagens (IoU da Trilha)

| Imagem | Dataset | IoU Trilha | Precisão | Recall |
|--------|---------|------------|----------|--------|
| CaSSeD_170.png | CaSSeD | - | - | - |
| CaSSeD_171.png | CaSSeD | - | - | - |
| Freiburg_Forest_0.png | Freiburg_Forest | - | - | - |
| Freiburg_Forest_110.png | Freiburg_Forest | - | - | - |
| Freiburg_Forest_125.png | Freiburg_Forest | - | - | - |

*O mIoU do treino (stats.md) é a média do mIoU de cada batch; aqui ele vem da matriz de confusão de todo o conjunto, que é a forma padrão. Os dois não são diretamente comparáveis.*

Métricas por imagem: `results/fcn/statistics/avaliacao_teste_por_imagem.csv`
