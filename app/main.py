"""Abre a interface do TCC no navegador. O menu do terminal foi substituído por ela.

Uso: python -m app.main [--porta 8000] [--sem-navegador]
O CARLA continua sendo controlado à parte (README, seção "Controlar o CARLA")."""
import argparse
import threading
import webbrowser


def main():
    parser = argparse.ArgumentParser(description='Interface da segmentação semântica off-road.')
    parser.add_argument('--porta', type=int, default=8000, help='porta do servidor local (padrão: 8000)')
    parser.add_argument('--sem-navegador', action='store_true', help='não abrir o navegador automaticamente')
    args = parser.parse_args()

    # Imports aqui para o --help responder sem carregar o PyTorch
    import uvicorn
    from configs import paths
    from app.web.erros import redirect_output
    from app.web.server import create_app

    url = f'http://127.0.0.1:{args.porta}/'
    # Única mensagem no terminal; daqui em diante tudo (logs, print do treino, erros) vai para o arquivo
    print(f'\nInterface disponível em {url} (Ctrl+C para encerrar)')
    print(f'Logs do sistema em {paths.relative(paths.SYSTEM_LOG_FILE)}\n', flush=True)
    redirect_output()

    app = create_app()

    if not args.sem_navegador:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    # Só na própria máquina: a interface não tem login e não deve ficar exposta na rede
    uvicorn.run(app, host='127.0.0.1', port=args.porta, log_level='warning')


if __name__ == '__main__':
    main()
