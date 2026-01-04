# create_ricardo_playlist.py

"""
================================================================================
MÓDULO DE GERAÇÃO DE PLAYLIST - PERSONA RICARDO (NOSTÁLGICO / ROCK & MPB)
================================================================================

OBJETIVO DO ARQUIVO:
    Gerenciar a criação da playlist para o perfil "Ricardo", focado em clássicos
    dos anos 90 (Rock e MPB). Este módulo implementa a lógica mais complexa
    do sistema: uma seleção "Estratificada Híbrida".

RESPONSABILIDADES:
    1. Dividir os artistas do CSV em "Tiers" (Famosos, Medianos, Lado B) baseando-se
       na posição do ranking (o CSV de entrada já deve estar ordenado).
    2. Aplicar regras de proporção específicas para cada Tier (ex: 40% Famosos).
    3. Para cada artista, selecionar músicas dividindo entre "Hits" e "Lado B" 
       (ex: 60% Hits, 40% Lado B).
    4. Utilizar "Sobre-amostragem" (Oversampling): Coletar mais músicas que o 
       necessário (140) para garantir que, após remover duplicatas, restem 
       pelo menos 100.
    5. Realizar o corte final e persistir a playlist no Spotify.

COMUNICAÇÃO:
    - Entrada: Lê 'ricardo/artistas_classicos_dados.csv'.
    - Saída: Criação de playlist e likes na conta Spotify.
    - Dependências: Usa 'src.functions' para I/O e API.
================================================================================
"""

