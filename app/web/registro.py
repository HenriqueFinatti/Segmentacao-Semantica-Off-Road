"""Persistência local da interface em um único JSON (results/registro.json).

Guarda o que não sai do código de treino: configurações nomeadas, sessões de segmentação, avaliações
das imagens, conclusões (validação, experimento e recomendação) e a decisão da coordenação.
Os arquivos grandes (pesos, imagens, máscaras) ficam nas pastas de cada configuração e de cada sessão."""
import os
import json
import uuid
import threading
from contextlib import contextmanager
from datetime import datetime

from configs import paths

VERSION = 1


def now():
    return datetime.now().isoformat(timespec='seconds')


def new_id(prefix=''):
    return f"{prefix}{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"


def empty_registry():
    return {
        'versao': VERSION,
        'configuracoes': {},
        'sessoes': {},
        'conclusoes': {},
        # A configuração em uso é a última executada (decisão da equipe para o protótipo)
        'configuracao_em_uso': None,
        'ultima_sessao': None,
    }


class Registro:

    def __init__(self, path=None):
        self.path = path or paths.REGISTRY_FILE
        self.lock = threading.RLock()
        self.data = self.load()


    def load(self):
        if not os.path.isfile(self.path):
            return empty_registry()

        with open(self.path, encoding='utf-8') as f:
            data = json.load(f)

        # Chaves novas entram sem perder o que já foi registrado
        for key, value in empty_registry().items():
            data.setdefault(key, value)
        return data


    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        temp_path = self.path + '.tmp'

        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

        # Troca atômica: o registro nunca fica pela metade se o programa parar no meio da gravação
        os.replace(temp_path, self.path)


    @contextmanager
    def transaction(self):
        with self.lock:
            yield self.data
            self.save()


    def read(self, function):
        with self.lock:
            return json.loads(json.dumps(function(self.data)))


    # Atalhos

    def configuration(self, configuration_id):
        with self.lock:
            return self.data['configuracoes'].get(configuration_id)


    def session(self, session_id):
        with self.lock:
            return self.data['sessoes'].get(session_id)


    def update_configuration(self, configuration_id, function):
        with self.transaction() as data:
            function(data['configuracoes'][configuration_id])


    def update_session(self, session_id, function):
        with self.transaction() as data:
            function(data['sessoes'][session_id])
