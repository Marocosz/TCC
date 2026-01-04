# src/collectors/create_daniel_playlist.py

"""
================================================================================
MÓDULO DE GERAÇÃO DE PLAYLIST - PERSONA DANIEL (LO-FI / CAOS CONTROLADO)
================================================================================

OBJETIVO DO ARQUIVO:
    Gerenciar a criação da playlist para o perfil "Daniel", focado em música Lo-fi.
    Diferente de perfis que buscam popularidade, este módulo prioriza a 
    aleatoriedade e a descoberta (serendipidade), utilizando uma estratégia de 
    sobre-amostragem (oversampling) para garantir diversidade.

RESPONSABILIDADES:
    1. Carregar uma base ampla de artistas do gênero Lo-fi.
    2. Realizar sorteios aleatórios em dois níveis:
       - Nível 1: Seleção aleatória de artistas.
       - Nível 2: Seleção aleatória de quantidade e faixas por artista.
    3. Garantir que a playlist final tenha exatamente 100 músicas (se possível).
    4. Interagir com a API do Spotify para criar a playlist e salvar as músicas.

COMUNICAÇÃO:
    - Entrada: Lê 'daniel/artistas_lofi_dados.csv'.
    - Saída: Criação de playlist e likes na conta Spotify.
    - Dependências: Usa 'functions' para operações de I/O e API.
================================================================================
"""

import random
import sys
import os

# Ajuste de path para garantir importação correta
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
diretorio_src = os.path.dirname(diretorio_atual)
sys.path.append(diretorio_src)

from functions import (
    load_artists_from_csv,
    extract_top_tracks_from_data,
    get_random_sample,
    create_playlist,        # Fetch removido pois usamos URIs diretas agora
    add_tracks_to_playlist,
    like_tracks_slowly
)

