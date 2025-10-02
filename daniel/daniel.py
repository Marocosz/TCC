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
    lógica de aleatoriedade total e garantia de 100 músicas no final
    através de sobre-amostragem.
    """
    # --- 1. PAINEL DE CONTROLE (CONFIGURAÇÕES) ---
    print("--- PASSO 1: Carregando configurações para o 'Daniel - Caos Controlado' ---")
    
    CSV_FILE = "daniel/artistas_lofi_dados.csv"
    PLAYLIST_NAME = "Lofi Flow (Input Daniel)"
    FINAL_PLAYLIST_SIZE = 100

    # --- Configs da Seleção de Artistas (TOTALMENTE ALEATÓRIA) ---
    ARTIST_SOURCE_POOL_SIZE = 80 
    ARTISTAS_A_SELECIONAR = 22 

    # --- Configs da Seleção de Músicas (TOTALMENTE ALEATÓRIA) ---
    MUSICAS_POR_ARTISTA_RANGE = (4, 8) # MUDANÇA: Aumentamos o intervalo para coletar mais músicas

    print(f"Lógica: Sobre-amostragem aleatória. Sortear {ARTISTAS_A_SELECIONAR} artistas para garantir {FINAL_PLAYLIST_SIZE} músicas únicas.")
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
        num_musicas_a_pegar = random.randint(MUSICAS_POR_ARTISTA_RANGE[0], MUSICAS_POR_ARTISTA_RANGE[1])
        musicas_selecionadas = get_random_sample(artist_top_tracks, num_musicas_a_pegar)
        track_names_pool.extend(musicas_selecionadas)
        print(f"  + Coletadas {len(musicas_selecionadas)} músicas aleatórias de '{artist['name']}'.")
        
    unique_tracks = list(set(track_names_pool))
    print(f"\nO universo musical contém {len(unique_tracks)} músicas ÚNICAS para o sorteio final.")
    print("-" * 40)
    
    # --- 4. MONTAGEM DA PLAYLIST FINAL (CORTE PARA 100) ---
    print(f"\n--- PASSO 4: Montando a playlist final com {FINAL_PLAYLIST_SIZE} músicas ---")

    # MUDANÇA: Lógica de sobre-amostragem, muito mais simples que o preenchimento
    if len(unique_tracks) < FINAL_PLAYLIST_SIZE:
        print(f"AVISO CRÍTICO: Mesmo com a sobre-amostragem, o total de músicas únicas ({len(unique_tracks)}) é menor que {FINAL_PLAYLIST_SIZE}. Usando todas as disponíveis.")
        final_track_names = unique_tracks
    else:
        # Sorteia 100 da nossa lista limpa e superdimensionada
        final_track_names = get_random_sample(unique_tracks, FINAL_PLAYLIST_SIZE)

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