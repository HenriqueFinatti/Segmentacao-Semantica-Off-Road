### Segmentação de Dataset de Teste - FCN

**Data:** 2026-11-14 17:23:34

#### Métricas

| Métrica | Valor |
|---------|-------|
| Imagens Processadas | 1669 |
| Tempo Total | 44.45s |
| Tempo Médio de Inferência/Frame | 11.25 ms |
| FPS de Inferência | 88.9 |
| Dispositivo | NVIDIA GeForce RTX 3080 |
| Resolução de Entrada | 512x512 |
| Batch | 1 |
| Passadas de Aquecimento | 5 |
| Status | concluído |

#### Tempo de Inferência por Frame

Tempo apenas do modelo (forward + argmax), medido com batch 1 e sincronizado com a GPU.

| Métrica | Tempo de Inferência | Tempo Total por Frame |
|---------|---------------------|-----------------------|
| Média | 11.25 ms | 26.63 ms |
| Mediana | 11.24 ms | 24.24 ms |
| Desvio Padrão | 0.02 ms | 9.98 ms |
| Mínimo | 11.19 ms | 17.27 ms |
| Máximo | 11.66 ms | 108.02 ms |
| P95 | 11.28 ms | 63.50 ms |
| FPS (1000 / média) | 88.9 | 37.6 |

*Tempo Total por Frame inclui carregar e pré-processar a imagem, a inferência e salvar a máscara.*

Tempos por frame: `results/fcn/statistics/tempos_inferencia_teste.csv`