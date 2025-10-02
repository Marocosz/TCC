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
    Função principal para criar a playlist da persona Sofia, com uma
    lógica de curadoria proporcional tanto para artistas quanto para músicas.
    """
    # --- 1. PAINEL DE CONTROLE DA CURADORIA ---
    print("--- PASSO 1: Carregando configurações para a 'Sofia Curadora' ---")
    
    CSV_FILE = "sofia/artistas_indie_dados.csv"
    PLAYLIST_NAME = "Poetic Melancholy (Input Sofia)"
    FINAL_PLAYLIST_SIZE = 100

    # --- Configuração da Seleção de Artistas (PROPORCIONAL) ---
    TOTAL_ARTISTAS_SELECIONADOS = 20

    PROPORCAO_ARTISTAS = {
        'famosos': 0.2,   # 20% dos artistas serão do grupo "famosos"
        'medianos': 0.3,  # 30% serão do grupo "medianos"
        'nicho': 0.5      # 50% serão do grupo "nicho"
    }

    FATIAS_ARTISTAS_CSV = {
        'famosos': (0, 10),    # Pool para sorteio: os 10 artistas mais famosos do CSV
        'medianos': (10, 40),  # Pool para sorteio: artistas do 11º ao 40º
        'nicho': (40, 100)     # Pool para sorteio: artistas do 41º ao 100º
    }

    # --- Configuração da Seleção de Músicas (ALEATÓRIA E PROPORCIONAL) ---
    MUSICAS_POR_ARTISTA_RANGE = (4, 8)
    PROPORCAO_MUSICAS = {'famosas': 0.20, 'medianas': 0.30}
    FATIAS_TOP_TRACKS = {'famosas': (0, 3), 'medianas': (3, 7), 'lado_b': (7, 10)}
    
    print(f"Lógica: Selecionar {TOTAL_ARTISTAS_SELECIONADOS} artistas proporcionalmente e coletar músicas de forma curada.")
    print("-" * 40)

    # --- 2. SELEÇÃO PROPORCIONAL DE ARTISTAS ---
    print("\n--- PASSO 2: Sorteando artistas proporcionalmente por popularidade ---")
    
    all_artists = load_artists_from_csv(CSV_FILE, limit=120) # Carrega uma base grande
    selected_artists = []

    for tier, proportion in PROPORCAO_ARTISTAS.items():
        # Calcula quantos artistas pegar deste tier (ex: 20% de 20 = 4)
        qtd_a_selecionar = int(TOTAL_ARTISTAS_SELECIONADOS * proportion)
        
        # Pega a "fatia" de artistas do CSV para este tier
        start, end = FATIAS_ARTISTAS_CSV[tier]
        artist_pool_tier = all_artists[start:end]
        
        # Sorteia os artistas
        sampled_artists = get_random_sample(artist_pool_tier, min(qtd_a_selecionar, len(artist_pool_tier)))
        selected_artists.extend(sampled_artists)
        print(f"Sorteados {len(sampled_artists)} artistas do nível '{tier}'.")

    print(f"\nTotal de {len(selected_artists)} artistas selecionados para a curadoria.")
    print("-" * 40)

    # --- 3. CRIAÇÃO DO "UNIVERSO MUSICAL" COM COLETA PROPORCIONAL DE MÚSICAS ---
    # (Esta lógica permanece a mesma da versão anterior)
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
        
        print(f"  De '{artist['name']}': coletadas {qtd_famosas} famosas, {qtd_medianas} medianas, {qtd_lado_b} lado B.")
        
    unique_tracks = list(set(track_names_pool))
    print(f"\nO universo musical da Sofia contém {len(unique_tracks)} músicas ÚNICAS.")
    print("-" * 40)
    
    # --- 4. MONTAGEM DA PLAYLIST FINAL COM 100 MÚSICAS ---
    print(f"\n--- PASSO 4: Montando a playlist final com {FINAL_PLAYLIST_SIZE} músicas ---")

    if len(unique_tracks) < FINAL_PLAYLIST_SIZE:
        playlist_size = len(unique_tracks)
        print(f"AVISO CRÍTICO: O universo de músicas únicas ({playlist_size}) é menor que o tamanho desejado. A playlist será criada com o máximo disponível.")
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
    print(f"Playlist '{PLAYLIST_NAME}' criada com {len(track_uris)} músicas e curtidas.")

if __name__ == "__main__":
    main()