"""Traduz exceções do código do TCC para falas em linguagem de usuário.

A interface nunca mostra traceback: a causa e o que fazer aparecem na tela, e os detalhes técnicos
vão só para o arquivo de logs do sistema (results/logs_sistema.txt), nunca para o terminal."""
import io
import os
import sys
import logging
import threading

from configs import paths

logger = logging.getLogger('interface')


class ErroDeUsuario(Exception):
    """Falha prevista, já descrita para o usuário. tipo: 'RA' (resolve no sistema) ou 'CE' (resolve fora dele)."""

    def __init__(self, causa, sugestao=None, tipo='CE'):
        super().__init__(causa)
        self.causa = causa
        self.sugestao = sugestao
        self.tipo = tipo


# Saída do código do TCC (print, avisos e tracebacks) capturada pelo redirect_output
output_logger = logging.getLogger('interface.saida')
_file_handler = None


def configure_logging():
    """Logs da interface só no arquivo de logs do sistema (sem StreamHandler: nada vai para o terminal)."""
    global _file_handler
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if _file_handler is not None:
        return

    try:
        os.makedirs(os.path.dirname(paths.SYSTEM_LOG_FILE), exist_ok=True)
        _file_handler = logging.FileHandler(paths.SYSTEM_LOG_FILE, encoding='utf-8')
    except OSError:
        _file_handler = logging.NullHandler()
    _file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(_file_handler)


class _LogStream(io.TextIOBase):
    """Arquivo de texto falso: cada linha escrita vira um registro no log do sistema."""

    def __init__(self, level):
        self.level = level
        self.buffer_text = ''
        self.lock = threading.Lock()

    def writable(self):
        return True

    def write(self, text):
        with self.lock:
            # \r (barras de progresso) conta como fim de linha, para não acumular texto
            self.buffer_text += str(text).replace('\r', '\n')
            *lines, self.buffer_text = self.buffer_text.split('\n')
        for line in lines:
            if line.strip():
                output_logger.log(self.level, line.rstrip())
        return len(text)

    def flush(self):
        with self.lock:
            line, self.buffer_text = self.buffer_text, ''
        if line.strip():
            output_logger.log(self.level, line.rstrip())

    def isatty(self):
        return False


def redirect_output():
    """Manda print(), avisos e tracebacks (stdout e stderr) para o arquivo de logs do sistema."""
    configure_logging()
    sys.stdout = _LogStream(logging.INFO)
    sys.stderr = _LogStream(logging.ERROR)


def is_out_of_memory(error):
    try:
        import torch
        if isinstance(error, torch.cuda.OutOfMemoryError):
            return True
    except (ImportError, AttributeError):
        pass

    text = str(error).lower()
    return isinstance(error, MemoryError) or 'out of memory' in text or 'cuda error: out of memory' in text


def describe(error, contexto='execucao'):
    """Retorna {causa, sugestao, tipo} para uma exceção. contexto: 'execucao', 'treino' ou 'dataset'."""
    if isinstance(error, ErroDeUsuario):
        return {'causa': error.causa, 'sugestao': error.sugestao, 'tipo': error.tipo}

    if is_out_of_memory(error):
        if contexto == 'treino':
            return {
                'causa': 'faltou memória no computador',
                'sugestao': 'Reduzir o batch size costuma resolver.',
                'tipo': 'RA',
            }
        return {
            'causa': 'faltou memória no computador',
            'sugestao': 'Tente de novo. Se continuar, feche outros programas que usam a placa de vídeo ou use outro computador.',
            'tipo': 'RA',
        }

    try:
        from PIL import UnidentifiedImageError
        if isinstance(error, UnidentifiedImageError):
            return {
                'causa': 'o arquivo não pôde ser lido como imagem (ele pode estar corrompido)',
                'sugestao': 'Deixe esta imagem de fora ou envie o arquivo de novo.',
                'tipo': 'RA',
            }
    except ImportError:
        pass

    try:
        import requests
        if isinstance(error, requests.exceptions.RequestException):
            return {
                'causa': 'não foi possível baixar os arquivos do site do dataset',
                'sugestao': 'Confira a conexão com a internet e tente de novo.',
                'tipo': 'CE',
            }
    except ImportError:
        pass

    # Imagem cortada ou corrompida que só falha ao ser lida por inteiro
    if isinstance(error, OSError) and ('truncated' in str(error).lower() or 'cannot identify image' in str(error).lower()):
        return {
            'causa': 'o arquivo não pôde ser lido como imagem (ele pode estar corrompido)',
            'sugestao': 'Deixe esta imagem de fora ou envie o arquivo de novo.',
            'tipo': 'RA',
        }

    if isinstance(error, OSError) and getattr(error, 'errno', None) == 28:
        return {
            'causa': 'o disco do computador está cheio',
            'sugestao': 'Libere espaço no disco e tente de novo.',
            'tipo': 'CE',
        }

    return {
        'causa': 'ocorreu um erro inesperado',
        'sugestao': 'Tente de novo. Se continuar, avise quem mantém o sistema: os detalhes técnicos foram '
                    'registrados em results/logs_sistema.txt.',
        'tipo': 'CE',
    }
