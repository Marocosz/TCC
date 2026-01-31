# src/utils/clear_follows.py

"""
================================================================================
SCRIPT DE LIMPEZA: DEIXAR DE SEGUIR TODOS OS ARTISTAS (UNFOLLOW ALL)
================================================================================

Objetivo do Arquivo:
    Resetar o gráfico social da conta do usuário, removendo todos os artistas
    seguidos. Isso prepara o "terreno" para que uma nova Persona possa ser
    instalada sem interferência de gostos anteriores.

Parte do Sistema:
    Utils / Manutenção de Conta.

Responsabilidades:
    1. Listar Seguidores: Iterar sobre todos os artistas seguidos pela conta.
    2. Remoção em Lote: Enviar comandos de 'unfollow' em blocos de 50.
    3. Segurança: Exigir confirmação manual antes de executar a ação destrutiva.

Comunicação:
    - Externa: Spotify Web API (endpoints `me/following`).

Uso:
    python src/utils/clear_follows.py
"""

import sys
import os
import time
from dotenv import load_dotenv

# --- 1. CONFIGURAÇÃO DE CAMINHOS E AMBIENTE ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
diretorio_src = os.path.dirname(diretorio_atual)
diretorio_raiz = os.path.dirname(diretorio_src)

sys.path.append(diretorio_raiz)

dotenv_path = os.path.join(diretorio_raiz, '.env')
load_dotenv(dotenv_path)

import spotipy
from spotipy.oauth2 import SpotifyOAuth

def remove_all_follows():
    """
    Remove TODOS os artistas que o usuário segue.

    O que faz:
        Busca paginada de todos os artistas seguidos e envia comandos de unfollow.

    Por que existe:
        Para evitar que o Spotify misture recomendações de Personas diferentes.
        Se a conta segue "Metallica" (Ricardo) e "Anitta" (Beatriz), o algoritmo
        de recomendação (Discover Weekly/Release Radar) ficará confuso.
        A limpeza garante isolamento do experimento.

    Quando é chamada:
        Manualmente pelo pesquisador antes de iniciar uma nova fase de coleta.

    Ação:
        - Busca paginada (cursor-based) de artistas seguidos.
        - Deleta em lotes de 50.
    """
    # Escopo necessário para LER e MODIFICAR seguidores
    scope = "user-follow-read user-follow-modify"
    
    if not os.getenv("SPOTIPY_CLIENT_ID"):
        print("ERRO CRÍTICO: Não foi possível ler o SPOTIPY_CLIENT_ID do arquivo .env")
        return

    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
        user = sp.current_user()
    except Exception as e:
        print(f"Erro na autenticação: {e}")
        return
    
    # --- BLOCO DE SEGURANÇA ---
    # Impede execução acidental em conta pessoal principal se não for a intenção.
    print("!!!" * 20)
    print(f"CONTA: {user['display_name']}")
    print("ATENÇÃO: ESTE SCRIPT VAI DEIXAR DE SEGUIR TODOS OS ARTISTAS DESTA CONTA.")
    print("!!!" * 20)
    
    confirm = input("Tem certeza absoluta que deseja continuar? Digite 'SIM': ")
    if confirm != 'SIM':
        print("Operação cancelada.")
        return

    print("\nIniciando processo de Unfollow...")
    total_removido = 0
    
    # --- LOOP DE REMOÇÃO (Paginação por Cursor) ---
    # Diferente de playlists, a API de seguidores usa um cursor 'after' (ID do último artista).
    # Porém, como estamos DELETANDO a lista enquanto iteramos, podemos simplesmente
    # pedir sempre os 'primeiros 50' repetidamente até que a lista volte vazia.
    while True:
        try:
            # Busca os artistas seguidos (máximo de 50 por vez)
            results = sp.current_user_followed_artists(limit=50)
            artists = results['artists']['items']

            if not artists:
                print("Você não está seguindo nenhum artista.")
                break

            # Extrai os IDs dos artistas
            artist_ids = [artist['id'] for artist in artists]
            
            # Deixa de seguir o lote atual
            if artist_ids:
                sp.user_unfollow_artists(ids=artist_ids)
                total_removido += len(artist_ids)
                print(f" - Deixou de seguir {len(artist_ids)} artistas (Total: {total_removido})")
                
                # Pausa técnica para evitar Rate Limiting (Erro 429)
                time.sleep(0.5)
            
            # Se o resultado for menor que 50, significa que era a última página
            if len(artists) < 50:
                break
                
        except Exception as e:
            print(f"Erro durante o processo de remoção: {e}")
            break

    print("-" * 40)
    print(f"LIMPEZA CONCLUÍDA! Total de artistas removidos: {total_removido}")

if __name__ == "__main__":
    remove_all_follows()