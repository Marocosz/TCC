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

def main():
    """
    Função principal para criar a playlist da persona Sofia com uma
    lógica de sobre-amostragem para garantir 100 músicas no final.
    """
    # --- 1. PAINEL DE CONTROLE DA CURADORIA ---
    print("--- PASSO 1: Carregando configurações para a 'Sofia Curadora' ---")
    
    CSV_FILE = "sofia/artistas_indie_dados.csv"
    PLAYLIST_NAME = "Poetic Melancholy (Input Sofia)"
    FINAL_PLAYLIST_SIZE = 100
    
    # MUDANÇA: Definimos um alvo inicial maior para compensar as duplicatas
    TARGET_INICIAL_DE_COLETA = 110

    # --- Configuração da Seleção de Artistas (PROPORCIONAL) ---
    TOTAL_ARTISTAS_SELECIONADOS = 20
    PROPORCAO_ARTISTAS = {'famosos': 0.2, 'medianos': 0.3, 'nicho': 0.5}
    FATIAS_ARTISTAS_CSV = {'famosos': (0, 10), 'medianos': (10, 40), 'nicho': (40, 100)}

    # --- Configuração da Seleção de Músicas (ALEATÓRIA E PROPORCIONAL) ---
    # MUDANÇA: Aumentamos o teto do intervalo para ajudar a coletar mais músicas
    MUSICAS_POR_ARTISTA_RANGE = (5, 9)
    PROPORCAO_MUSICAS = {'famosas': 0.20, 'medianas': 0.30}
    FATIAS_TOP_TRACKS = {'famosas': (0, 3), 'medianas': (3, 7), 'lado_b': (7, 10)}
    
    print(f"Lógica: Sobre-amostragem. Coletar ~{TARGET_INICIAL_DE_COLETA} faixas para garantir {FINAL_PLAYLIST_SIZE} no final.")
    print("-" * 40)

    # --- 2. SELEÇÃO PROPORCIONAL DE ARTISTAS ---
    print("\n--- PASSO 2: Sorteando artistas proporcionalmente por popularidade ---")
    
    all_artists = load_artists_from_csv(CSV_FILE, limit=120)
    selected_artists = []

    for tier, proportion in PROPORCAO_ARTISTAS.items():
        qtd_a_selecionar = int(TOTAL_ARTISTAS_SELECIONADOS * proportion)
        start, end = FATIAS_ARTISTAS_CSV[tier]
        artist_pool_tier = all_artists[start:end]
        sampled_artists = get_random_sample(artist_pool_tier, min(qtd_a_selecionar, len(artist_pool_tier)))
        selected_artists.extend(sampled_artists)
        print(f"Sorteados {len(sampled_artists)} artistas do nível '{tier}'.")

    print(f"\nTotal de {len(selected_artists)} artistas selecionados para a curadoria.")
    print("-" * 40)

    # --- 3. CRIAÇÃO DO "UNIVERSO MUSICAL" COM COLETA PROPORCIONAL ---
    print(f"\n--- PASSO 3: Criando 'pote' de músicas com coleta proporcional ---")
    
    track_names_pool = []
    
    for artist in selected_artists:
        artist_top_tracks = extract_top_tracks_from_data(artist)
        if len(artist_top_tracks) < 10:
            print(f"  AVISO: '{artist['name']}' não tem 10 top tracks. Pulando.")
            continue
        
        total_musicas_a_pegar = random.randint(MUSICAS_POR_ARTISTA_RANGE[0], MUSICAS_POR_ARTISTA_RANGE[1])
        
        qtd_famosas = math.ceil(total_musicas_a_pegar * PROPORCAO_MUSICAS['famosas'])
        qtd_medianas = math.floor(total_musicas_a_pegar * PROPORCAO_MUSICAS['medianas'])
        qtd_lado_b = total_musicas_a_pegar - qtd_famosas - qtd_medianas

        pool_famosas = artist_top_tracks[FATIAS_TOP_TRACKS['famosas'][0] : FATIAS_TOP_TRACKS['famosas'][1]]
        pool_medianas = artist_top_tracks[FATIAS_TOP_TRACKS['medianas'][0] : FATIAS_TOP_TRACKS['medianas'][1]]
        pool_lado_b = artist_top_tracks[FATIAS_TOP_TRACKS['lado_b'][0] : FATIAS_TOP_TRACKS['lado_b'][1]]

        track_names_pool.extend(get_random_sample(pool_famosas, qtd_famosas))
        track_names_pool.extend(get_random_sample(pool_medianas, qtd_medianas))
        track_names_pool.extend(get_random_sample(pool_lado_b, qtd_lado_b))
        
        print(f"  De '{artist['name']}': coletadas {total_musicas_a_pegar} músicas ({qtd_famosas}f, {qtd_medianas}m, {qtd_lado_b}lb).")
        
    unique_tracks = list(set(track_names_pool))
    print(f"\nO universo musical da Sofia contém {len(unique_tracks)} músicas ÚNICAS.")
    print("-" * 40)
    
    # --- 4. MONTAGEM DA PLAYLIST FINAL (CORTE PARA 100) ---
    print(f"\n--- PASSO 4: Montando a playlist final com {FINAL_PLAYLIST_SIZE} músicas ---")

    # MUDANÇA: Lógica de sobre-amostragem, mais simples que o preenchimento
    if len(unique_tracks) < FINAL_PLAYLIST_SIZE:
        print(f"AVISO CRÍTICO: Mesmo com a sobre-amostragem, o total de músicas ({len(unique_tracks)}) é menor que {FINAL_PLAYLIST_SIZE}. Usando todas as disponíveis.")
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
    print(f"Playlist '{PLAYLIST_NAME}' criada com {len(track_uris)} músicas e curtidas.")

if __name__ == "__main__":
    main()