"""Formato das mensagens entre o cliente do CARLA e o servidor de direção.

Este arquivo roda nos dois lados, então precisa funcionar em Python 3.6 e usar só a biblioteca padrão.
"""
import json
import struct

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5555

FRAME_WIDTH = 800
FRAME_HEIGHT = 600

_HEADER = struct.Struct('!II')


def send_message(sock, message, payload=b''):
    body = json.dumps(message).encode('utf-8')
    sock.sendall(_HEADER.pack(len(body), len(payload)) + body + payload)


def recv_message(sock):
    body_size, payload_size = _HEADER.unpack(_recv_exact(sock, _HEADER.size))
    message = json.loads(_recv_exact(sock, body_size).decode('utf-8'))
    return message, _recv_exact(sock, payload_size)


def _recv_exact(sock, size):
    chunks = []
    missing = size

    while missing > 0:
        chunk = sock.recv(min(missing, 1024 * 1024))
        if not chunk:
            raise ConnectionError('Conexão encerrada no meio de uma mensagem')
        chunks.append(chunk)
        missing -= len(chunk)

    return b''.join(chunks)
