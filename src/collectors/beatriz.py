import spotipy
from spotipy.oauth2 import SpotifyOAuth
from src.functions import (
    load_artists_from_csv,
    get_random_sample,
    fetch_track_uris,
    create_playlist,
    add_tracks_to_playlist,
    like_tracks_slowly 
)

def main():
    """
    Função principal que orquestra a criação da playlist da Beatriz,
    com uma lógica de "ranking absoluto" focado na popularidade
    individual de cada música.
    """
    # --- 1. CONFIGURAÇÕES ---
    print("--- PASSO 1: Carregando configurações para a 'Beatriz Mainstream' ---")
    
    CSV_FILE = "beatriz/artistas_topbrasil_dados.csv"
    PLAYLIST_NAME = "Top Hits Brasil (Input Beatriz)"
    FINAL_PLAYLIST_SIZE = 100
    ARTIST_SOURCE_LIMIT = 100
    
    print(f"Lógica: Criar um ranking de músicas por popularidade da FAIXA e selecionar o Top {FINAL_PLAYLIST_SIZE}.")
    print("-" * 40)

    # --- 2. CRIAÇÃO DO "UNIVERSO MUSICAL" ---
    print("\n--- PASSO 2: Coletando todas as top músicas de todos os artistas do CSV ---")
    
    all_artists = load_artists_from_csv(CSV_FILE, limit=ARTIST_SOURCE_LIMIT)
    if not all_artists:
        print(f"ERRO: Não foi possível carregar artistas do arquivo '{CSV_FILE}'.")
        return

    # Autenticação para buscar detalhes das faixas
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth())
    
    # Lista que vai guardar os OBJETOS completos de cada música
    all_tracks_pool = []
    
    for artist in all_artists:
        try:
            # Extrai o ID do artista a partir da URI
            artist_id = artist['uri'].split(':')[-1]
            # Busca os objetos completos das top 10 músicas do artista
            top_tracks_objects = sp.artist_top_tracks(artist_id, country="BR")['tracks']
            all_tracks_pool.extend(top_tracks_objects)
            print(f"  + Coletadas {len(top_tracks_objects)} músicas de '{artist['name']}'")
        except Exception as e:
            print(f"  AVISO: Não foi possível buscar músicas de '{artist['name']}'. Erro: {e}")
            
    print(f"\nColetadas {len(all_tracks_pool)} músicas no total para o ranking.")
    
    # --- 3. RANKING POR POPULARIDADE DA MÚSICA ---
    print("\n--- PASSO 3: Ordenando todas as músicas por sua popularidade individual ---")

    # Ordena a lista de músicas com base na chave 'popularity' de cada música
    all_tracks_pool.sort(key=lambda track: track['popularity'], reverse=True)
    
    print("Ranking de músicas criado com sucesso.")
    print("-" * 40)

    # --- 4. SELEÇÃO DO TOP 100 SEM DUPLICATAS ---
    print(f"\n--- PASSO 4: Selecionando as {FINAL_PLAYLIST_SIZE} músicas mais populares do ranking ---")
    
    final_track_names = []
    seen_tracks = set()
    
    for track in all_tracks_pool:
        track_name = track['name']
        if track_name not in seen_tracks:
            final_track_names.append(track_name)
            seen_tracks.add(track_name)
        
        if len(final_track_names) >= FINAL_PLAYLIST_SIZE:
            break
            
    print(f"Selecionadas {len(final_track_names)} músicas únicas para a playlist.")
    print("-" * 40)
    
    # --- 5. MONTAGEM DA PLAYLIST FINAL ---
    print(f"\n--- PASSO 5: Montando a playlist final ---")

    # A lista 'final_track_names' já está na ordem de popularidade
    track_uris = fetch_track_uris(final_track_names)
    if not track_uris: return

    playlist_id = create_playlist(PLAYLIST_NAME)
    if playlist_id:
        add_tracks_to_playlist(playlist_id, track_uris)
        
        print("\n--- PASSO 6: Curtindo as músicas (uma por uma) ---")
        like_tracks_slowly(track_uris)
    
    print("\n--- PROCESSO FINALIZADO! ---")
    print(f"Playlist '{PLAYLIST_NAME}' criada com sucesso.")

if __name__ == "__main__":
    main()