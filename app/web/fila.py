"""Fila de tarefas: treinos, execuções e preparação dos datasets rodam uma de cada vez, em segundo plano.

Uma de cada vez porque todas usam a mesma placa de vídeo; rodar duas juntas tende a faltar memória.
A fila vive só enquanto a interface está aberta (fechar a interface encerra o treino)."""
import queue
import threading
import traceback

from app.web.erros import describe, logger
from app.web.registro import new_id, now

MAX_FINISHED = 200


class Tarefa:

    def __init__(self, tipo, titulo, alvo, function, contexto):
        self.id = new_id('t-')
        self.tipo = tipo
        self.titulo = titulo
        self.alvo = alvo
        self.function = function
        self.contexto = contexto
        self.estado = 'na fila'
        self.progresso = {'atual': 0, 'total': 0, 'texto': ''}
        self.causa = None
        self.sugestao = None
        self.criada_em = now()
        self.terminada_em = None
        self.lock = threading.Lock()


    def set_progress(self, atual=None, total=None, texto=None):
        with self.lock:
            if atual is not None:
                self.progresso['atual'] = atual
            if total is not None:
                self.progresso['total'] = total
            if texto is not None:
                self.progresso['texto'] = texto


    def to_dict(self):
        with self.lock:
            return {
                'id': self.id,
                'tipo': self.tipo,
                'titulo': self.titulo,
                'alvo': self.alvo,
                'estado': self.estado,
                'progresso': dict(self.progresso),
                'causa': self.causa,
                'sugestao': self.sugestao,
                'criada_em': self.criada_em,
                'terminada_em': self.terminada_em,
            }


class FilaDeTarefas:

    def __init__(self):
        self.pending = queue.Queue()
        self.tasks = []
        self.lock = threading.Lock()
        self.worker = threading.Thread(target=self.run, name='fila-de-tarefas', daemon=True)
        self.worker.start()


    def submit(self, tipo, titulo, function, alvo=None, contexto='execucao', on_failure=None):
        """function(tarefa) faz o trabalho; on_failure(tarefa, descricao) registra a falha onde a interface a mostra."""
        task = Tarefa(tipo, titulo, alvo or {}, function, contexto)
        task.on_failure = on_failure

        with self.lock:
            self.tasks.append(task)
            finished = [t for t in self.tasks if t.estado in ('concluído', 'falhou')]
            for old in finished[:-MAX_FINISHED]:
                self.tasks.remove(old)

        self.pending.put(task)
        return task


    def run(self):
        while True:
            task = self.pending.get()
            with task.lock:
                task.estado = 'treinando' if task.tipo == 'treino' else 'processando'

            try:
                task.function(task)
            except Exception as error:
                logger.error("Tarefa %s (%s) falhou:\n%s", task.titulo, task.id, traceback.format_exc())
                description = describe(error, task.contexto)

                with task.lock:
                    task.estado = 'falhou'
                    task.causa = description['causa']
                    task.sugestao = description['sugestao']

                if task.on_failure:
                    try:
                        task.on_failure(task, description)
                    except Exception:
                        logger.error("Falha ao registrar a falha da tarefa %s:\n%s", task.id, traceback.format_exc())
            else:
                with task.lock:
                    task.estado = 'concluído'
            finally:
                with task.lock:
                    task.terminada_em = now()


    def list(self):
        with self.lock:
            return [task.to_dict() for task in self.tasks]


    def active(self, tipo=None):
        with self.lock:
            return [task.to_dict() for task in self.tasks
                    if task.estado not in ('concluído', 'falhou') and (tipo is None or task.tipo == tipo)]


    def get(self, task_id):
        with self.lock:
            for task in self.tasks:
                if task.id == task_id:
                    return task.to_dict()
        return None
