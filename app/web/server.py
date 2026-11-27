"""Servidor local da interface: API em /api e as páginas em /static. Tudo roda no computador, sem internet."""
import os
import json
import math
import traceback

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.web.erros import configure_logging, describe, logger
from app.web.fila import FilaDeTarefas
from app.web.registro import Registro
from app.web.servicos import ACCEPTED_FORMATS_TEXT, Recusa, Sistema

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')


def clean_numbers(value):
    # NaN e infinito não existem em JSON: viram null (ex.: precisão sem nenhum pixel previsto como trilha)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {key: clean_numbers(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_numbers(item) for item in value]
    return value


class SafeJSONResponse(JSONResponse):
    def render(self, content):
        return json.dumps(clean_numbers(content), ensure_ascii=False).encode('utf-8')


def read_version():
    """Hash curto do commit em que a interface está rodando, para identificar a versão nas capturas e nos testes."""
    import subprocess
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        commit = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=root, capture_output=True, text=True, timeout=5)
        if commit.returncode != 0:
            return {'commit': None, 'alteracoes': False}
        changed = subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', '.'], cwd=root, timeout=5).returncode != 0
        return {'commit': commit.stdout.strip(), 'alteracoes': changed}
    except (OSError, subprocess.SubprocessError):
        return {'commit': None, 'alteracoes': False}


def refusal(error, status=400):
    return SafeJSONResponse({'erro': error.to_dict()}, status_code=status)


