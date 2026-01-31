# src/utils/clear_library.py

"""
================================================================================
SCRIPT DE LIMPEZA: REMOVER TODOS OS LIKES (UNLIKE ALL)
================================================================================

Objetivo do Arquivo:
    Remover todas as músicas salvas na biblioteca ("Músicas Curtidas") do usuário.
    Garante que o histórico de "Likes", que é um forte sinal para o algoritmo
    de recomendação, seja zerado antes de testar uma nova Persona.

Parte do Sistema:
    Utils / Manutenção de Conta.

Responsabilidades:
    1. Listar Biblioteca: Iterar sobre todas as músicas salvas.
    2. Remoção em Lote: Apagar músicas em blocos de 50 (limite da API).
    3. Controle de Fluxo: Paginação automática até esvaziar a biblioteca.
    4. Segurança: Solicitação de confirmação explícita do usuário.

Comunicação:
    - Externa: Spotify Web API (endpoints `me/tracks`).

Uso:
    python src/utils/clear_library.py
"""

import sys
import os
import time
from dotenv import load_dotenv # Importação necessária para ler o .env

# --- 1. CONFIGURAÇÃO DE CAMINHOS E AMBIENTE ---
# Pega o caminho da pasta atual (src/utils)
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
# Pega o caminho da pasta src
diretorio_src = os.path.dirname(diretorio_atual)
# Pega o caminho da raiz do projeto (TCC)
diretorio_raiz = os.path.dirname(diretorio_src)

# Adiciona a raiz ao path do Python (caso precise importar módulos locais)
sys.path.append(diretorio_raiz)

# CARREGA O ARQUIVO .ENV DA RAIZ
# Isso define SPOTIPY_CLIENT_ID e SECRET na memória para o Spotipy achar
dotenv_path = os.path.join(diretorio_raiz, '.env')
load_dotenv(dotenv_path)

import spotipy
from spotipy.oauth2 import SpotifyOAuth

def remove_all_likes():
    """
    Função principal que orquestra a limpeza da biblioteca.

    O que faz:
        1. Autentica o usuário.
        2. Solicita confirmação ('SIM').
        3. Entra num loop 'while' infinito que esvazia a biblioteca em lotes.

    Por que existe:
        Resetar o estado da conta para garantir a pureza dos testes entre Personas.

    Quando é chamada:
        Manualmente antes de iniciar uma nova fase de coleta.

    Lógica de Execução:
        Não usamos paginação tradicional (next) porque estamos removendo itens,
        então a "próxima página" sempre será a página 0 da nova lista reduzida.
    """
    # Escopo necessário para LER e REMOVER da biblioteca
    scope = "user-library-read user-library-modify"
    
    # Verifica se as credenciais foram carregadas corretamente
    if not os.getenv("SPOTIPY_CLIENT_ID"):
        print("ERRO CRÍTICO: Não foi possível ler o SPOTIPY_CLIENT_ID do arquivo .env")
        print(f"Caminho tentado: {dotenv_path}")
        return

    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    except Exception as e:
        print(f"Erro na autenticação: {e}")
        return
    
    # --- CONFIRMAÇÃO DE SEGURANÇA ---
    print("!!!" * 20)
    print("ATENÇÃO: ESTE SCRIPT VAI REMOVER TODAS AS MÚSICAS CURTIDAS DA SUA CONTA.")
    print("!!!" * 20)
    
    confirm = input("Tem certeza absoluta que deseja continuar? Digite 'SIM': ")
    if confirm != 'SIM':
        print("Operação cancelada.")
        return

    print("\nIniciando limpeza...")
    total_removido = 0
    batch_size = 50 # Limite máximo da API por chamada

    # --- LOOP DE REMOÇÃO CONTÍNUA ---
    while True:
        try:
            # Busca as primeiras 50 músicas salvas
            # Como estamos deletando, o offset é sempre 0 (início da fila)
            results = sp.current_user_saved_tracks(limit=batch_size)
            items = results['items']

            if not items:
                print("Sua biblioteca de curtidas está vazia.")
                break

            # Extrai os IDs das músicas
            track_ids = []
            for item in items:
                if item.get('track') and item['track'].get('id'):
                    track_ids.append(item['track']['id'])
            
            # Remove o lote atual
            if track_ids:
                sp.current_user_saved_tracks_delete(tracks=track_ids)
                total_removido += len(track_ids)
                print(f" - Removidas {len(track_ids)} músicas (Total removido nesta sessão: {total_removido})")
                
                # Pequena pausa para não estourar o rate limit (Boas práticas de API)
                time.sleep(0.5)
            else:
                break
        except Exception as e:
            print(f"Erro durante o processo de remoção: {e}")
            break

    print("-" * 40)
    print(f"LIMPEZA CONCLUÍDA! Total de músicas removidas: {total_removido}")

if __name__ == "__main__":
    remove_all_likes()