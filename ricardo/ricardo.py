# construir_playlist_ricardo.py

import random
import math
from functions import (
    load_artists_from_csv,
    extract_top_tracks_from_data,
    get_random_sample,
    fetch_track_uris,
    create_playlist,
    add_tracks_to_playlist,
    like_tracks_slowly
)

def distribuir_musicas_entre_artistas(total_musicas: int, num_artistas: int) -> list:
    """
    Função auxiliar que distribui um número total de músicas de forma
    aleatória entre um número de artistas.
    Ex: distribuir_musicas_entre_artistas(40, 6) -> [7, 5, 8, 6, 9, 5] (soma = 40)
    """
    distribuicao = [0] * num_artistas
    for _ in range(total_musicas):
        indice_artista = random.randint(0, num_artistas - 1)
        distribuicao[indice_artista] += 1
    return distribuicao

def main():
    """
    Função principal para criar a playlist da persona Ricardo com uma
    lógica híbrida: proporcional por tier de artista e aleatória por artista.
    """
    # --- 1. PAINEL DE CONTROLE (CONFIGURAÇÕES) ---
    print("--- PASSO 1: Carregando configurações para o 'Ricardo Nostálgico' ---")
    
    CSV_FILE = "ricardo/artistas_classicos_dados.csv"
    PLAYLIST_NAME = "Rock & MPB 90s (Input Ricardo)"
    FINAL_PLAYLIST_SIZE = 100

    # --- Configs de Seleção de Artistas ---
    FATIAS_ARTISTAS_CSV = {
        'famosos': (0, 15),
        'medianos': (15, 50),
        'lado_b': (50, 100)
    }
    QTD_ARTISTAS_POR_TIER = {
        'famosos': 6,
        'medianos': 4,
        'lado_b': 3
    } # Total: 13 artistas

    # --- Configs da Composição da Playlist Final ---
    PROPORCAO_FINAL_PLAYLIST = {
        'famosos': 0.40,  # 40 músicas virão dos artistas 'famosos'
        'medianos': 0.35, # 35 músicas virão dos 'medianos'
        'lado_b': 0.25    # 25 músicas virão do 'lado_b'
    }

    # --- Configs da Seleção de Músicas por Artista ---
    PROPORCAO_MUSICAS_POR_ARTISTA = {'famosas': 0.6, 'medianas': 0.4}
    FATIAS_TOP_TRACKS = {'famosas': (0, 4), 'medianas': (4, 10)}

    print(f"Lógica: Montar playlist de {FINAL_PLAYLIST_SIZE} faixas a partir de {sum(QTD_ARTISTAS_POR_TIER.values())} artistas selecionados.")
    print("-" * 40)

    # --- 2. SELEÇÃO ESTRATIFICADA DE ARTISTAS ---
    print("\n--- PASSO 2: Sorteando um grupo seleto de artistas ---")
    
    all_artists = load_artists_from_csv(CSV_FILE, limit=120)
    selected_artists_por_tier = {'famosos': [], 'medianos': [], 'lado_b': []}

    for tier, (start, end) in FATIAS_ARTISTAS_CSV.items():
        artist_pool_tier = all_artists[start:end]
        num_to_sample = QTD_ARTISTAS_POR_TIER[tier]
        sampled = get_random_sample(artist_pool_tier, min(num_to_sample, len(artist_pool_tier)))
        selected_artists_por_tier[tier] = sampled
        print(f"Sorteados {len(sampled)} artistas do nível '{tier}'.")

    print("-" * 40)

    # --- 3. COLETA DE MÚSICAS COM LÓGICA HÍBRIDA ---
    print(f"\n--- PASSO 3: Coletando {FINAL_PLAYLIST_SIZE} músicas com a lógica híbrida ---")
    
    track_names_pool = []
    
    for tier, artists_do_tier in selected_artists_por_tier.items():
        if not artists_do_tier:
            continue

        total_musicas_do_tier = int(FINAL_PLAYLIST_SIZE * PROPORCAO_FINAL_PLAYLIST[tier])
        distribuicao_por_artista = distribuir_musicas_entre_artistas(total_musicas_do_tier, len(artists_do_tier))
        
        print(f"\nDo nível '{tier}', coletando um total de {total_musicas_do_tier} músicas de {len(artists_do_tier)} artistas.")

        for artist, total_a_pegar in zip(artists_do_tier, distribuicao_por_artista):
            artist_top_tracks = extract_top_tracks_from_data(artist)
            
            if len(artist_top_tracks) < 10:
                print(f"  AVISO: '{artist['name']}' não tem 10 top tracks. Pulando.")
                continue

            # Aplica a proporção 60% famosas / 40% medianas
            qtd_famosas = math.ceil(total_a_pegar * PROPORCAO_MUSICAS_POR_ARTISTA['famosas'])
            qtd_medianas = total_a_pegar - qtd_famosas

            pool_famosas = artist_top_tracks[FATIAS_TOP_TRACKS['famosas'][0]:FATIAS_TOP_TRACKS['famosas'][1]]
            pool_medianas = artist_top_tracks[FATIAS_TOP_TRACKS['medianas'][0]:FATIAS_TOP_TRACKS['medianas'][1]]

            track_names_pool.extend(get_random_sample(pool_famosas, qtd_famosas))
            track_names_pool.extend(get_random_sample(pool_medianas, qtd_medianas))
            
            print(f"  De '{artist['name']}': coletadas {total_a_pegar} músicas ({qtd_famosas} famosas, {qtd_medianas} medianas).")

    # --- 4. MONTAGEM DA PLAYLIST FINAL ---
    print("\n" + "-" * 40)
    print(f"\n--- PASSO 4: Montando a playlist final ---")

    unique_tracks = list(set(track_names_pool))
    print(f"Total de {len(unique_tracks)} músicas únicas selecionadas para a playlist.")

    # Ajuste final para garantir exatamente 100 musicas, caso a remoção de duplicatas altere o total
    if len(unique_tracks) > FINAL_PLAYLIST_SIZE:
        final_track_names = get_random_sample(unique_tracks, FINAL_PLAYLIST_SIZE)
    else:
        final_track_names = unique_tracks
    
    print(f"Tamanho final da playlist: {len(final_track_names)} músicas.")

    track_uris = fetch_track_uris(final_track_names)
    if not track_uris: return

    playlist_id = create_playlist(PLAYLIST_NAME)
    if playlist_id:
        add_tracks_to_playlist(playlist_id, track_uris)
        
        print("\n--- PASSO 5: Curtindo as músicas (uma por uma) ---")
        like_tracks_slowly(track_uris)
    
    print("\n--- PROCESSO FINALIZADO! ---")

if __name__ == "__main__":
    main()