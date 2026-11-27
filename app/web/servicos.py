"""Regras da interface sobre o código do TCC: configurações, treino, sessões de segmentação,
e desempenho no conjunto de teste.

Os nomes das falas e dos campos seguem o esquema de signos da Entrega 9 (seção 4) do projeto de IHC."""
import os
import re
import json
import csv
import shutil
import unicodedata
from datetime import datetime

from configs import paths
from configs.settings import Settings
from modules.models.registry import MODELS
from modules.dataset.dataset_service import DATASET_NAMES, DatasetService, test_set_fingerprint
from modules.metrics.segmentation_metrics import compute_metrics

from app.web.erros import ErroDeUsuario, logger
from app.web.registro import new_id, now

MODEL_NAMES = {'fcn': 'FCN', 'deeplabv3+': 'DeepLabV3+'}

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
VIDEO_EXTENSIONS = {'.mp4'}
ACCEPTED_FORMATS_TEXT = 'imagens em JPG ou PNG e vídeos em MP4'

METRICS = ['miou', 'iou_trilha', 'iou_fundo', 'acuracia', 'tempo_inferencia_ms']
# Métricas em que o maior valor é destacado; o tempo depende do computador e não entra no destaque
HIGHLIGHTED_METRICS = ['miou', 'iou_trilha', 'iou_fundo', 'acuracia']


class Recusa(Exception):
    """A fala do usuário não pode seguir como está. tipo: PA (prevenção ativa), AL (alerta), RA ou CE."""

    def __init__(self, tipo, mensagem, campo=None, dados=None):
        super().__init__(mensagem)
        self.tipo = tipo
        self.mensagem = mensagem
        self.campo = campo
        self.dados = dados or {}


    def to_dict(self):
        return {'tipo': self.tipo, 'mensagem': self.mensagem, 'campo': self.campo, 'dados': self.dados}


def safe_filename(name):
    name = os.path.basename(name or '').strip()
    stem, extension = os.path.splitext(name)
    stem = unicodedata.normalize('NFKD', stem).encode('ascii', 'ignore').decode('ascii')
    stem = re.sub(r'[^A-Za-z0-9_-]+', '_', stem).strip('_') or 'arquivo'
    return stem[:80], extension.lower()


def ascii_text(text):
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')


def format_epochs(epochs):
    if epochs is None:
        return 'sem limite de épocas'
    return f"{epochs} época" if epochs == 1 else f"{epochs} épocas"


def mask_name(image_name):
    return os.path.splitext(image_name)[0] + '.png'


