# Segmentação-Semantica-Off-Road

## Artigos
[Planilha de artigos do TCC](https://docs.google.com/spreadsheets/d/1R5qA6WePVfGyGWpKvlxbrkAxcpj4FcO8L0CS4ba1-YY/edit?usp=sharing)

## Como rodar
```
python -m app.main
```
A interface abre no navegador em `http://127.0.0.1:8000/` (só na própria máquina, sem internet). Opções: `--porta 8080` e `--sem-navegador`.
O treino e a segmentação rodam enquanto o programa estiver aberto; fechar o terminal encerra o treino em andamento.

Onde a interface guarda os dados:
- `raw/`: datasets brutos (nunca são apagados; "Remontar o dataset" copia daqui para `dataset/`).
- `results/configuracoes/<id>/`: pesos, estatísticas e gráficos de cada configuração treinada pela interface.
- `results/registro.json`: configurações, avaliações das imagens, conclusões e decisões.
- `sessoes/<id>/`: imagens e vídeos enviados, quadros extraídos e máscaras de cada configuração.
- `results/interface.log`: detalhes técnicos de falhas (a interface mostra só a causa em linguagem de usuário).

Os modelos treinados antes da interface (`results/fcn/model.pth` e `results/deeplabv3+/model.pth`) aparecem como configurações disponíveis.
## Como Instalar as dependencias
```
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu118
```

## Controlar o CARLA

- **Se for a primeira vez**
```
sudo docker build -t seg-carla-client -f docker/Dockerfile docker
```

- **Terminal 1**  
(Espere cerca de 30 segundos e deixe a janela aberta. O CARLA precisa estar pronto antes do próximo passo)
```
cd ~/Downloads/CARLA_0.9.6-dirty && sh CarlaUE4.sh -opengl -windowed -ResX=640 -ResY=480
```
- **Terminal 2**
```
.venv/bin/python -m modules.driving.server --mode mask --weather ClearNoon --min-speed 4 --max-speed 8 --video-speed 3
```
- **Terminal 3**
```
sudo docker run --rm --net host -v "$PWD:/app:ro" -v "$HOME/Downloads/CARLA_0.9.6-dirty/PythonAPI/carla/dist:/carla/dist:ro" seg-carla-client
```