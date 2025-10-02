# construir_playlist_daniel.py

import random
from functions import (
    load_artists_from_csv,
    extract_top_tracks_from_data,
    get_random_sample,
    fetch_track_uris,
    create_playlist,
    add_tracks_to_playlist,
    like_tracks_slowly
)

def main():
    """
    Função principal para criar a playlist da persona Daniel, com uma
    lógica de aleatoriedade total para servir como "grupo de controle".
    """
    # --- 1. PAINEL DE CONTROLE (CONFIGURAÇÕES) ---
    print("--- PASSO 1: Carregando configurações para o 'Daniel - Caos Controlado' ---")
    
    CSV_FILE = "daniel/artistas_lofi_dados.csv"
    PLAYLIST_NAME = "Lofi Flow (Input Daniel)"
    FINAL_PLAYLIST_SIZE = 100

    # --- Configs da Seleção de Artistas (TOTALMENTE ALEATÓRIA) ---
    # Define o universo de artistas de onde vamos sortear
    ARTIST_SOURCE_POOL_SIZE = 80 
    # Define quantos artistas vamos sortear desse universo
    ARTISTAS_A_SELECIONAR = 20

    # --- Configs da Seleção de Músicas (TOTALMENTE ALEATÓRIA) ---
    # Para cada artista, vamos sortear uma quantidade de músicas neste intervalo
    MUSICAS_POR_ARTISTA_RANGE = (3, 7)

    print(f"Lógica: Aleatoriedade total. Sortear {ARTISTAS_A_SELECIONAR} artistas de um universo de {ARTIST_SOURCE_POOL_SIZE}.")
    print("-" * 40)

    # --- 2. SELEÇÃO ALEATÓRIA DE ARTISTAS ---
    print("\n--- PASSO 2: Sorteando artistas aleatoriamente ---")
    
    all_artists_pool = load_artists_from_csv(CSV_FILE, limit=ARTIST_SOURCE_POOL_SIZE)
    if len(all_artists_pool) < ARTISTAS_A_SELECIONAR:
        print("AVISO: O pool de artistas é menor que o número desejado. Usando todos os artistas disponíveis.")
        ARTISTAS_A_SELECIONAR = len(all_artists_pool)
        
    selected_artists = get_random_sample(all_artists_pool, ARTISTAS_A_SELECIONAR)
    
    print(f"{len(selected_artists)} artistas foram sorteados aleatoriamente para a curadoria.")
    print("-" * 40)

    # --- 3. CRIAÇÃO DO "UNIVERSO MUSICAL" COM COLETA ALEATÓRIA ---
    print(f"\n--- PASSO 3: Criando 'pote' de músicas com coleta duplamente aleatória ---")
    
    track_names_pool = []
    
    for artist in selected_artists:
        artist_top_tracks = extract_top_tracks_from_data(artist)
        
        # Sorteia QUANTAS músicas pegar deste artista
        num_musicas_a_pegar = random.randint(MUSICAS_POR_ARTISTA_RANGE[0], MUSICAS_POR_ARTISTA_RANGE[1])
        
        # Sorteia QUAIS músicas pegar de todo o top 10 dele
        musicas_selecionadas = get_random_sample(artist_top_tracks, num_musicas_a_pegar)
        
        track_names_pool.extend(musicas_selecionadas)
        print(f"  + Coletadas {len(musicas_selecionadas)} músicas aleatórias de '{artist['name']}'.")
        
    unique_tracks = list(set(track_names_pool))
    print(f"\nO universo musical contém {len(unique_tracks)} músicas ÚNICAS para o sorteio final.")
    print("-" * 40)
    
    # --- 4. MONTAGEM DA PLAYLIST FINAL COM 100 MÚSICAS ---
    print(f"\n--- PASSO 4: Montando a playlist final com {FINAL_PLAYLIST_SIZE} músicas ---")

    if len(unique_tracks) < FINAL_PLAYLIST_SIZE:
        playlist_size = len(unique_tracks)
        print(f"AVISO CRÍTICO: O universo de músicas ({playlist_size}) é menor que o desejado. A playlist será criada com o máximo disponível.")
    else:
        playlist_size = FINAL_PLAYLIST_SIZE

    final_track_names = get_random_sample(unique_tracks, playlist_size)
    print(f"Sorteadas {len(final_track_names)} músicas para a playlist final.")

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