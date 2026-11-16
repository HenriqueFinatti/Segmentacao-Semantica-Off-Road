### Segmentação de Dataset de Teste - DEEPLABV3+

**Data:** 2026-11-14 17:24:23

#### Métricas

| Métrica | Valor |
|---------|-------|
| Imagens Processadas | 1669 |
| Tempo Total | 47.79s |
| Tempo Médio de Inferência/Frame | 13.59 ms |
| FPS de Inferência | 73.6 |
| Dispositivo | NVIDIA GeForce RTX 3080 |
| Resolução de Entrada | 512x512 |
| Batch | 1 |
| Passadas de Aquecimento | 5 |
| Status | concluído |

#### Tempo de Inferência por Frame

Tempo apenas do modelo (forward + argmax), medido com batch 1 e sincronizado com a GPU.

| Métrica | Tempo de Inferência | Tempo Total por Frame |
|---------|---------------------|-----------------------|
| Média | 13.59 ms | 28.64 ms |
| Mediana | 13.58 ms | 26.10 ms |
| Desvio Padrão | 0.03 ms | 9.97 ms |
| Mínimo | 13.56 ms | 19.31 ms |
| Máximo | 14.31 ms | 69.81 ms |
| P95 | 13.62 ms | 66.21 ms |
| FPS (1000 / média) | 73.6 | 34.9 |

*Tempo Total por Frame inclui carregar e pré-processar a imagem, a inferência e salvar a máscara.*

Tempos por frame: `results/deeplabv3+/statistics/tempos_inferencia_teste.csv`