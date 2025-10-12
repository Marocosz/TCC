# sofia/sofia.py

import random
import math
import sys
import os

# --- Bloco de código para encontrar o arquivo functions.py na pasta pai ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
diretorio_pai = os.path.dirname(diretorio_atual)
sys.path.append(diretorio_pai)

from functions import *
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# --- FUNÇÕES AUXILIARES AUTÔNOMAS PARA GARANTIR A PUREZA ---

def get_primary_artists_from_playlist_pure(sp_client, playlist_id: str) -> dict:
    print("Buscando APENAS os artistas principais da playlist semente...")
    unique_artists = {}
    results = sp_client.playlist_items(playlist_id)
    playlist_items = results['items']
    while results['next']:
        results = sp_client.next(results)
        playlist_items.extend(results['items'])
    for item in playlist_items:
        if item.get("track") and item['track'] and item['track'].get('artists'):
            primary_artist = item["track"]["artists"][0]
            if primary_artist['id'] not in unique_artists:
                unique_artists[primary_artist['id']] = primary_artist
    return unique_artists

def get_artist_album_tracks_pure(sp_client, artist_id: str, limit_albums=5) -> list:
    all_track_ids = set()
    try:
        results = sp_client.artist_albums(artist_id, album_type='album,single', limit=limit_albums)
        for album in results['items']:
            track_results = sp_client.album_tracks(album['id'])
            for track in track_results['items']:
                if track and track.get('id'):
                    all_track_ids.add(track['id'])
    except Exception:
        return []
    
    full_track_objects = []
    if all_track_ids:
        for i in range(0, len(list(all_track_ids)), 50):
            batch_ids = list(all_track_ids)[i:i+50]
            try:
                tracks_info = sp_client.tracks(batch_ids)
                full_track_objects.extend([t for t in tracks_info['tracks'] if t])
            except Exception:
                continue
    return full_track_objects

def main():
    # --- 1. PAINEL DE CONTROLE ---
    print("--- PASSO 1: Carregando configurações da 'Curadoria Pura' ---")
    
    PLAYLIST_URL_SEMENTE = "https://open.spotify.com/playlist/5m7jvWtwE8OJ9DgzU6jhUu?si=c5ac24ba302f4e49"
    NOVO_PLAYLIST_NAME = "Alternativa Pura (Input Sofia)"
    FINAL_PLAYLIST_SIZE = 100

    # --- 2. COLETAR E CLASSIFICAR OS ARTISTAS (APENAS PRIMÁRIOS) ---
    print("\n--- PASSO 2: Coletando e classificando os artistas da playlist base ---")
    
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-read-private"))
    
    try:
        # Pega os artistas simplificados (só nome e ID)
        artistas_simplificados_map = get_primary_artists_from_playlist_pure(sp, PLAYLIST_URL_SEMENTE.split('/')[-1].split('?')[0])
        
        # MUDANÇA: Agora "enriquecemos" os dados para obter a popularidade
        print("Buscando perfis completos para obter a popularidade de cada artista...")
        todos_os_artistas_com_pop = get_full_artist_profiles(artistas_simplificados_map)
        
        # Agora podemos ordenar com segurança
        todos_os_artistas_com_pop.sort(key=lambda x: int(x['popularity']), reverse=True)
        
        ponto_de_corte = len(todos_os_artistas_com_pop) // 2
        artistas_populares = todos_os_artistas_com_pop[:ponto_de_corte]
        artistas_nicho = todos_os_artistas_com_pop[ponto_de_corte:]

        print(f"Encontrados {len(todos_os_artistas_com_pop)} artistas principais. Divisão 50/50.")
        print("-" * 40)

    except Exception as e:
        print(f"ERRO: Não foi possível processar a playlist base. Erro: {e}")
        return

    # --- 3. COLETAR UM UNIVERSO DE URIs (NÃO NOMES) ---
    print("\n--- PASSO 3: Coletando um universo de URIs com lógica condicional ---")
    
    track_uris_pool = []
    
    print("\nProcessando artistas da 'metade superior' (pegando Lado B)...")
    for artist in artistas_populares:
        todas_as_faixas_obj = get_artist_album_tracks_pure(sp, artist['uri'].split(':')[-1])
        todas_as_faixas_obj.sort(key=lambda x: x.get('popularity', 0), reverse=True)
        
        faixas_lado_b = todas_as_faixas_obj[5:]
        track_uris_pool.extend([track['uri'] for track in faixas_lado_b])
        print(f"  + {len(faixas_lado_b)} URIs 'lado B' de '{artist['name']}' adicionadas ao pote.")

    print("\nProcessando artistas da 'metade inferior' (pegando aleatório)...")
    for artist in artistas_nicho:
        todas_as_faixas_obj = get_artist_album_tracks_pure(sp, artist['uri'].split(':')[-1])
        track_uris_pool.extend([track['uri'] for track in todas_as_faixas_obj])
        print(f"  + {len(todas_as_faixas_obj)} URIs de '{artist['name']}' adicionadas ao pote.")

    # --- 4. MONTAGEM FINAL COM 100 MÚSICAS GARANTIDAS ---
    print("\n" + "-" * 40)
    print(f"\n--- PASSO 4: Montando a playlist final ---")

    unique_uris = list(set(track_uris_pool))
    print(f"Total de {len(unique_uris)} URIs únicas coletadas.")

    if len(unique_uris) < FINAL_PLAYLIST_SIZE:
        final_track_uris = unique_uris
    else:
        final_track_uris = get_random_sample(unique_uris, FINAL_PLAYLIST_SIZE)
    
    print(f"Tamanho final da playlist: {len(final_track_uris)} músicas.")

    # A função fetch_track_uris não é mais necessária, pois já temos as URIs
    # track_uris = fetch_track_uris(final_track_names)

    playlist_id = create_playlist(NOVO_PLAYLIST_NAME)
    if playlist_id:
        add_tracks_to_playlist(playlist_id, final_track_uris)
        print("\n--- PASSO 5: Curtindo as músicas (uma por uma) ---")
        like_tracks_slowly(final_track_uris)
    
    print("\n--- PROCESSO FINALIZADO! ---")

if __name__ == "__main__":
    main()