def main():
    """
    Função controladora principal do fluxo do Daniel.
    
    Estratégia "Caos Controlado":
        Ao invés de pegar as top 10 músicas de 10 artistas, este fluxo sorteia
        uma quantidade variável de músicas (4 a 8) de um número maior de artistas,
        criando um "pool" excedente que é recortado aleatoriamente no final.
    """
    
    # --- 1. PAINEL DE CONTROLE (CONFIGURAÇÕES) ---
    print("--- PASSO 1: Carregando configurações para o 'Daniel - Caos Controlado' ---")
    
    # Caminho absoluto para garantir leitura
    CSV_FILE = r"C:\Users\marco\OneDrive\Documentos\projetos\TCC\data\raw\artistas_lofi_dados.csv"
    PLAYLIST_NAME = "Lofi Flow (Input Daniel)"
    FINAL_PLAYLIST_SIZE = 100 # Meta final de faixas na playlist

    # Configuração de Amostragem de Artistas:
    # Lemos 80 do CSV, mas usaremos apenas 22 para compor a playlist.
    ARTIST_SOURCE_POOL_SIZE = 80 
    ARTISTAS_A_SELECIONAR = 22 

    # Configuração de Amostragem de Músicas:
    # Define o intervalo aleatório de faixas a serem extraídas de cada artista.
    MUSICAS_POR_ARTISTA_RANGE = (4, 8)

    print(f"Lógica: Sobre-amostragem aleatória. Sortear {ARTISTAS_A_SELECIONAR} artistas para garantir {FINAL_PLAYLIST_SIZE} músicas únicas.")
    print("-" * 40)

    # --- 2. SELEÇÃO ALEATÓRIA DE ARTISTAS ---
    # Etapa de filtro inicial: Reduz o universo total de artistas para um subgrupo sorteado.
    print("\n--- PASSO 2: Sorteando artistas aleatoriamente ---")
    
    all_artists_pool = load_artists_from_csv(CSV_FILE, limit=ARTIST_SOURCE_POOL_SIZE)
    
    if not all_artists_pool:
        print("ERRO CRÍTICO: Nenhum artista encontrado no CSV.")
        return

    # Validação de segurança:
    if len(all_artists_pool) < ARTISTAS_A_SELECIONAR:
        print("AVISO: O pool de artistas é menor que o número desejado. Usando todos os artistas disponíveis.")
        ARTISTAS_A_SELECIONAR = len(all_artists_pool)
        
    selected_artists = get_random_sample(all_artists_pool, ARTISTAS_A_SELECIONAR)
    
    print(f"{len(selected_artists)} artistas foram sorteados aleatoriamente para a curadoria.")
    print("-" * 40)

    # --- 3. CRIAÇÃO DO "UNIVERSO MUSICAL" (TRACK POOL) ---
    # Coleta as músicas dos artistas selecionados aplicando aleatoriedade na quantidade.
    print(f"\n--- PASSO 3: Criando 'pote' de músicas com coleta duplamente aleatória ---")
    
    track_uris_pool = [] # Alterado para guardar URIs (Links) em vez de Nomes
    
    for artist in selected_artists:
        # Extrai a lista de objetos de faixa (agora retorna objetos completos com URI)
        raw_tracks = extract_top_tracks_from_data(artist)
        
        # Filtra apenas as URIs válidas
        artist_uris = []
        for t in raw_tracks:
            if isinstance(t, dict) and 'uri' in t:
                artist_uris.append(t['uri'])
        
        # Se não tiver músicas, pula
        if not artist_uris:
            continue

        # Define aleatoriamente quantas faixas esse artista específico vai contribuir
        # Proteção: Se tiver menos músicas que o sorteado, ajusta o teto
        num_musicas_a_pegar = random.randint(MUSICAS_POR_ARTISTA_RANGE[0], MUSICAS_POR_ARTISTA_RANGE[1])
        num_musicas_a_pegar = min(num_musicas_a_pegar, len(artist_uris))
        
        # Seleciona as faixas aleatoriamente dentro do repertório do artista
        musicas_selecionadas = get_random_sample(artist_uris, num_musicas_a_pegar)
        
        track_uris_pool.extend(musicas_selecionadas)
        print(f"  + Coletadas {len(musicas_selecionadas)} músicas aleatórias de '{artist['name']}'.")
        
    # Deduplicação: Remove URIs repetidas
    # AGORA FUNCIONA: Strings (URIs) são hashables, dicionários não eram.
    unique_uris = list(set(track_uris_pool))
    
    print(f"\nO universo musical contém {len(unique_uris)} músicas ÚNICAS para o sorteio final.")
    print("-" * 40)
    
    # --- 4. SELEÇÃO FINAL (CORTE PARA 100) ---
    # Ajusta a lista para o tamanho exato da playlist (FINAL_PLAYLIST_SIZE).
    print(f"\n--- PASSO 4: Montando a playlist final com {FINAL_PLAYLIST_SIZE} músicas ---")

    if len(unique_uris) < FINAL_PLAYLIST_SIZE:
        # Caso de exceção: Se a coleta aleatória não gerou faixas suficientes.
        print(f"AVISO CRÍTICO: Mesmo com a sobre-amostragem, o total ({len(unique_uris)}) é menor que {FINAL_PLAYLIST_SIZE}. Usando todas.")
        final_track_uris = unique_uris
    else:
        # Caminho feliz: Temos mais músicas que o necessário.
        # Sorteamos exatamente 100 faixas do pool limpo para garantir variedade máxima.
        final_track_uris = get_random_sample(unique_uris, FINAL_PLAYLIST_SIZE)

    print(f"Sorteadas {len(final_track_uris)} músicas para a playlist final.")

    # --- 5. PERSISTÊNCIA NA API DO SPOTIFY ---
    if not final_track_uris: 
        print("ERRO: Nenhuma música selecionada.")
        return

    # Cria a playlist vazia na conta do usuário
    playlist_id = create_playlist(PLAYLIST_NAME)
    
    if playlist_id:
        # Adiciona as faixas à playlist criada
        # Nota: Passamos URIs direto, sem precisar de fetch_track_uris
        add_tracks_to_playlist(playlist_id, final_track_uris)
        
        # Simula o comportamento do usuário "curtindo" as músicas
        print("\n--- PASSO 5: Curtindo as músicas (uma por uma) ---")
        like_tracks_slowly(final_track_uris)
    
    print("\n--- PROCESSO FINALIZADO! ---")
    print(f"Playlist '{PLAYLIST_NAME}' criada com sucesso.")

if __name__ == "__main__":
    main()