class Sistema:

    def __init__(self, registro, fila):
        self.registro = registro
        self.fila = fila
        self.settings = Settings()
        self.dataset_service = DatasetService(self.settings)

        self.clean_drafts()
        self.recover_interrupted()
        self.register_existing_models()


    # ------------------------------------------------------------------ inicialização

    def clean_drafts(self):
        # Rascunhos são envios que nunca chegaram a ser executados (ex.: a pessoa trocou os arquivos)
        with self.registro.transaction() as data:
            for session_id in [sid for sid, s in data['sessoes'].items() if s.get('rascunho')]:
                folder = paths.session_dir(session_id)
                if os.path.isdir(folder):
                    paths.safe_rmtree(folder)
                del data['sessoes'][session_id]


    def recover_interrupted(self):
        # A fila não sobrevive ao fechamento da interface; o que estava em andamento é marcado como interrompido
        with self.registro.transaction() as data:
            for configuration in data['configuracoes'].values():
                training = configuration.get('treino') or {}
                if training.get('estado') in ('na fila', 'treinando'):
                    training.update({
                        'estado': 'falhou',
                        'causa': 'o programa foi fechado antes de o treino terminar',
                        'sugestao': 'Reinicie o treino; os parâmetros da configuração foram mantidos.',
                        'tipo_falha': 'RA',
                        'etapa_falha': 'treino',
                    })
                evaluation = configuration.get('avaliacao') or {}
                if evaluation.get('estado') in ('na fila', 'processando'):
                    evaluation.update({
                        'estado': 'falhou',
                        'causa': 'o programa foi fechado antes de a avaliação terminar',
                        'sugestao': 'Tente a avaliação de novo.',
                        'tipo_falha': 'RA',
                    })

            for session in data['sessoes'].values():
                for execution in session.get('execucoes', {}).values():
                    if execution.get('estado') in ('na fila', 'processando'):
                        execution.update({
                            'estado': 'falhou',
                            'causa': 'a interface foi fechada antes de a execução terminar',
                            'sugestao': 'Tente de novo.',
                        })
                for video in session.get('videos', []):
                    if video.get('estado') in ('na fila', 'processando'):
                        video['estado'] = 'falhou'


    def register_existing_models(self):
        """Os modelos treinados antes da interface (results/<modelo>/model.pth) viram configurações disponíveis."""
        with self.registro.transaction() as data:
            known = {c.get('pasta') for c in data['configuracoes'].values()}

            for model in MODELS:
                folder = paths.relative(os.path.join(paths.RESULTS_DIR, model))
                if folder in known or not os.path.isfile(paths.model_path(model)):
                    continue

                parameters = self.read_legacy_parameters(model)
                name = self.unique_name(f"{MODEL_NAMES[model]} – {format_epochs(parameters['epocas'])}", data)
                configuration_id = new_id('c-')
                data['configuracoes'][configuration_id] = {
                    'id': configuration_id,
                    'nome': name,
                    'modelo': model,
                    'parametros': parameters,
                    'tamanho_imagem': self.settings.get_image_size(),
                    'pasta': folder,
                    'origem': 'existente',
                    'criada_em': datetime.fromtimestamp(os.path.getmtime(paths.model_path(model))).isoformat(timespec='seconds'),
                    'treino': {'estado': 'concluído', 'historico': [], 'motivo_termino': None,
                               'epoca_final': None, 'melhor_epoca': None, 'antes_da_interface': True},
                    'teste': self.read_legacy_test(model),
                }
                logger.info("Modelo existente registrado como configuração: %s", name)


    def read_legacy_parameters(self, model):
        defaults = {**self.default_parameters(), 'execucao_teste': False}
        stats = os.path.join(paths.statistics_dir(model), 'stats.md')
        if not os.path.isfile(stats):
            return defaults

        table = {}
        with open(stats, encoding='utf-8') as f:
            for line in f:
                match = re.match(r'\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', line)
                if match:
                    table[match.group(1)] = match.group(2)

        parameters = dict(defaults)
        epochs = str(table.get('Épocas (máximo)', defaults['epocas']))
        try:
            parameters['epocas'] = None if epochs.startswith('Sem limite') else int(epochs)
            parameters['batch_size'] = int(table.get('Batch Size', defaults['batch_size']))
        except ValueError:
            pass

        early = table.get('Early Stopping', '')
        parameters['early_stopping'] = early.startswith('Sim')
        patience = re.search(r'paciência (\d+)', early)
        if patience:
            parameters['paciencia'] = int(patience.group(1))

        test_execution = re.match(r'Sim \((\d+) imagens, (\d+) épocas\)', table.get('Execução de Teste', ''))
        if test_execution:
            parameters['execucao_teste'] = True
            parameters['execucao_teste_imagens'] = int(test_execution.group(1))
            parameters['execucao_teste_epocas'] = int(test_execution.group(2))

        if 'Datasets' in table:
            labels = [label.strip() for label in table['Datasets'].split(',')]
            ids = [key for key, label in DATASET_NAMES.items() if label in labels or key in labels]
            parameters['datasets'] = ids or defaults['datasets']

        return parameters


    def read_legacy_test(self, model):
        per_image = os.path.join(paths.statistics_dir(model), 'avaliacao_teste_por_imagem.csv')
        if not os.path.isfile(per_image):
            return None

        counts = {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 0}
        names = []
        with open(per_image, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                names.append(row['imagem'])
                for key in counts:
                    counts[key] += int(row[key])

        if not names:
            return None

        times_file = os.path.join(paths.statistics_dir(model), 'tempos_inferencia_teste.csv')
        inference = None
        if os.path.isfile(times_file):
            with open(times_file, encoding='utf-8') as f:
                values = [float(row['tempo_inferencia_ms']) for row in csv.DictReader(f)]
            inference = sum(values) / len(values) if values else None

        return self.build_test_result(counts, names, inference, os.path.getmtime(per_image))


    def build_test_result(self, counts, mask_names, inference_ms, timestamp=None):
        per_dataset = {}
        for name in mask_names:
            prefix = next((p for p in DATASET_NAMES if name.startswith(f"{p}_")), None)
            label = DATASET_NAMES.get(prefix, 'Outro')
            per_dataset[label] = per_dataset.get(label, 0) + 1

        metrics = compute_metrics(counts)
        return {
            'conjunto': {
                'id': test_set_fingerprint(mask_names),
                'imagens': len(mask_names),
                'por_dataset': per_dataset,
            },
            'metricas': {
                'miou': metrics['miou'],
                'iou_trilha': metrics['iou_trilha'],
                'iou_fundo': metrics['iou_fundo'],
                'acuracia': metrics['acuracia'],
                'tempo_inferencia_ms': inference_ms,
            },
            'matriz': counts,
            'avaliado_em': (datetime.fromtimestamp(timestamp) if timestamp else datetime.now()).isoformat(timespec='seconds'),
        }


    # ------------------------------------------------------------------ configurações

    def default_parameters(self):
        settings = self.settings
        datasets = [name for name in DATASET_NAMES if settings.settings.get(name, False)]
        return {
            'epocas': settings.get_epochs(),
            'early_stopping': settings.is_early_stopping_on(),
            'paciencia': settings.get_patience(),
            'datasets': datasets,
            'batch_size': settings.get_batch_size(),
            'graficos': True,
            'execucao_teste': settings.is_test_execution_on(),
            'execucao_teste_imagens': settings.get_test_execution_images(),
            'execucao_teste_epocas': settings.get_test_execution_epochs(),
        }


    def configuration_folder(self, configuration):
        return os.path.join(paths.ROOT, configuration['pasta'])


    def weights_path(self, configuration):
        return os.path.join(self.configuration_folder(configuration), 'model.pth')


    def is_available(self, configuration):
        return (configuration.get('treino') or {}).get('estado') == 'concluído'


    def description(self, configuration):
        p = configuration['parametros']
        early = f"early stopping com paciência {p['paciencia']}" if p['early_stopping'] else 'sem early stopping'
        datasets = ', '.join(DATASET_NAMES.get(d, d) for d in p['datasets'])
        epochs = f"até {format_epochs(p['epocas'])}" if p['epocas'] is not None else 'até o early stopping parar'
        description = (f"{MODEL_NAMES[configuration['modelo']]}, {epochs}, {early}, "
                       f"batch size {p['batch_size']}, datasets de treino: {datasets}")
        if p.get('execucao_teste'):
            description += f", execução de teste com {p['execucao_teste_imagens']} imagens"
        return description


    def configuration_view(self, configuration, data, detailed=False):
        view = {
            'id': configuration['id'],
            'nome': configuration['nome'],
            'modelo': configuration['modelo'],
            'modelo_nome': MODEL_NAMES[configuration['modelo']],
            'parametros': configuration['parametros'],
            'descricao': self.description(configuration),
            'disponivel': self.is_available(configuration),
            'criada_em': configuration.get('criada_em'),
            'teste': configuration.get('teste'),
            'avaliacao': configuration.get('avaliacao'),
            'treino': {k: v for k, v in (configuration.get('treino') or {}).items() if detailed or k != 'historico'},
            'origem': configuration.get('origem'),
        }
        if detailed:
            charts = os.path.join(self.configuration_folder(configuration), 'images')
            view['graficos_gerados'] = os.path.isdir(charts) and any(f.endswith('.png') for f in os.listdir(charts))
        return view


    def list_configurations(self):
        def build(data):
            items = [self.configuration_view(c, data) for c in data['configuracoes'].values()]
            return sorted(items, key=lambda c: c.get('criada_em') or '', reverse=True)
        return self.registro.read(build)


    def get_configuration(self, configuration_id):
        def build(data):
            configuration = data['configuracoes'].get(configuration_id)
            return self.configuration_view(configuration, data, detailed=True) if configuration else None
        return self.registro.read(build)


    def unique_name(self, base, data):
        existing = {c['nome'].casefold() for c in data['configuracoes'].values()}
        if base.casefold() not in existing:
            return base
        index = 2
        while f"{base} ({index})".casefold() in existing:
            index += 1
        return f"{base} ({index})"


    def suggest_name(self, model):
        # "modelo - data hora"; dois treinos no mesmo minuto recebem " (2)", " (3)"...
        model = model if model in MODELS else 'deeplabv3+'
        base = f"{MODEL_NAMES[model]} - {datetime.now():%d/%m/%Y %H:%M}"
        return self.registro.read(lambda data: self.unique_name(base, data))


    def training_defaults(self):
        status = self.dataset_service.status()
        return {
            'modelos': [{'id': key, 'nome': label} for key, label in MODEL_NAMES.items()],
            'padrao': self.default_parameters(),
            'datasets': [
                {'id': d['id'], 'nome': d['nome'], 'imagens_treino': d['imagens_treino']}
                for d in status['datasets']
            ],
        }


    def validate_training(self, form):
        # Um ou os dois modelos: cada um vira uma configuração com os mesmos parâmetros, treinadas uma depois da outra
        models = [m for m in MODELS if m in (form.get('modelos') or [])]
        if not models:
            raise Recusa('PA', 'Escolha pelo menos um modelo: FCN, DeepLabV3+ ou os dois.', 'modelos')

        def positive_int(field, label):
            try:
                value = int(form.get(field))
            except (TypeError, ValueError):
                raise Recusa('PA', f'Informe {label} como um número inteiro.', field)
            if value < 1:
                raise Recusa('PA', f'{label[0].upper() + label[1:]} precisa ser pelo menos 1.', field)
            return value

        batch_size = positive_int('batch_size', 'o batch size')

        # Execução de teste: treino leve (poucas imagens e épocas) para conferir o fluxo num computador modesto.
        # Ligada, ela desliga o early stopping e o campo único "epocas" traz as épocas do teste; a Paciência é ignorada.
        test_execution = bool(form.get('execucao_teste'))
        if test_execution:
            test_images = positive_int('execucao_teste_imagens', 'o número de imagens da execução de teste')
            if test_images < 3:
                raise Recusa('PA', 'A execução de teste precisa de pelo menos 3 imagens (2 de treino e 1 de validação).',
                             'execucao_teste_imagens')
            test_epochs = positive_int('epocas', 'o número de épocas da execução de teste')
            epochs = test_epochs
            early_stopping = False
            patience = self.settings.get_patience()
        else:
            test_images = self.settings.get_test_execution_images()
            test_epochs = self.settings.get_test_execution_epochs()
            early_stopping = bool(form.get('early_stopping'))
            # Com early stopping não há número de épocas: o treino continua até ele parar (None = sem limite)
            epochs = None if early_stopping else positive_int('epocas', 'o número de épocas')
            patience = positive_int('paciencia', 'a paciência') if early_stopping else self.settings.get_patience()

        datasets = [d for d in form.get('datasets') or [] if d in DATASET_NAMES]
        if not datasets:
            raise Recusa('PA', 'Escolha pelo menos um dataset de treino para continuar.', 'datasets')

        counts = self.dataset_service.count_images()
        missing = [DATASET_NAMES[d] for d in datasets if counts[d]['train'] == 0]
        if missing:
            raise Recusa('PA', f"{', '.join(missing)} não tem imagens no dataset montado. Monte o dataset na tela "
                               f"Datasets ou escolha outro dataset de treino.", 'datasets')

        return {
            'modelos': models,
            'parametros': {
                'epocas': epochs,
                'early_stopping': early_stopping,
                'paciencia': patience,
                'datasets': datasets,
                'batch_size': batch_size,
                # Os gráficos de treino são sempre gerados
                'graficos': True,
                'execucao_teste': test_execution,
                'execucao_teste_imagens': test_images,
                'execucao_teste_epocas': test_epochs,
            },
        }


    def start_training(self, form):
        """Cria uma configuração por modelo escolhido e põe os treinos na fila (rodam um de cada vez, na ordem)."""
        validated = self.validate_training(form)
        names = form.get('nomes') or {}
        chosen = {}
        for model in validated['modelos']:
            name = str(names.get(model) or '').strip()
            if not name:
                raise Recusa('PA', f'Informe o nome da configuração do {MODEL_NAMES[model]}.', f'nome-{model}')
            if any(name.casefold() == other.casefold() for other in chosen.values()):
                raise Recusa('PA', 'As duas configurações precisam de nomes diferentes.', f'nome-{model}')
            chosen[model] = name

        with self.registro.transaction() as data:
            for model, name in chosen.items():
                if any(c['nome'].casefold() == name.casefold() for c in data['configuracoes'].values()):
                    raise Recusa('RA', 'Já existe uma configuração com este nome. Escolha outro.', f'nome-{model}',
                                 {'sugestao': self.unique_name(name, data)})

            configuration_ids = []
            for model, name in chosen.items():
                configuration_id = new_id('c-')
                data['configuracoes'][configuration_id] = {
                    'id': configuration_id,
                    'nome': name,
                    'modelo': model,
                    'parametros': json.loads(json.dumps(validated['parametros'])),
                    'tamanho_imagem': self.settings.get_image_size(),
                    'pasta': paths.relative(paths.configuration_dir(configuration_id)),
                    'origem': 'interface',
                    'criada_em': now(),
                    'treino': {'estado': 'na fila'},
                    'teste': None,
                }
                configuration_ids.append(configuration_id)

        for configuration_id in configuration_ids:
            self.enqueue_training(configuration_id)
        return {'configuracoes': [self.get_configuration(cid) for cid in configuration_ids]}


    def restart_training(self, configuration_id, batch_size=None):
        configuration = self.registro.configuration(configuration_id)
        if configuration is None:
            raise Recusa('CE', 'Configuração não encontrada.')
        if configuration.get('origem') == 'existente':
            raise Recusa('CE', 'Esta configuração foi treinada antes da interface e não pode ser reiniciada aqui.')
        if configuration['treino'].get('estado') != 'falhou':
            raise Recusa('PA', 'Só um treino interrompido pode ser reiniciado.')

        def update(c):
            if batch_size is not None:
                value = int(batch_size)
                if value < 1:
                    raise Recusa('PA', 'O batch size precisa ser pelo menos 1.', 'batch_size')
                c['parametros']['batch_size'] = value
            c['treino'] = {'estado': 'na fila'}

        self.registro.update_configuration(configuration_id, update)
        self.enqueue_training(configuration_id)
        return self.get_configuration(configuration_id)


    def enqueue_training(self, configuration_id):
        configuration = self.registro.configuration(configuration_id)

        def on_failure(task, description):
            def update(c):
                c['treino'].update({
                    'estado': 'falhou',
                    'causa': description['causa'],
                    'sugestao': description['sugestao'],
                    'tipo_falha': description['tipo'],
                    'etapa_falha': 'treino',
                    'terminado_em': now(),
                })
                if description['causa'] == 'faltou memória no computador':
                    c['treino']['batch_size_sugerido'] = max(1, c['parametros']['batch_size'] // 2)
            self.registro.update_configuration(configuration_id, update)

        self.fila.submit('treino', f"Treino da {configuration['nome']}", lambda task: self.run_training(task, configuration_id),
                         alvo={'configuracao': configuration_id}, contexto='treino', on_failure=on_failure)


    def run_training(self, task, configuration_id):
        from modules.training.trainer.trainer import Trainer

        configuration = self.registro.configuration(configuration_id)
        p = configuration['parametros']
        overrides = {
            'Epochs': p['epocas'],
            'EarlyStopping': p['early_stopping'],
            'Patience': p['paciencia'],
            'BATCH_SIZE': p['batch_size'],
            # Configurações antigas não têm estes campos: a execução de teste fica desligada
            'Test_Execution': p.get('execucao_teste', False),
            'Test_Execution_Images': p.get('execucao_teste_imagens', self.settings.get_test_execution_images()),
            'Test_Execution_Epochs': p.get('execucao_teste_epocas', self.settings.get_test_execution_epochs()),
            **{name: name in p['datasets'] for name in DATASET_NAMES},
        }
        settings = Settings().with_overrides(overrides)
        folder = self.configuration_folder(configuration)
        os.makedirs(folder, exist_ok=True)

        # Sem limite (early stopping): não há total, o progresso mostra só a época atual
        total = p['epocas']
        if settings.is_test_execution_on():
            total = min(total or settings.get_test_execution_epochs(), settings.get_test_execution_epochs())

        self.registro.update_configuration(configuration_id, lambda c: c.update({'treino': {
            'estado': 'treinando', 'epoca': 0, 'total': total, 'historico': [], 'iniciado_em': now(),
            'etapa': 'Preparando o treino',
        }}))
        task.set_progress(0, total or 0, 'Preparando o treino')

        def on_epoch(epoch):
            entry = {
                'epoca': epoch['epoca'],
                'treino': epoch['treino'],
                'validacao': {k: epoch['validacao'][k] for k in ('loss', 'acuracia', 'miou', 'iou_trilha')} if epoch['validacao'] else None,
                'duracao_s': epoch['duracao_s'],
            }

            def update(c):
                c['treino']['epoca'] = epoch['epoca']
                c['treino']['historico'].append(entry)
                c['treino']['melhor_epoca'] = epoch['melhor_epoca']
                c['treino']['etapa'] = 'Treinando'
            self.registro.update_configuration(configuration_id, update)
            task.set_progress(epoch['epoca'], total or 0,
                              f"Época {epoch['epoca']} de {total}" if total else f"Época {epoch['epoca']} (até o early stopping parar)")

        try:
            result = Trainer(configuration['modelo'], settings, output_dir=folder, on_epoch=on_epoch).train_model()
        except ValueError as error:
            if 'Nenhuma imagem de treino' in str(error) or 'Nenhum dataset habilitado' in str(error):
                raise ErroDeUsuario('não há imagens de treino dos datasets escolhidos no dataset montado',
                                    'Monte o dataset na tela Datasets e reinicie o treino.', 'CE')
            if 'imagem de treino' in str(error):
                raise ErroDeUsuario('há imagens de treino de menos para formar um batch',
                                    'Escolha mais datasets de treino ou monte o dataset de novo.', 'CE')
            raise

        def finish_training(c):
            c['treino'].update({
                'estado': 'concluído',
                'motivo_termino': result['motivo_termino'],
                'epoca_final': result['epoca_final'],
                'melhor_epoca': result['melhor_epoca'],
                'tempo_total_s': result['tempo_total_s'],
                'terminado_em': now(),
                'etapa': None,
            })
            # Pesos novos: métricas antigas (se houver) deixam de valer até a nova avaliação
            c['teste'] = None
        self.registro.update_configuration(configuration_id, finish_training)

        # Ao fim do treino, o sistema avalia a configuração no conjunto de teste (outra tarefa da fila)
        self.enqueue_evaluation(configuration_id)


    def enqueue_evaluation(self, configuration_id):
        configuration = self.registro.configuration(configuration_id)
        if configuration is None or not self.is_available(configuration):
            raise Recusa('PA', 'Só configurações com treino concluído podem ser avaliadas.')
        if (configuration.get('avaliacao') or {}).get('estado') in ('na fila', 'processando'):
            return None

        self.registro.update_configuration(configuration_id, lambda c: c.update({'avaliacao': {
            'estado': 'na fila', 'solicitada_em': now(),
        }}))

        def on_failure(task, description):
            self.registro.update_configuration(configuration_id, lambda c: c['avaliacao'].update({
                'estado': 'falhou', 'causa': description['causa'], 'sugestao': description['sugestao'],
                'tipo_falha': description['tipo'], 'terminada_em': now(),
            }))

        return self.fila.submit('avaliacao', f"Avaliação da {configuration['nome']} no conjunto de teste",
                                lambda task: self.run_evaluation(task, configuration_id),
                                alvo={'configuracao': configuration_id}, on_failure=on_failure).to_dict()


    def run_evaluation(self, task, configuration_id):
        self.registro.update_configuration(configuration_id, lambda c: c['avaliacao'].update({
            'estado': 'processando', 'iniciada_em': now(),
        }))
        task.set_progress(0, 0, 'Avaliando no conjunto de teste')

        configuration = self.registro.configuration(configuration_id)
        if not os.path.isfile(self.weights_path(configuration)):
            raise ErroDeUsuario(f"os pesos da {configuration['nome']} não foram encontrados no computador",
                                'Confira a pasta de resultados com quem treinou a configuração e tente de novo.', 'CE')

        if self.evaluate_on_test_set(configuration_id, task) is None:
            raise ErroDeUsuario('não há conjunto de teste montado',
                                'Monte o dataset na tela Datasets e avalie a configuração lá.', 'CE')

        self.registro.update_configuration(configuration_id, lambda c: c['avaliacao'].update({
            'estado': 'concluída', 'terminada_em': now(), 'causa': None, 'sugestao': None,
        }))


    def retry_evaluation(self, configuration_id):
        configuration = self.registro.configuration(configuration_id)
        if configuration is None:
            raise Recusa('CE', 'Configuração não encontrada.')
        self.enqueue_evaluation(configuration_id)
        return self.get_configuration(configuration_id)


    def evaluate_on_test_set(self, configuration_id, task=None):
        """Segmenta o conjunto de teste montado com a configuração e guarda IoU, acurácia, tempo de
        inferência e matriz de confusão. Sem conjunto de teste montado, a configuração fica sem métricas."""
        from modules.metrics.chart import Charts
        from modules.metrics.test_evaluator import TestEvaluator
        from modules.segmentation.inference_dataset import InferenceDataset
        from modules.segmentation.predictor import Predictor
        from modules.segmentation.segmentation_service import SegmentationService

        test_set = self.dataset_service.current_test_set()
        if test_set is None:
            self.registro.update_configuration(configuration_id, lambda c: c.update({'teste': None}))
            return None

        configuration = self.registro.configuration(configuration_id)
        folder = self.configuration_folder(configuration)
        predictions_dir = os.path.join(folder, 'teste_predicoes')
        if os.path.isdir(predictions_dir):
            paths.safe_rmtree(predictions_dir)
        os.makedirs(predictions_dir, exist_ok=True)

        settings = Settings()
        service = SegmentationService(settings)
        predictor = Predictor(configuration['modelo'], configuration['tamanho_imagem'], service.device, self.weights_path(configuration))
        dataset = InferenceDataset(paths.dataset_dir('test', 'original'), predictor.transform)

        def on_image(done, total, _name):
            if task:
                task.set_progress(done, total, f'Avaliando no conjunto de teste: {done} de {total} imagens')

        segmented = service.segment_files(predictor, dataset, predictions_dir, on_image=on_image)
        evaluation = TestEvaluator(settings, Charts(settings)).evaluate_predictions(
            configuration['nome'], predictions_dir, os.path.join(folder, 'statistics'))

        if evaluation is None:
            raise ErroDeUsuario('as imagens do conjunto de teste não têm máscaras correspondentes',
                                'Monte o dataset de novo na tela Datasets.', 'CE')

        totals = evaluation['groups']['Todos']
        counts = {key: totals[key] for key in ('tp', 'fp', 'fn', 'tn')}
        times = list(segmented['inference_times'].values())
        mask_files = [image['imagem'] for image in evaluation['images']]
        result = self.build_test_result(counts, mask_files, sum(times) / len(times) if times else None)
        result['conjunto']['montado_em'] = test_set.get('montado_em')

        self.registro.update_configuration(configuration_id, lambda c: c.update({'teste': result}))
        return result


    # ------------------------------------------------------------------ sessões e execução

    def create_session(self, cycle, uploads):
        """uploads: lista de (nome do arquivo, objeto de arquivo). Retorna a sessão (rascunho) e os arquivos recusados."""
        from PIL import Image
        from processing.video import read_video_info

        cycle = (cycle or '').strip()
        if not cycle:
            raise Recusa('PA', 'Informe o ciclo de testes: o nome ou a data do teste de campo.', 'ciclo')
        if not uploads:
            raise Recusa('PA', 'Escolha pelo menos uma imagem ou um vídeo.', 'arquivos')

        session_id = new_id('s-')
        inputs_dir = os.path.join(paths.session_dir(session_id), 'entradas')
        videos_dir = os.path.join(paths.session_dir(session_id), 'videos')
        os.makedirs(inputs_dir, exist_ok=True)

        images, videos, refused, stems = [], [], [], set()

        for original_name, file in uploads:
            stem, extension = safe_filename(original_name)
            label = os.path.basename(original_name or '')

            if extension not in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
                refused.append({'nome': label, 'motivo': 'formato não aceito'})
                continue

            unique_stem, index = stem, 2
            while unique_stem in stems:
                unique_stem = f"{stem}_{index}"
                index += 1
            stems.add(unique_stem)

            if extension in IMAGE_EXTENSIONS:
                target = os.path.join(inputs_dir, unique_stem + extension)
                with open(target, 'wb') as output:
                    shutil.copyfileobj(file, output)
                try:
                    with Image.open(target) as image:
                        image.verify()
                    with Image.open(target) as image:
                        width, height = image.size
                except Exception:
                    os.remove(target)
                    refused.append({'nome': label, 'motivo': 'o arquivo não pôde ser lido como imagem'})
                    continue
                images.append({'nome': unique_stem + extension, 'origem': 'imagem', 'nome_original': label,
                               'largura': width, 'altura': height})
            else:
                os.makedirs(videos_dir, exist_ok=True)
                target = os.path.join(videos_dir, unique_stem + extension)
                with open(target, 'wb') as output:
                    shutil.copyfileobj(file, output)
                info = read_video_info(target)
                if info is None:
                    os.remove(target)
                    refused.append({'nome': label, 'motivo': 'o arquivo não pôde ser lido como vídeo'})
                    continue
                videos.append({'nome': unique_stem + extension, 'nome_original': label, 'fps': info[0],
                               'quadros_previstos': info[1], 'quadros': 0, 'estado': 'na fila'})

        session = {
            'id': session_id,
            'criada_em': now(),
            'ciclo': cycle,
            'rascunho': True,
            'imagens': images,
            'videos': videos,
            'execucoes': {},
        }

        with self.registro.transaction() as data:
            data['sessoes'][session_id] = session

        if not images and not videos:
            self.discard_draft(session_id)
            return {'sessao': None, 'recusadas': refused}

        return {'sessao': self.get_session(session_id), 'recusadas': refused}


    def discard_draft(self, session_id):
        with self.registro.transaction() as data:
            session = data['sessoes'].get(session_id)
            if session and session.get('rascunho'):
                del data['sessoes'][session_id]
                folder = paths.session_dir(session_id)
                if os.path.isdir(folder):
                    paths.safe_rmtree(folder)


    def get_session(self, session_id):
        def build(data):
            session = data['sessoes'].get(session_id)
            if session is None:
                return None
            view = dict(session)
            view['configuracoes'] = {
                cid: {'nome': c['nome'], 'descricao': self.description(c)}
                for cid in session['execucoes']
                if (c := data['configuracoes'].get(cid))
            }
            return view
        return self.registro.read(build)


    def list_sessions(self):
        """Resumo de todas as sessões (sem os rascunhos), da mais recente para a mais antiga."""
        def summary(session, data):
            executions = []
            for cid, e in session['execucoes'].items():
                c = data['configuracoes'].get(cid)
                executions.append({
                    'configuracao': cid,
                    'nome': c['nome'] if c else cid,
                    'estado': e.get('estado'),
                    'concluidas': len(e.get('concluidas') or []),
                    'falhas': len(e.get('falhas') or {}),
                    'data': e.get('data'),
                })
            videos = session.get('videos', [])
            running = any(e['estado'] in ('na fila', 'processando') for e in executions) \
                or any(v.get('estado') in ('na fila', 'processando') for v in videos)
            failed = any(e['estado'] == 'falhou' or e['falhas'] for e in executions) \
                or any(v.get('estado') == 'falhou' for v in videos)
            if running:
                state = 'processando'
            elif failed:
                state = 'falhou'
            elif executions:
                state = 'concluído'
            else:
                state = None
            dates = [e['data'] for e in executions if e['data']]
            return {
                'id': session['id'],
                'ciclo': session['ciclo'],
                'criada_em': session.get('criada_em'),
                'executada_em': max(dates) if dates else None,
                'imagens': sum(1 for i in session['imagens'] if i.get('origem') != 'quadro'),
                'videos': len(videos),
                'execucoes': executions,
                'estado': state,
                'com_resultado': any(e['concluidas'] for e in executions),
            }

        def build(data):
            items = [summary(s, data) for s in data['sessoes'].values() if not s.get('rascunho')]
            return sorted(items, key=lambda s: s.get('criada_em') or '', reverse=True)
        return self.registro.read(build)


    def execute(self, session_id, configuration_ids, images=None):
        configuration_ids = list(dict.fromkeys(configuration_ids or []))
        if not configuration_ids:
            raise Recusa('PA', 'Escolha pelo menos uma configuração.', 'configuracoes')

        with self.registro.transaction() as data:
            session = data['sessoes'].get(session_id)
            if session is None:
                raise Recusa('CE', 'Sessão não encontrada.')

            for configuration_id in configuration_ids:
                configuration = data['configuracoes'].get(configuration_id)
                if configuration is None or not self.is_available(configuration):
                    raise Recusa('PA', 'Só configurações com treino concluído podem ser executadas.', 'configuracoes')

            if images is not None:
                known = {image['nome'] for image in session['imagens']}
                images = [name for name in images if name in known]
                if not images:
                    raise Recusa('PA', 'Escolha pelo menos uma imagem.', 'imagens')

            session['rascunho'] = False
            data['ultima_sessao'] = session_id

            for configuration_id in configuration_ids:
                execution = session['execucoes'].setdefault(configuration_id, {
                    'concluidas': [], 'falhas': {}, 'deixadas_de_fora': [], 'pedidas': [],
                })
                requested = images if images is not None else None
                execution.update({'estado': 'na fila', 'causa': None, 'sugestao': None, 'pendentes': requested})

            pending_videos = [video['nome'] for video in session['videos'] if video.get('estado') in ('na fila', 'falhou')]
            for video in session['videos']:
                if video['nome'] in pending_videos:
                    video['estado'] = 'na fila'

        for video in pending_videos:
            self.fila.submit('extracao', f'Extração dos quadros de {video}',
                             lambda task, video=video: self.run_extraction(task, session_id, video),
                             alvo={'sessao': session_id, 'video': video},
                             on_failure=lambda task, d, video=video: self.extraction_failed(session_id, video, d))

        for configuration_id in configuration_ids:
            self.enqueue_execution(session_id, configuration_id)

        return self.get_session(session_id)


    def enqueue_execution(self, session_id, configuration_id):
        configuration = self.registro.configuration(configuration_id)

        def on_failure(task, description):
            def update(session):
                session['execucoes'][configuration_id].update({
                    'estado': 'falhou', 'causa': description['causa'], 'sugestao': description['sugestao'],
                    'tipo_falha': description['tipo'],
                })
            self.registro.update_session(session_id, update)

        self.fila.submit('execucao', f"Execução da {configuration['nome']}",
                         lambda task: self.run_execution(task, session_id, configuration_id),
                         alvo={'sessao': session_id, 'configuracao': configuration_id}, on_failure=on_failure)


    def extraction_failed(self, session_id, video, description):
        def update(session):
            for item in session['videos']:
                if item['nome'] == video:
                    item.update({'estado': 'falhou', 'causa': description['causa']})
        self.registro.update_session(session_id, update)


    def run_extraction(self, task, session_id, video_name):
        from processing.video import extract_frames

        folder = paths.session_dir(session_id)
        stem = os.path.splitext(video_name)[0]
        self.registro.update_session(session_id, lambda s: [v.update({'estado': 'processando'}) for v in s['videos'] if v['nome'] == video_name])

        def on_frame(done, total):
            if done % 10 == 0 or done == total:
                task.set_progress(done, total, f'Extraindo os quadros de {video_name}: {done} de {total}')

        names, fps = extract_frames(os.path.join(folder, 'videos', video_name), os.path.join(folder, 'entradas'), stem, on_frame)

        def update(session):
            known = {image['nome'] for image in session['imagens']}
            for index, name in enumerate(names):
                if name not in known:
                    session['imagens'].append({'nome': name, 'origem': 'quadro', 'video': video_name, 'quadro': index + 1})
            for video in session['videos']:
                if video['nome'] == video_name:
                    video.update({'estado': 'concluído', 'quadros': len(names), 'fps': fps})
        self.registro.update_session(session_id, update)


    def run_execution(self, task, session_id, configuration_id):
        from modules.segmentation.inference_dataset import InferenceDataset
        from modules.segmentation.predictor import Predictor
        from modules.segmentation.segmentation_service import SegmentationService

        session = self.registro.session(session_id)
        configuration = self.registro.configuration(configuration_id)
        execution = session['execucoes'][configuration_id]

        excluded = set(execution.get('deixadas_de_fora', []))
        requested = execution.get('pendentes')
        if requested is None:
            requested = [image['nome'] for image in session['imagens']]
        requested = [name for name in requested if name not in excluded]

        if not requested:
            raise ErroDeUsuario('não há imagens para segmentar nesta sessão',
                                'Volte e envie as imagens de novo.', 'RA')

        def start(s):
            e = s['execucoes'][configuration_id]
            e['estado'] = 'processando'
            e['pedidas'] = list(dict.fromkeys(e.get('pedidas', []) + requested))
            e['total_atual'] = len(requested)
        self.registro.update_session(session_id, start)
        task.set_progress(0, len(requested), f"0 de {len(requested)} imagens")

        weights = self.weights_path(configuration)
        if not os.path.isfile(weights):
            raise ErroDeUsuario(f"o arquivo de pesos da {configuration['nome']} não foi encontrado no computador",
                                'Treine a configuração de novo ou confira a pasta de resultados com quem a treinou.', 'CE')

        service = SegmentationService(Settings())
        predictor = Predictor(configuration['modelo'], configuration['tamanho_imagem'], service.device, weights)
        folder = paths.session_dir(session_id)
        output_dir = os.path.join(folder, 'mascaras', configuration_id)
        os.makedirs(output_dir, exist_ok=True)
        dataset = InferenceDataset(os.path.join(folder, 'entradas'), predictor.transform, images=requested)

        def on_image(done, total, _name):
            task.set_progress(done, total, f"{done} de {total} imagens")
            if done % 5 == 0 or done == total:
                self.registro.update_session(session_id, lambda s: s['execucoes'][configuration_id].update({'progresso': done}))

        segmented = service.segment_files(predictor, dataset, output_dir, on_image=on_image, stop_on_error=False)

        from app.web.erros import describe
        failures = {name: describe(error) for name, error in segmented['failures'].items()}
        for name, error in segmented['failures'].items():
            logger.error("Falha ao segmentar %s com %s: %r", name, configuration['nome'], error)

        succeeded = [name for name in requested if name not in failures]
        # Só a execução inteira falha quando nenhuma imagem tem resultado; repetir uma imagem que falha de novo
        # mantém as já segmentadas e deixa a falha só na linha da imagem
        if not succeeded and not execution.get('concluidas'):
            first = next(iter(failures.values()))
            raise ErroDeUsuario(first['causa'], first['sugestao'], first['tipo'])

        times = list(segmented['inference_times'].values())

        def finish(s):
            e = s['execucoes'][configuration_id]
            e['concluidas'] = list(dict.fromkeys(e.get('concluidas', []) + succeeded))
            for name in succeeded:
                e['falhas'].pop(name, None)
            e['falhas'].update(failures)
            e.update({'estado': 'concluído', 'data': now(), 'pendentes': None, 'progresso': None,
                      'tempo_medio_ms': sum(times) / len(times) if times else None})
        self.registro.update_session(session_id, finish)

        with self.registro.transaction() as data:
            data['configuracao_em_uso'] = configuration_id

        self.build_videos(task, session_id, configuration_id)


    def build_videos(self, task, session_id, configuration_id):
        from processing.video import build_overlay_video

        session = self.registro.session(session_id)
        configuration = self.registro.configuration(configuration_id)
        execution = session['execucoes'][configuration_id]
        done = set(execution['concluidas'])
        folder = paths.session_dir(session_id)

        for video in session['videos']:
            frames = [image['nome'] for image in session['imagens'] if image.get('video') == video['nome']]
            if not frames or not all(name in done for name in frames):
                continue

            task.set_progress(texto=f"Montando o vídeo com a sobreposição de {video['nome']}")
            output_dir = os.path.join(folder, 'videos_sobreposicao')
            os.makedirs(output_dir, exist_ok=True)
            output = os.path.join(output_dir, f"{configuration_id}_{video['nome']}")
            build_overlay_video(os.path.join(folder, 'entradas'), os.path.join(folder, 'mascaras', configuration_id),
                                frames, output, video['fps'], ascii_text(configuration['nome']))

            self.registro.update_session(session_id, lambda s, name=video['nome']: s['execucoes'][configuration_id]
                                         .setdefault('videos', {}).update({name: os.path.basename(output)}))


    def handle_image_failure(self, session_id, configuration_id, image, action):
        if action not in ('tentar de novo', 'deixar de fora'):
            raise Recusa('PA', 'Ação desconhecida.')

        with self.registro.transaction() as data:
            session = data['sessoes'].get(session_id)
            execution = session and session['execucoes'].get(configuration_id)
            if not execution or image not in execution.get('falhas', {}):
                raise Recusa('CE', 'Esta imagem não está entre as que falharam.')

            if action == 'deixar de fora':
                execution['falhas'].pop(image)
                execution['deixadas_de_fora'] = list(dict.fromkeys(execution.get('deixadas_de_fora', []) + [image]))
                return self.get_session(session_id)

            execution.update({'estado': 'na fila', 'pendentes': [image]})

        self.enqueue_execution(session_id, configuration_id)
        return self.get_session(session_id)


    def handle_execution_failure(self, session_id, configuration_id, action):
        if action not in ('tentar de novo', 'deixar de fora'):
            raise Recusa('PA', 'Ação desconhecida.')

        with self.registro.transaction() as data:
            session = data['sessoes'].get(session_id)
            execution = session and session['execucoes'].get(configuration_id)
            if not execution or execution.get('estado') != 'falhou':
                raise Recusa('CE', 'Esta execução não falhou.')

            if action == 'deixar de fora':
                del session['execucoes'][configuration_id]
                return self.get_session(session_id)

            execution.update({'estado': 'na fila', 'causa': None, 'sugestao': None})

        self.enqueue_execution(session_id, configuration_id)
        return self.get_session(session_id)


    def retry_video(self, session_id, video_name):
        with self.registro.transaction() as data:
            session = data['sessoes'].get(session_id)
            video = next((v for v in session['videos'] if v['nome'] == video_name), None) if session else None
            if not video or video.get('estado') != 'falhou':
                raise Recusa('CE', 'Este vídeo não falhou.')
            video['estado'] = 'na fila'
            pending = [cid for cid, e in session['execucoes'].items()]
            for cid in pending:
                session['execucoes'][cid].update({'estado': 'na fila', 'pendentes': None})

        self.fila.submit('extracao', f'Extração dos quadros de {video_name}',
                         lambda task: self.run_extraction(task, session_id, video_name),
                         alvo={'sessao': session_id, 'video': video_name},
                         on_failure=lambda task, d: self.extraction_failed(session_id, video_name, d))
        for cid in pending:
            self.enqueue_execution(session_id, cid)
        return self.get_session(session_id)


    def leave_video_out(self, session_id, video_name):
        with self.registro.transaction() as data:
            session = data['sessoes'].get(session_id)
            if not session:
                raise Recusa('CE', 'Sessão não encontrada.')
            session['videos'] = [v for v in session['videos'] if v['nome'] != video_name]
        return self.get_session(session_id)


    def session_file(self, session_id, kind, name, configuration_id=None):
        session = self.registro.session(session_id)
        if session is None:
            return None
        folder = paths.session_dir(session_id)

        if kind == 'imagem':
            if name not in {image['nome'] for image in session['imagens']}:
                return None
            return os.path.join(folder, 'entradas', name)

        if kind == 'mascara':
            if name not in {image['nome'] for image in session['imagens']} or configuration_id not in session['execucoes']:
                return None
            return os.path.join(folder, 'mascaras', configuration_id, mask_name(name))

        if kind == 'video':
            execution = session['execucoes'].get(configuration_id) or {}
            file = (execution.get('videos') or {}).get(name)
            return os.path.join(folder, 'videos_sobreposicao', file) if file else None

        return None


    def download_name(self, configuration_id, image, suffix):
        """Nome do arquivo baixado: imagem, configuração e o tipo, para não confundir downloads de configurações diferentes."""
        configuration = self.registro.configuration(configuration_id) or {}
        stem, _ = safe_filename(f"{os.path.splitext(image)[0]}_{configuration.get('nome', configuration_id)}_{suffix}.png")
        return f"{stem}.png"


    def overlay_image(self, session_id, configuration_id, image):
        """PNG com a sobreposição da máscara sobre a imagem original, gerado na hora para o download."""
        from processing.video import build_overlay_image

        image_path = self.session_file(session_id, 'imagem', image)
        mask_path = self.session_file(session_id, 'mascara', image, configuration_id)
        if not image_path or not mask_path or not os.path.isfile(image_path) or not os.path.isfile(mask_path):
            return None
        return build_overlay_image(image_path, mask_path)


    # ------------------------------------------------------------------ ciclos e desempenho

    def cycles(self):
        def build(data):
            cycles = {}
            for session in data['sessoes'].values():
                if session.get('rascunho'):
                    continue
                item = cycles.setdefault(session['ciclo'], {'ciclo': session['ciclo'], 'sessoes': 0, 'configuracoes': [], 'ultima': ''})
                item['sessoes'] += 1
                item['ultima'] = max(item['ultima'], session['criada_em'])
                for cid, execution in session['execucoes'].items():
                    if execution.get('estado') == 'concluído' and cid not in item['configuracoes']:
                        item['configuracoes'].append(cid)

            return sorted(cycles.values(), key=lambda c: c['ultima'], reverse=True)
        return self.registro.read(build)


    def execution_dates(self, data, cycle):
        dates = {}
        for session in data['sessoes'].values():
            if session.get('rascunho') or (cycle and session['ciclo'] != cycle):
                continue
            for cid, execution in session['execucoes'].items():
                if execution.get('estado') == 'concluído' and execution.get('data'):
                    dates[cid] = max(dates.get(cid, ''), execution['data'])
        return dates


    def performance(self, configuration_ids, cycle=None, compare_anyway=False):
        configuration_ids = list(dict.fromkeys(configuration_ids or []))
        if not configuration_ids:
            raise Recusa('PA', 'Escolha pelo menos uma configuração para comparar.', 'configuracoes')

        def build(data):
            configurations = []
            for cid in configuration_ids:
                configuration = data['configuracoes'].get(cid)
                if configuration is None or not self.is_available(configuration):
                    raise Recusa('PA', 'Só configurações com treino concluído podem ser comparadas.', 'configuracoes')
                configurations.append(configuration)

            dates = self.execution_dates(data, cycle)
            if cycle:
                missing = [c['nome'] for c in configurations if c['id'] not in dates]
                if missing:
                    raise Recusa('CE', '', dados={'ruptura': 'execucao_faltante', 'configuracoes': missing, 'ciclo': cycle})

            without_test = [c['nome'] for c in configurations if not c.get('teste')]
            if without_test:
                raise Recusa('CE', '', dados={'ruptura': 'sem_avaliacao_no_teste', 'configuracoes': without_test})

            sets = {c['teste']['conjunto']['id'] for c in configurations}
            if len(sets) > 1 and not compare_anyway:
                raise Recusa('AL', '', dados={
                    'ruptura': 'conjuntos_diferentes',
                    'conjuntos': [{'configuracao': c['nome'], 'conjunto': c['teste']['conjunto']} for c in configurations],
                })

            rows = []
            for c in configurations:
                rows.append({
                    'id': c['id'],
                    'nome': c['nome'],
                    'descricao': self.description(c),
                    'conjunto': c['teste']['conjunto'],
                    'avaliado_em': c['teste'].get('avaliado_em'),
                    'data_execucao': dates.get(c['id']),
                    'metricas': c['teste']['metricas'],
                    'matriz': c['teste']['matriz'],
                })

            highest = {}
            for metric in HIGHLIGHTED_METRICS:
                values = [(row['metricas'].get(metric), row['id']) for row in rows if row['metricas'].get(metric) is not None]
                if len(rows) > 1 and values:
                    best = max(value for value, _ in values)
                    highest[metric] = [cid for value, cid in values if abs(value - best) < 1e-12]

            reference = None
            in_use = data['configuracoes'].get(data.get('configuracao_em_uso') or '')
            if in_use and in_use.get('teste'):
                reference = {
                    'configuracao': in_use['id'],
                    'nome': in_use['nome'],
                    'metricas': in_use['teste']['metricas'],
                    'conjunto': in_use['teste']['conjunto'],
                    'origem': f"configuração em uso (a última executada): {in_use['nome']}, no conjunto de teste",
                }

            return {
                'ciclo': cycle,
                'configuracoes': rows,
                'maior_valor': highest,
                'referencia': reference,
                'conjuntos_iguais': len(sets) == 1,
                'calculado_em': now(),
            }

        with self.registro.lock:
            return self.registro.read(build)


    # ------------------------------------------------------------------ datasets

    def datasets_status(self):
        status = self.dataset_service.status()
        current = self.dataset_service.current_test_set()

        def build(data):
            outdated, evaluations = [], []
            for configuration in data['configuracoes'].values():
                if not self.is_available(configuration):
                    continue
                test = configuration.get('teste')
                evaluation = configuration.get('avaliacao') or {}
                missing = current and (not test or test['conjunto']['id'] != current['id'])
                if missing and evaluation.get('estado') not in ('na fila', 'processando'):
                    outdated.append({'id': configuration['id'], 'nome': configuration['nome'],
                                     'motivo': 'sem avaliação no conjunto de teste' if not test else 'avaliada em outro conjunto de teste'})
                if evaluation:
                    evaluations.append({'id': configuration['id'], 'nome': configuration['nome'], **evaluation})
            evaluations.sort(key=lambda e: e.get('solicitada_em') or '', reverse=True)
            return outdated, evaluations

        outdated, evaluations = self.registro.read(build)
        tasks = self.fila.list()
        assemblies = [t for t in tasks if t['tipo'] == 'dataset' and t['alvo'].get('dataset') == 'todos']

        status['conjunto_de_teste'] = current
        status['configuracoes_a_avaliar'] = outdated
        status['avaliacoes'] = evaluations
        status['ultima_montagem'] = assemblies[-1] if assemblies else None
        status['tarefas'] = [t for t in tasks if t['tipo'] == 'dataset' and t['estado'] not in ('concluído', 'falhou')]
        status['tarefas_recentes'] = [t for t in tasks if t['tipo'] == 'dataset'][-5:]
        return status


    def download_dataset(self, name):
        if name not in DATASET_NAMES or name == 'CaSSeD':
            raise Recusa('CE', 'O CaSSeD é copiado manualmente para a pasta raw/CaSSed_Dataset.')

        def run(task):
            def on_progress(part, parts, done, total):
                if total:
                    task.set_progress(done, total, f"Baixando {DATASET_NAMES[name]}: parte {part} de {parts} "
                                                   f"({done / 1024 ** 2:.0f} de {total / 1024 ** 2:.0f} MB)")
            task.set_progress(texto=f'Baixando {DATASET_NAMES[name]}')
            self.dataset_service.download(name, on_progress)

        return self.fila.submit('dataset', f'Download do {DATASET_NAMES[name]}', run, alvo={'dataset': name}, contexto='dataset').to_dict()


    def rebuild_dataset(self):
        def run(task):
            self.dataset_service.rebuild_dataset(lambda step, total, label: task.set_progress(step, total, label))

        return self.fila.submit('dataset', 'Montagem do dataset', run, alvo={'dataset': 'todos'}, contexto='dataset').to_dict()


    def evaluate_configurations(self, configuration_ids):
        if not configuration_ids:
            raise Recusa('PA', 'Escolha pelo menos uma configuração para avaliar.', 'configuracoes')
        tasks = []
        for configuration_id in configuration_ids:
            configuration = self.registro.configuration(configuration_id)
            if configuration is None or not self.is_available(configuration):
                continue
            task = self.enqueue_evaluation(configuration_id)
            if task:
                tasks.append(task)
        return tasks


    # ------------------------------------------------------------------ estado geral

    def overview(self):
        tasks = self.fila.list()

        def build(data):
            in_use = data['configuracoes'].get(data.get('configuracao_em_uso') or '')
            trainings = [c for c in data['configuracoes'].values() if c.get('origem') == 'interface']
            latest_training = max(trainings, key=lambda c: (c['treino'].get('iniciado_em') or c['criada_em']), default=None)
            return {
                'configuracao_em_uso': {'id': in_use['id'], 'nome': in_use['nome']} if in_use else None,
                'ultima_sessao': data.get('ultima_sessao') if data.get('ultima_sessao') in data['sessoes'] else None,
                'treino_recente': {
                    'id': latest_training['id'],
                    'nome': latest_training['nome'],
                    'estado': latest_training['treino'].get('estado'),
                    'epoca': latest_training['treino'].get('epoca'),
                    'total': latest_training['treino'].get('total'),
                    'avaliacao': (latest_training.get('avaliacao') or {}).get('estado'),
                } if latest_training else None,
            }

        view = self.registro.read(build)
        view['tarefas'] = [t for t in tasks if t['estado'] not in ('concluído', 'falhou')]
        view['tarefas_recentes'] = tasks[-20:]
        return view

