import os

def limpar_imagens_pasta_test(pasta_raiz):
    # Lista de extensões de imagem comuns consideradas válidas
    extensoes_imagem = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff'}

    # os.walk percorre a pasta raiz e todas as subpastas automaticamente
    for diretorio_atual, subpastas, arquivos in os.walk(pasta_raiz):
        for arquivo in arquivos:
            # Separa o nome do arquivo e a extensão
            nome_base, extensao = os.path.splitext(arquivo)

            # 1. Verifica se é um arquivo de imagem
            if extensao.lower() in extensoes_imagem:
                # Divide pelo último '_' para extrair o número do padrão <nome>_<numero>
                partes = nome_base.rsplit('_', 1)

                # Garante que existe uma parte numérica após o underscore
                if len(partes) == 2 and partes[1].isdigit():
                    numero = int(partes[1])
                    caminho_completo = os.path.join(diretorio_atual, arquivo)

                    # 2. Se o número for maior do que 20, apaga o arquivo
                    if numero > 5:
                        try:
                            os.remove(caminho_completo)
                            print(f"[APAGADO] {caminho_completo} (Número: {numero})")
                        except Exception as e:
                            print(f"[ERRO] Não foi possível apagar {caminho_completo}: {e}")

                    # 3. Se for menor ou igual a 20, não faz nada (apenas exibe opcionalmente se quiser)
                    else:
                        print(f"[MANTIDO] {caminho_completo} (Número: {numero})")

def limpar_imagens_pasta_train(pasta_raiz):
    # Lista de extensões de imagem comuns consideradas válidas
    extensoes_imagem = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff'}

    # os.walk percorre a pasta raiz e todas as subpastas automaticamente
    for diretorio_atual, subpastas, arquivos in os.walk(pasta_raiz):
        for arquivo in arquivos:
            # Separa o nome do arquivo e a extensão
            nome_base, extensao = os.path.splitext(arquivo)

            # 1. Verifica se é um arquivo de imagem
            if extensao.lower() in extensoes_imagem:
                # Divide pelo último '_' para extrair o número do padrão <nome>_<numero>
                partes = nome_base.rsplit('_', 1)

                # Garante que existe uma parte numérica após o underscore
                if len(partes) == 2 and partes[1].isdigit():
                    numero = int(partes[1])
                    nome = partes[0]
                    caminho_completo = os.path.join(diretorio_atual, arquivo)

                    # 2. Se o número for maior do que 20, apaga o arquivo
                    numeros_aceitos = [136, 137, 138, 139, 140, 1234, 1235, 1236, 1237, 1238]
                    if numero not in numeros_aceitos:
                        try:
                            os.remove(caminho_completo)
                            print(f"[APAGADO] {caminho_completo} (Número: {numero})")
                        except Exception as e:
                            print(f"[ERRO] Não foi possível apagar {caminho_completo}: {e}")

                    # 3. Se for menor ou igual a 20, não faz nada (apenas exibe opcionalmente se quiser)
                    else:
                        print(f"[MANTIDO] {caminho_completo} (Número: {numero})")
if __name__ == "__main__":
    # Substitua pelo caminho da sua pasta raiz
    test_folder = r"/home/henrique/Documents/git/Segmentacao-Semantica-Off-Road/dataset/test"
    train_folder = r"/home/henrique/Documents/git/Segmentacao-Semantica-Off-Road/dataset/train"

    print("Iniciando varredura e limpeza...")
    limpar_imagens_pasta_test(test_folder)
    limpar_imagens_pasta_train(train_folder)
    print("Processo concluído!")