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
    - Dependências: Usa 'functions' para I/O e API.
================================================================================
"""

import random
import math
import sys
import os

# Ajuste de path para garantir importação correta caso rodado de subpasta
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
diretorio_src = os.path.dirname(diretorio_atual)
sys.path.append(diretorio_src)

from functions import (
    load_artists_from_csv,
    extract_top_tracks_from_data,
    get_random_sample,
    create_playlist,        # Fetch removido/não usado pois já pegamos a URI na origem
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
    if num_artistas == 0: return []
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
           uma mistura de Superstars, Artistas Médios e Desconhecidos usando % do total.
        2. Estratificação de Músicas: Dentro de cada artista, ele não pega apenas as Top 10.
           Ele força a inclusão de faixas menos conhecidas (índices 4 a 10) para gerar
           sensação de profundidade no catálogo.
    """
    
    # --- 1. PAINEL DE CONTROLE (CONFIGURAÇÕES) ---
    print("--- PASSO 1: Carregando configurações para o 'Ricardo Nostálgico' ---")
    
    # Usando caminho absoluto conforme sua configuração anterior
    CSV_FILE = r"C:\Users\marco\OneDrive\Documentos\projetos\TCC\data\raw\artistas_classicos_dados.csv"
    PLAYLIST_NAME = "Rock & MPB 90s (Input Ricardo)"
    FINAL_PLAYLIST_SIZE = 100

    # Estratégia de Sobre-amostragem (Oversampling):
    # Como artistas de Rock/MPB frequentemente têm colaborações entre si, a chance de
    # duplicatas é alta. Coletamos 40% a mais (140) para ter margem de corte depois.
    TARGET_INICIAL_DE_COLETA = 140

    # --- CARREGAMENTO INICIAL PARA CÁLCULO DE TIERS ---
    # Carregamos até 200 artistas para garantir que temos o dataset completo
    all_artists = load_artists_from_csv(CSV_FILE, limit=200)
    total_artistas = len(all_artists)
    
    print(f"Total de artistas disponíveis no CSV: {total_artistas}")

    if total_artistas == 0:
        print("ERRO CRÍTICO: Nenhum artista encontrado no CSV.")
        return

    # --- DEFINIÇÃO DINÂMICA DE TIERS (BASEADA EM %) ---
    # Em vez de números fixos (0-15), usamos porcentagens para adaptar a datasets pequenos.
    # Tier 1 (Famosos): Top 15%
    # Tier 2 (Medianos): Próximos 35%
    # Tier 3 (Lado B): Restante 50%
    
    idx_famosos = max(1, int(total_artistas * 0.15)) # Pelo menos 1 famoso
    idx_medianos = max(idx_famosos + 1, int(total_artistas * 0.50)) # Até 50% da lista

    FATIAS_ARTISTAS_CSV = {
        'famosos': (0, idx_famosos),
        'medianos': (idx_famosos, idx_medianos),
        'lado_b': (idx_medianos, total_artistas)
    }
    
    print(f"Distribuição de Tiers calculada: Famosos({0}-{idx_famosos}), Medianos({idx_famosos}-{idx_medianos}), Lado B({idx_medianos}-{total_artistas})")

    # Quantos artistas sorteamos de cada fatia para compor a curadoria
    # Ajustamos dinamicamente se o tier for muito pequeno (pega todos se tiver menos que a meta)
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
    # Seleciona os artistas respeitando as fatias calculadas acima.
    print("\n--- PASSO 2: Sorteando um grupo seleto de artistas ---")
    
    selected_artists_por_tier = {'famosos': [], 'medianos': [], 'lado_b': []}

    for tier, (start, end) in FATIAS_ARTISTAS_CSV.items():
        # Recorte do CSV específico para o tier atual
        artist_pool_tier = all_artists[start:end]
        
        # Se o tier estiver vazio (ex: dataset muito pequeno), avisa e continua
        if not artist_pool_tier:
            print(f"AVISO: Tier '{tier}' está vazio. Pulando.")
            continue

        # Tenta pegar a quantidade alvo, mas se não tiver o suficiente, pega todos do tier
        num_to_sample = QTD_ARTISTAS_POR_TIER[tier]
        sampled = get_random_sample(artist_pool_tier, min(num_to_sample, len(artist_pool_tier)))
        
        selected_artists_por_tier[tier] = sampled
        print(f"Sorteados {len(sampled)} artistas do nível '{tier}'.")

    print("-" * 40)

    # --- 3. COLETA DE MÚSICAS (LÓGICA HÍBRIDA) ---
    # Itera sobre os artistas sorteados e coleta as músicas respeitando as proporções
    # de "Hits" vs "Lado B".
    print(f"\n--- PASSO 3: Coletando ~{TARGET_INICIAL_DE_COLETA} músicas (Via URI) com a lógica híbrida ---")
    
    track_uris_pool = [] # Renomeado para refletir que guardamos URIs
    
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
            # Obtém os objetos completos das músicas
            raw_tracks = extract_top_tracks_from_data(artist)
            
            # --- CORREÇÃO ARTISTA ERRADO ---
            # Extrai diretamente as URIs para evitar busca por nome depois.
            artist_track_uris = []
            for t in raw_tracks:
                if isinstance(t, dict) and 'uri' in t:
                    artist_track_uris.append(t['uri'])
            
            # Validação: Fallback para artistas com poucos dados.
            # Se o artista tiver menos de 10 faixas (quebra lógica de fatiamento)
            # OU se tiver menos músicas do que a quantidade solicitada (total_a_pegar).
            if len(artist_track_uris) < 10 or len(artist_track_uris) < total_a_pegar:
                print(f"  AVISO: '{artist['name']}' tem apenas {len(artist_track_uris)} tracks. Usando fallback.")
                # Coleta o máximo possível até atingir a cota, sem distinção de tier
                # OBS: Aqui já estamos adicionando URIs
                amostra = get_random_sample(artist_track_uris, min(total_a_pegar, len(artist_track_uris)))
                track_uris_pool.extend(amostra)
                continue # Pula a lógica complexa abaixo

            # Cálculo interno por Artista:
            # Define quantas das músicas a pegar serão do topo (0-4) e quantas do meio (4-10).
            qtd_famosas = math.ceil(total_a_pegar * PROPORCAO_MUSICAS_POR_ARTISTA['famosas'])
            qtd_medianas = total_a_pegar - qtd_famosas

            # Fatiamento das listas de músicas (Usando a lista de URIs)
            pool_famosas = artist_track_uris[FATIAS_TOP_TRACKS['famosas'][0]:FATIAS_TOP_TRACKS['famosas'][1]]
            pool_medianas = artist_track_uris[FATIAS_TOP_TRACKS['medianas'][0]:FATIAS_TOP_TRACKS['medianas'][1]]

            # Coleta final para o pool geral
            track_uris_pool.extend(get_random_sample(pool_famosas, qtd_famosas))
            track_uris_pool.extend(get_random_sample(pool_medianas, qtd_medianas))
            
            print(f"  De '{artist['name']}': coletadas {total_a_pegar} músicas ({qtd_famosas} famosas, {qtd_medianas} medianas).")

    # --- 4. TRATAMENTO FINAL E CORTE ---
    # Remove duplicatas e ajusta o tamanho da lista para o valor exato desejado (100).
    print("\n" + "-" * 40)
    print(f"\n--- PASSO 4: Montando a playlist final ---")

    unique_uris = list(set(track_uris_pool))
    print(f"Total de {len(unique_uris)} músicas únicas selecionadas na coleta inicial.")

    if len(unique_uris) < FINAL_PLAYLIST_SIZE:
        # Fallback: Se mesmo coletando 140, as duplicatas reduziram para menos de 100.
        print(f"AVISO CRÍTICO: Mesmo com a sobre-amostragem, o total de músicas únicas ({len(unique_uris)}) é menor que {FINAL_PLAYLIST_SIZE}. Usando todas as disponíveis.")
        final_track_uris = unique_uris
    else:
        # Caminho Feliz: Temos >100 músicas únicas.
        # Sorteamos aleatoriamente 100 para remover o excedente da sobre-amostragem.
        final_track_uris = get_random_sample(unique_uris, FINAL_PLAYLIST_SIZE)
    
    print(f"Tamanho final da playlist: {len(final_track_uris)} músicas.")

    # --- 5. PERSISTÊNCIA NA API DO SPOTIFY ---
    # CORREÇÃO: Não chamamos mais fetch_track_uris pois já temos URIs.
    # Verificamos apenas se a lista não está vazia.
    if not final_track_uris: 
        return

    playlist_id = create_playlist(PLAYLIST_NAME)
    if playlist_id:
        add_tracks_to_playlist(playlist_id, final_track_uris)
        
        print("\n--- PASSO 5: Curtindo as músicas (uma por uma) ---")
        like_tracks_slowly(final_track_uris)
    
    print("\n--- PROCESSO FINALIZADO! ---")

if __name__ == "__main__":
    main()