### Segmentação de Vídeo - FCN

**Data:** 2026-11-14 14:55:16

#### Métricas

| Métrica | Valor |
|---------|-------|
| Imagens Processadas | 7449 |
| Tempo Total | 242.56s |
| Tempo Médio de Inferência/Frame | 11.47 ms |
| FPS de Inferência | 87.2 |
| Dispositivo | NVIDIA GeForce RTX 3080 |
| Resolução de Entrada | 512x512 |
| Batch | 1 |
| Passadas de Aquecimento | 5 |
| Status | concluído |

#### Tempo de Inferência por Frame

Tempo apenas do modelo (forward + argmax), medido com batch 1 e sincronizado com a GPU.

| Métrica | Tempo de Inferência | Tempo Total por Frame |
|---------|---------------------|-----------------------|
| Média | 11.47 ms | 32.56 ms |
| Mediana | 11.28 ms | 32.48 ms |
| Desvio Padrão | 0.56 ms | 1.92 ms |
| Mínimo | 10.54 ms | 28.44 ms |
| Máximo | 22.97 ms | 96.16 ms |
| P95 | 12.26 ms | 34.89 ms |
| FPS (1000 / média) | 87.2 | 30.7 |

*Tempo Total por Frame inclui carregar e pré-processar a imagem, a inferência e salvar a máscara.*

Tempos por frame: `results/fcn/statistics/tempos_inferencia_video.csv`