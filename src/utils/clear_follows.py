# src/utils/clear_follows.py

"""
================================================================================
SCRIPT DE LIMPEZA: DEIXAR DE SEGUIR TODOS OS ARTISTAS (UNFOLLOW ALL)
================================================================================

OBJETIVO:
    Remover todos os artistas seguidos na conta do usuário.
    Fundamental para limpar o perfil da Persona antes de iniciar um novo 
    treinamento de nicho.

PERIGO:
    Esta ação é IRREVERSÍVEL.
================================================================================
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
    
    # Diferente das músicas, o Spotify usa um cursor ('after') para paginação de seguidores
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
                
                # Pausa técnica para evitar Rate Limiting
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