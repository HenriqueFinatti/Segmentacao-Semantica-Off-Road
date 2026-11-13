# Segmentação-Semantica-Off-Road

## Artigos
[Planilha de artigos do TCC](https://docs.google.com/spreadsheets/d/1R5qA6WePVfGyGWpKvlxbrkAxcpj4FcO8L0CS4ba1-YY/edit?usp=sharing)

## Como rodar
```
python -m app.main
```
## Como Instalar as dependencias
```
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu118
```

## Controlar o CARLA

- **Se for a primeira vez**
```
sudo docker build -t seg-carla-client -f docker/Dockerfile docker
```

- **Terminal 1 (Espere cerca de 30 segundos e deixe a janela aberta. O CARLA precisa estar
pronto antes do próximo passo)**
```
cd ~/Downloads/CARLA_0.9.6-dirty && sh CarlaUE4.sh -opengl -windowed -ResX=640 -ResY=480
```
- **Terminal 2**
```
.venv/bin/python -m modules.driving.server --mode mask --weather ClearNoon --min-speed 2 --m1ax-speed 4 --video-speed 3
```
- **Terminal 3**
```
sudo docker run --rm --net host -v "$PWD:/app:ro" -v "$HOME/Downloads/CARLA_0.9.6-dirty/PythonAPI/carla/dist:/carla/dist:ro" seg-carla-client
```
## To-do
### Artigo
- [ ] **Resultados reportados são de treino.** A acurácia (98,57%) e o mIoU (92,58%) em "Resultados Parciais" são médias sobre o dataset de treino. Refazer com métricas no dataset de teste depois que a avaliação existir no código (ver seção Código).
- [ ] **Remover as menções ao dataset YAMAHA (YCOR)**, que não será mais usado: Introdução (objetivo de validação), Metodologia (parágrafos de *Transfer Learning* e do YCOR) e conclusão de "Resultados Parciais".
- [ ] **Recall, F1-score e matrizes de confusão** são prometidos na Metodologia, mas ainda não são calculados. Implementar no código ou retirar do texto.
- [ ] **Validação no CARLA** é prometida na Introdução, Metodologia e Resultados Parciais, mas não existe no código. Implementar ou rebaixar para trabalho futuro.
- [ ] **Segmentação de vídeo com consistência temporal**: o texto descreve exploração de correlação entre frames, mas o código segmenta cada frame isoladamente. Ajustar o texto ou o código.
- [ ] **Caminhos das figuras**: `../metrics/training_metrics.png` e `../metrics/performance_summary.png` não existem; o código salva os gráficos em `results/{fcn,deeplabv3+}/images/`.
- [ ] **Inconsistência no tamanho do Freiburg Forest**: a Metodologia diz "aproximadamente 200 imagens" e, mais adiante, "milhares de imagens multiespectrais".
- [ ] Referência "imagem 7" para o fluxograma da metodologia: usar `\ref{}` em vez de número fixo.
- [ ] Erro de digitação na legenda: "Permformance do modelo DeepLab".
- [ ] **Tempo de inferência (12,85 ms)** em "Resultados Parciais": medir de novo com a nova métrica (batch 1, com aquecimento, sincronizado com a GPU) e usar os relatórios `results/<modelo>/statistics/segmentation_<contexto>.md` e os gráficos `results/comparacao/tempo_inferencia_<contexto>.png`.

### Código
#### Avaliação
- [ ] **Não há avaliação no teste.** `segment_test_dataset` gera as predições em `dataset/test/new_segmentation/`, mas nunca as compara com `dataset/test/mask`. Calcular acurácia, mIoU (e Recall/F1/matriz de confusão) no teste.
- [ ] **Sem split de validação.** O melhor modelo (`save_best_model`) e o early stopping usam o mIoU de treino. Separar validação e usar o mIoU dela.
#### Bugs
- [x] **Caminhos estilo Windows** em `app/main.py:10` (`r"video\video.mp4"`, `"video\\output\\"`): no Linux criam a pasta literal `video\output\` na raiz e o vídeo não é encontrado. Usar `os.path.join`. Apagar a pasta `video\output\` criada por engano.
- [x] `Video(...)` é instanciado no import de `app/main.py`, criando pastas em toda execução, qualquer que seja a opção escolhida.
- [x] **Opção 6 retreina os dois modelos** antes de segmentar o vídeo; deveria usar os `model.pth` já treinados.
- [ ] **Predições ficam em 512×512**: não voltam ao tamanho original da imagem, então o vídeo gerado sai em 512×512 e só com a máscara preto/branco. Redimensionar e, idealmente, sobrepor a máscara no frame original.
- [x] `SegmentationService.load_model` retorna `None` se o `.pth` não existe, e `run_inference` quebra com um erro confuso. Lançar `FileNotFoundError` claro.
- [ ] `modules/metrics/metrics_tracker.py:177`: "Tempo Médio por Época" usa `total_secs` em vez de `avg_secs`.
- [x] `schemas/settings_config.py` não bate com `settings.json`: `Dataset_Labels` vs `Datasets_Labels`, e faltam `Test_Execution` e `BATCH_SIZE`.
- [ ] `OffRoadDataset.get_images` retorna `None` quando os dois datasets estão desligados.
- [ ] `MaskGenerator.generate_masks` calcula `total_generated`/`total_skipped` e os percentuais, mas nunca imprime nada.
- [ ] Gráfico de IoU (`chart.py`) tem rótulo "mIoU (%)", mas os valores estão em 0–1.

### Estrutura
#### Prioridade (fazer junto com os bugs)
- [x] **Registro único de modelos.** A escolha `if model == 'FCN' ... 'DEEPLABV3+'` está repetida em `Trainer`, `MetricsTracker.get_result_path`, `Charts.get_result_path` e `SegmentationService`. Trocar por um dicionário `MODELS = {"fcn": FCN, "deeplabv3+": DeepLabV3Plus}` e derivar os caminhos de `results/<nome>/` a partir do nome.
- [x] **Caminhos e hiperparâmetros centralizados.** `'dataset/train'`, `'./raw'`, `results/...` e `images/...` estão fixos em ~10 arquivos; tamanho 512, normalização ImageNet, lr `1e-4`, pesos de classe `[1, 9]` e `num_workers` também. Criar `configs/paths.py` e mover os hiperparâmetros para `settings.json`.
- [x] **Transform duplicado** em `trainer.py` e `segmentation_service.py`: definir uma vez e reutilizar.
- [x] **Remover efeitos colaterais no import.** `dataset_service.py`, `chart.py`, `training_service.py` e `app/main.py` criam objetos globais (e pastas) ao serem importados; `Settings()` é criado e relido do disco em ~6 lugares. Criar `Settings` uma vez no `main` e passar como parâmetro.

#### Depois, se sobrar tempo
- [ ] **Reorganizar pastas:**
  ```
  modules/
    data/        # downloaders, cleaners, converters, mask_generator, os dois Dataset
    models/      # fcn.py, deeplabv3.py (hoje em training/trainer/model/, mas a segmentação também usa)
    training/    # trainer.py, early_stopping.py
    inference/   # segmentation_service.py, video.py (hoje processing/ fica fora de modules/)
    metrics/
  ```
- [ ] Renomear `earlyStopping/` para `early_stopping/` e adicionar `__init__.py` nos pacotes.
- [ ] **CLI com `argparse`** no lugar do menu com `input()` (ex.: `python -m app.main train --model deeplabv3+`), para poder rodar experimentos por script.
- [ ] Cleaners/converters/downloaders são classes sem estado com `__init__` vazio: podem virar funções.
- [ ] `Settings` como dataclass com validação, para pegar divergências como a de `Dataset_Labels`.
- [ ] Testes simples para geração de máscara e cálculo de mIoU (os números que vão para o artigo).