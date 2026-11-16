### Segmentação de Vídeo - DEEPLABV3+

**Data:** 2026-11-14 14:59:30

#### Métricas

| Métrica | Valor |
|---------|-------|
| Imagens Processadas | 7449 |
| Tempo Total | 253.41s |
| Tempo Médio de Inferência/Frame | 12.78 ms |
| FPS de Inferência | 78.3 |
| Dispositivo | NVIDIA GeForce RTX 3080 |
| Resolução de Entrada | 512x512 |
| Batch | 1 |
| Passadas de Aquecimento | 5 |
| Status | concluído |

#### Tempo de Inferência por Frame

Tempo apenas do modelo (forward + argmax), medido com batch 1 e sincronizado com a GPU.

| Métrica | Tempo de Inferência | Tempo Total por Frame |
|---------|---------------------|-----------------------|
| Média | 12.78 ms | 34.02 ms |
| Mediana | 12.71 ms | 33.77 ms |
| Desvio Padrão | 0.58 ms | 2.12 ms |
| Mínimo | 12.43 ms | 30.13 ms |
| Máximo | 47.38 ms | 79.48 ms |
| P95 | 13.43 ms | 37.11 ms |
| FPS (1000 / média) | 78.3 | 29.4 |

*Tempo Total por Frame inclui carregar e pré-processar a imagem, a inferência e salvar a máscara.*

Tempos por frame: `results/deeplabv3+/statistics/tempos_inferencia_video.csv`