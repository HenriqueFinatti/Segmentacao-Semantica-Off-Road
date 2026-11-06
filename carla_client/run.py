import argparse
import queue
import socket
import time

from carla_client.env import CarlaEnv
from carla_client.protocol import SERVER_HOST, SERVER_PORT, recv_message, send_message

RETRY_SECONDS = 2

# Erros de quando o CARLA ou o servidor de direção param no meio de uma execução
EPISODE_ERRORS = (ConnectionError, RuntimeError, queue.Empty)


def connect(host, port):
    while True:
        try:
            connection = socket.create_connection((host, port))
            connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            return connection
        except OSError:
            time.sleep(RETRY_SECONDS)


def run_episode(connection, env):
    send_message(connection, {'type': 'hello'})
    config, _ = recv_message(connection)
    print('Iniciando {map} com clima {weather}'.format(**config), flush=True)

    try:
        env.start(config['map'], config['weather'], config['spawn'], config['fps'])

        while True:
            state, frame = env.tick()
            send_message(connection, state, frame)
            action, _ = recv_message(connection)
            env.apply(action)

            if action['done']:
                print('Fim da execução:', action['reason'], flush=True)
                return
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser(description='Cliente do CARLA 0.9.6')
    parser.add_argument('--server-host', default=SERVER_HOST)
    parser.add_argument('--server-port', type=int, default=SERVER_PORT)
    parser.add_argument('--carla-host', default='127.0.0.1')
    parser.add_argument('--carla-port', type=int, default=2000)
    parser.add_argument('--once', action='store_true', help='Encerra depois de uma execução')
    args = parser.parse_args()

    print('Aguardando o servidor de direção...', flush=True)

    while True:
        connection = connect(args.server_host, args.server_port)

        try:
            run_episode(connection, CarlaEnv(args.carla_host, args.carla_port))
        except EPISODE_ERRORS as error:
            print('Execução interrompida:', error, flush=True)
        finally:
            connection.close()

        if args.once:
            return


if __name__ == '__main__':
    main()