import random
import math
from src.functions import (
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
    Distribui um número total de músicas entre uma quantidade de artistas de forma
    quase equitativa, mas com variação aleatória para lidar com divisões não exatas.

    Exemplo:
        Se precisamos de 10 músicas de 3 artistas, não podemos pegar 3.33 de cada.
        Esta função retorna algo como [3, 4, 3] ou [4, 3, 3].
    
    Retorno:
        list: Lista de inteiros indicando quantas músicas cada artista deve contribuir.
    """
    distribuicao = [0] * num_artistas
    for _ in range(total_musicas):
        # Sorteia qual artista ganha +1 música no slot até atingir o total
        indice_artista = random.randint(0, num_artistas - 1)
        distribuicao[indice_artista] += 1
    return distribuicao

def main():
    """
    Controlador principal do fluxo do Ricardo.
    
    Lógica de Negócio (Estratificação Dupla):
        1. Estratificação de Artistas: O sistema não pega artistas aleatórios. Ele garante
           uma mistura de Superstars, Artistas Médios e Desconhecidos.
        2. Estratificação de Músicas: Dentro de cada artista, ele não pega apenas as Top 10.
           Ele força a inclusão de faixas menos conhecidas (índices 4 a 10) para gerar
           sensação de profundidade no catálogo.
    """
    
    # --- 1. PAINEL DE CONTROLE (CONFIGURAÇÕES) ---
    print("--- PASSO 1: Carregando configurações para o 'Ricardo Nostálgico' ---")
    
    CSV_FILE = "ricardo/artistas_classicos_dados.csv"
    PLAYLIST_NAME = "Rock & MPB 90s (Input Ricardo)"
    FINAL_PLAYLIST_SIZE = 100

    # Estratégia de Sobre-amostragem (Oversampling):
    # Como artistas de Rock/MPB frequentemente têm colaborações entre si, a chance de
    # duplicatas é alta. Coletamos 40% a mais (140) para ter margem de corte depois.
    TARGET_INICIAL_DE_COLETA = 140

    # Definição dos Tiers de Artistas (Baseado na linha do CSV):
    # O CSV é ordenado por popularidade. 
    # Linhas 0-15 são "Famosos", 15-50 "Medianos", 50-100 "Lado B".
    FATIAS_ARTISTAS_CSV = {'famosos': (0, 15), 'medianos': (15, 50), 'lado_b': (50, 100)}
    
    # Quantos artistas sorteamos de cada fatia para compor a curadoria
    QTD_ARTISTAS_POR_TIER = {'famosos': 6, 'medianos': 4, 'lado_b': 3}

    # Definição da Composição da Playlist (Peso por Tier):
    # Determina qual porcentagem da playlist final virá de cada grupo de artistas.
    PROPORCAO_FINAL_PLAYLIST = {'famosos': 0.40, 'medianos': 0.35, 'lado_b': 0.25}

    # Definição da Seleção de Músicas (Peso por Faixa):
    # Dentro de um artista, quantas músicas serão "Hits" (famosas) vs "Deep Cuts" (medianas).
    PROPORCAO_MUSICAS_POR_ARTISTA = {'famosas': 0.6, 'medianas': 0.4}
    
    # Índices no array de Top Tracks do Spotify:
    # 0-4: As 4 músicas mais ouvidas.
    # 4-10: Músicas entre a 5ª e 10ª posição (Lado B do artista).
    FATIAS_TOP_TRACKS = {'famosas': (0, 4), 'medianas': (4, 10)}

    print(f"Lógica: Sobre-amostragem. Coletar {TARGET_INICIAL_DE_COLETA} faixas para garantir {FINAL_PLAYLIST_SIZE} no final.")
    print("-" * 40)

    # --- 2. SELEÇÃO ESTRATIFICADA DE ARTISTAS ---
    # Seleciona os artistas respeitando as fatias do CSV definidas na configuração.
    print("\n--- PASSO 2: Sorteando um grupo seleto de artistas ---")
    
    all_artists = load_artists_from_csv(CSV_FILE, limit=120)
    selected_artists_por_tier = {'famosos': [], 'medianos': [], 'lado_b': []}

    for tier, (start, end) in FATIAS_ARTISTAS_CSV.items():
        # Recorte do CSV específico para o tier atual
        artist_pool_tier = all_artists[start:end]
        num_to_sample = QTD_ARTISTAS_POR_TIER[tier]
        
        # Sorteio aleatório dentro do tier
        sampled = get_random_sample(artist_pool_tier, min(num_to_sample, len(artist_pool_tier)))
        selected_artists_por_tier[tier] = sampled
        print(f"Sorteados {len(sampled)} artistas do nível '{tier}'.")

    print("-" * 40)

    # --- 3. COLETA DE MÚSICAS (LÓGICA HÍBRIDA) ---
    # Itera sobre os artistas sorteados e coleta as músicas respeitando as proporções
    # de "Hits" vs "Lado B".
    print(f"\n--- PASSO 3: Coletando ~{TARGET_INICIAL_DE_COLETA} músicas com a lógica híbrida ---")
    
    track_names_pool = []
    
    for tier, artists_do_tier in selected_artists_por_tier.items():
        if not artists_do_tier: continue
        
        # Cálculo da Meta do Tier:
        # Quantas músicas ESSE grupo de artistas (ex: Famosos) deve contribuir para o total de 140.
        total_musicas_do_tier = int(TARGET_INICIAL_DE_COLETA * PROPORCAO_FINAL_PLAYLIST[tier])
        
        # Distribui essa meta entre os artistas disponíveis no tier.
        # Ex: Se precisamos de 20 músicas e temos 3 artistas, distribui algo como 7, 7, 6.
        distribuicao_por_artista = distribuir_musicas_entre_artistas(total_musicas_do_tier, len(artists_do_tier))
        
        print(f"\nDo nível '{tier}', coletando um total de {total_musicas_do_tier} músicas.")

        for artist, total_a_pegar in zip(artists_do_tier, distribuicao_por_artista):
            # Obtém as 10 músicas mais populares do artista
            artist_top_tracks = extract_top_tracks_from_data(artist)
            
            # Validação: Fallback para artistas com poucos dados.
            # Se o artista tiver menos de 10 faixas, a lógica de separação Famosas/Medianas falha.
            # Nesse caso, pegamos uma amostra simples do que estiver disponível.
            if len(artist_top_tracks) < 10:
                print(f"  AVISO: '{artist['name']}' tem apenas {len(artist_top_tracks)} tracks. Usando fallback.")
                # Coleta o máximo possível até atingir a cota, sem distinção de tier
                amostra = get_random_sample(artist_top_tracks, min(total_a_pegar, len(artist_top_tracks)))
                track_names_pool.extend(amostra)
                continue # Pula a lógica complexa abaixo

            # Cálculo interno por Artista:
            # Define quantas das músicas a pegar serão do topo (0-4) e quantas do meio (4-10).
            qtd_famosas = math.ceil(total_a_pegar * PROPORCAO_MUSICAS_POR_ARTISTA['famosas'])
            qtd_medianas = total_a_pegar - qtd_famosas

            # Fatiamento das listas de músicas
            pool_famosas = artist_top_tracks[FATIAS_TOP_TRACKS['famosas'][0]:FATIAS_TOP_TRACKS['famosas'][1]]
            pool_medianas = artist_top_tracks[FATIAS_TOP_TRACKS['medianas'][0]:FATIAS_TOP_TRACKS['medianas'][1]]

            # Coleta final para o pool geral
            track_names_pool.extend(get_random_sample(pool_famosas, qtd_famosas))
            track_names_pool.extend(get_random_sample(pool_medianas, qtd_medianas))
            
            print(f"  De '{artist['name']}': coletadas {total_a_pegar} músicas ({qtd_famosas} famosas, {qtd_medianas} medianas).")

    # --- 4. TRATAMENTO FINAL E CORTE ---
    # Remove duplicatas e ajusta o tamanho da lista para o valor exato desejado (100).
    print("\n" + "-" * 40)
    print(f"\n--- PASSO 4: Montando a playlist final ---")

    unique_tracks = list(set(track_names_pool))
    print(f"Total de {len(unique_tracks)} músicas únicas selecionadas na coleta inicial.")

    if len(unique_tracks) < FINAL_PLAYLIST_SIZE:
        # Fallback: Se mesmo coletando 140, as duplicatas reduziram para menos de 100.
        print(f"AVISO CRÍTICO: Mesmo com a sobre-amostragem, o total de músicas únicas ({len(unique_tracks)}) é menor que {FINAL_PLAYLIST_SIZE}. Usando todas as disponíveis.")
        final_track_names = unique_tracks
    else:
        # Caminho Feliz: Temos >100 músicas únicas.
        # Sorteamos aleatoriamente 100 para remover o excedente da sobre-amostragem.
        final_track_names = get_random_sample(unique_tracks, FINAL_PLAYLIST_SIZE)
    
    print(f"Tamanho final da playlist: {len(final_track_names)} músicas.")

    # --- 5. PERSISTÊNCIA NA API DO SPOTIFY ---
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