def create_app():
    configure_logging()
    registro = Registro()
    fila = FilaDeTarefas()
    sistema = Sistema(registro, fila)

    app = FastAPI(title='Segmentação Off-Road', default_response_class=SafeJSONResponse)
    app.state.sistema = sistema

    @app.exception_handler(Recusa)
    async def handle_refusal(request: Request, error: Recusa):
        return refusal(error, 409 if error.tipo in ('AL', 'RA') else 400)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, error: Exception):
        logger.error("Erro em %s %s:\n%s", request.method, request.url.path, traceback.format_exc())
        description = describe(error)
        return SafeJSONResponse({'erro': {'tipo': 'CE', 'mensagem': f"{description['causa'][0].upper()}{description['causa'][1:]}. "
                                                                    f"{description['sugestao']}", 'campo': None, 'dados': {}}},
                                status_code=500)

    def not_found(message='Não encontrado.'):
        return SafeJSONResponse({'erro': {'tipo': 'CE', 'mensagem': message, 'campo': None, 'dados': {}}}, status_code=404)

    # Estado geral

    version = read_version()

    @app.get('/api/estado')
    def state():
        return {**sistema.overview(), 'versao': version}

    @app.get('/api/formatos')
    def formats():
        return {'texto': ACCEPTED_FORMATS_TEXT, 'extensoes': ['.jpg', '.jpeg', '.png', '.mp4']}

    # Configurações e treino

    @app.get('/api/configuracoes')
    def configurations():
        return sistema.list_configurations()

    @app.get('/api/configuracoes/{configuration_id}')
    def configuration(configuration_id: str):
        found = sistema.get_configuration(configuration_id)
        return found if found else not_found('Configuração não encontrada.')

    @app.get('/api/treino/padroes')
    def training_defaults():
        return sistema.training_defaults()

    @app.get('/api/treino/nome-sugerido')
    def suggested_name(modelo: str, epocas: int = 1):
        return {'nome': sistema.suggest_name(modelo, epocas)}

    @app.post('/api/treino/validar')
    async def validate_training(request: Request):
        sistema.validate_training(await request.json())
        return {'ok': True}

    @app.post('/api/treino')
    async def start_training(request: Request):
        return sistema.start_training(await request.json())

    @app.post('/api/configuracoes/{configuration_id}/avaliar')
    def evaluate_configuration(configuration_id: str):
        return sistema.retry_evaluation(configuration_id)

    @app.post('/api/treino/{configuration_id}/reiniciar')
    async def restart_training(configuration_id: str, request: Request):
        body = await request.json()
        return sistema.restart_training(configuration_id, body.get('batch_size'))

    # Sessões

    @app.post('/api/sessoes')
    def create_session(ciclo: str = Form(''), arquivos: list[UploadFile] = File(default=[])):
        uploads = [(upload.filename, upload.file) for upload in arquivos]
        return sistema.create_session(ciclo, uploads)

    @app.delete('/api/sessoes/{session_id}/rascunho')
    def discard_draft(session_id: str):
        sistema.discard_draft(session_id)
        return {'ok': True}

    @app.get('/api/sessoes/atual')
    def current_session():
        session_id = sistema.current_session_id()
        session = sistema.get_session(session_id) if session_id else None
        return session if session else not_found('Ainda não há sessão de segmentação.')

    @app.get('/api/sessoes/{session_id}')
    def session(session_id: str):
        found = sistema.get_session(session_id)
        return found if found else not_found('Sessão não encontrada.')

    @app.post('/api/sessoes/{session_id}/executar')
    async def execute(session_id: str, request: Request):
        body = await request.json()
        return sistema.execute(session_id, body.get('configuracoes'), body.get('imagens'))

    @app.post('/api/sessoes/{session_id}/falhas')
    async def image_failure(session_id: str, request: Request):
        body = await request.json()
        if body.get('imagem'):
            return sistema.handle_image_failure(session_id, body.get('configuracao'), body['imagem'], body.get('acao'))
        if body.get('video'):
            if body.get('acao') == 'deixar de fora':
                return sistema.leave_video_out(session_id, body['video'])
            return sistema.retry_video(session_id, body['video'])
        return sistema.handle_execution_failure(session_id, body.get('configuracao'), body.get('acao'))

    def send_file(path, media_type=None, download_name=None):
        if not path or not os.path.isfile(path):
            return not_found('Arquivo não encontrado.')
        headers = {'Cache-Control': 'no-cache'}
        return FileResponse(path, media_type=media_type, filename=download_name, headers=headers)

    @app.get('/api/sessoes/{session_id}/imagens/{image}')
    def image_file(session_id: str, image: str):
        return send_file(sistema.session_file(session_id, 'imagem', image))

    @app.get('/api/sessoes/{session_id}/mascaras/{configuration_id}/{image}')
    def mask_file(session_id: str, configuration_id: str, image: str, baixar: bool = False):
        name = sistema.download_name(configuration_id, image, 'mascara') if baixar else None
        return send_file(sistema.session_file(session_id, 'mascara', image, configuration_id), 'image/png', name)

    @app.get('/api/sessoes/{session_id}/sobreposicoes/{configuration_id}/{image}')
    def overlay_file(session_id: str, configuration_id: str, image: str):
        png = sistema.overlay_image(session_id, configuration_id, image)
        if png is None:
            return not_found('Esta imagem não tem máscara desta configuração.')
        name = sistema.download_name(configuration_id, image, 'sobreposicao')
        return Response(png, media_type='image/png',
                        headers={'Content-Disposition': f'attachment; filename="{name}"', 'Cache-Control': 'no-cache'})

    @app.get('/api/sessoes/{session_id}/videos/{configuration_id}/{video}')
    def video_file(session_id: str, configuration_id: str, video: str):
        path = sistema.session_file(session_id, 'video', video, configuration_id)
        return send_file(path, 'video/mp4', os.path.basename(path) if path else None)

    # Ciclos e desempenho

    @app.get('/api/ciclos')
    def cycles():
        return sistema.cycles()

    @app.post('/api/desempenho')
    async def performance(request: Request):
        body = await request.json()
        return sistema.performance(body.get('configuracoes'), body.get('ciclo') or None, bool(body.get('comparar_mesmo_assim')))

    # Datasets

    @app.get('/api/datasets')
    def datasets():
        return sistema.datasets_status()

    @app.post('/api/datasets/{name}/baixar')
    def download(name: str):
        return sistema.download_dataset(name)

    @app.post('/api/datasets/remontar')
    def rebuild():
        return sistema.rebuild_dataset()

    @app.post('/api/datasets/avaliar')
    async def evaluate(request: Request):
        body = await request.json()
        return sistema.evaluate_configurations(body.get('configuracoes') or [])

    # Páginas

    @app.middleware('http')
    async def no_cache_for_pages(request: Request, call_next):
        # Sem cache das páginas e scripts: depois de atualizar o código, o navegador pega a versão nova
        response = await call_next(request)
        if request.url.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-cache'
        return response

    app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')

    @app.get('/')
    def index():
        return FileResponse(os.path.join(STATIC_DIR, 'index.html'), headers={'Cache-Control': 'no-cache'})

    @app.get('/favicon.ico')
    def favicon():
        return Response(status_code=204)

    return app
