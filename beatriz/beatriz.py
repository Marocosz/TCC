# construir_playlist_beatriz.py

from functions import (
    load_artists_from_csv,
    extract_top_tracks_from_data,
    fetch_track_uris,
    create_playlist,
    add_tracks_to_playlist,
    like_tracks_slowly 
)

def main():
    """
    Função principal que orquestra a criação da playlist da Beatriz,
    com uma lógica de "ranking absoluto" para criar a playlist definitiva
    do mainstream.
    """
    # --- 1. CONFIGURAÇÕES ---
    print("--- PASSO 1: Carregando configurações para a 'Beatriz Mainstream' ---")
    
    CSV_FILE = "beatriz/artistas_topbrasil_dados.csv"
    PLAYLIST_NAME = "Top Hits Brasil (Input Beatriz)"
    FINAL_PLAYLIST_SIZE = 100

    # Carrega todos os artistas do CSV para garantir uma base de dados completa
    ARTIST_SOURCE_LIMIT = 100
    
    print(f"Lógica: Criar um ranking de todas as músicas por popularidade do artista e selecionar o Top {FINAL_PLAYLIST_SIZE}.")
    print("-" * 40)

    # --- 2. CRIAÇÃO DO RANKING GERAL DE MÚSICAS ---
    print("\n--- PASSO 2: Criando ranking geral de músicas por popularidade do artista ---")
    
    all_artists = load_artists_from_csv(CSV_FILE, limit=ARTIST_SOURCE_LIMIT)
    if not all_artists:
        print(f"ERRO: Não foi possível carregar artistas do arquivo '{CSV_FILE}'.")
        return

    # Lista que vai guardar cada música junto com a popularidade do seu artista
    ranked_music_list = []
    
    for artist in all_artists:
        # Pega a popularidade do artista (convertendo para inteiro)
        artist_popularity = int(artist.get('popularity', 0))
        # Pega as top músicas do artista
        top_tracks = extract_top_tracks_from_data(artist)
        
        # Adiciona cada música à lista de ranking
        for track_name in top_tracks:
            ranked_music_list.append({
                'name': track_name,
                'artist_popularity': artist_popularity
            })
            
    print(f"Coletadas {len(ranked_music_list)} músicas no total para o ranking.")
    
    # Ordena a lista de músicas com base na popularidade do artista (do maior para o menor)
    ranked_music_list.sort(key=lambda x: x['artist_popularity'], reverse=True)
    
    print("Ranking de músicas criado com sucesso.")
    print("-" * 40)

    # --- 3. SELEÇÃO DO TOP 100 SEM DUPLICATAS ---
    print(f"\n--- PASSO 3: Selecionando as {FINAL_PLAYLIST_SIZE} músicas mais populares do ranking ---")
    
    final_track_names = []
    seen_tracks = set() # Usamos um set para controlar as músicas já adicionadas
    
    for music_data in ranked_music_list:
        track_name = music_data['name']
        if track_name not in seen_tracks:
            final_track_names.append(track_name)
            seen_tracks.add(track_name)
        
        # Para quando atingirmos o tamanho desejado
        if len(final_track_names) >= FINAL_PLAYLIST_SIZE:
            break
            
    print(f"Selecionadas {len(final_track_names)} músicas únicas para a playlist.")
    print("-" * 40)
    
    # --- 4. MONTAGEM DA PLAYLIST FINAL ---
    print(f"\n--- PASSO 4: Montando a playlist final ---")

    # A lista 'final_track_names' já está na ordem de popularidade, não precisamos embaralhar.
    track_uris = fetch_track_uris(final_track_names)
    if not track_uris: return

    playlist_id = create_playlist(PLAYLIST_NAME)
    if playlist_id:
        add_tracks_to_playlist(playlist_id, track_uris)
        
        print("\n--- PASSO 5: Curtindo as músicas (uma por uma) ---")
        like_tracks_slowly(track_uris)
    
    print("\n--- PROCESSO FINALIZADO! ---")
    print(f"Playlist '{PLAYLIST_NAME}' criada com sucesso.")

if __name__ == "__main__":
    main()