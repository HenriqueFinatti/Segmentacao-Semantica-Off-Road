"""Traduz exceções do código do TCC para falas em linguagem de usuário.

A interface nunca mostra traceback: a causa e o que fazer aparecem na tela, e os detalhes técnicos
vão só para o terminal e para results/interface.log."""
import logging

from configs import paths

logger = logging.getLogger('interface')


class ErroDeUsuario(Exception):
    """Falha prevista, já descrita para o usuário. tipo: 'RA' (resolve no sistema) ou 'CE' (resolve fora dele)."""

    def __init__(self, causa, sugestao=None, tipo='CE'):
        super().__init__(causa)
        self.causa = causa
        self.sugestao = sugestao
        self.tipo = tipo


def configure_logging():
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    try:
        import os
        os.makedirs(paths.RESULTS_DIR, exist_ok=True)
        file_handler = logging.FileHandler(paths.INTERFACE_LOG_FILE, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        pass


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
                    'registrados no terminal e em results/interface.log.',
        'tipo': 'CE',
    }
