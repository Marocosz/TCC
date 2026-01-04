# src/collectors/create_beatriz_playlist.py

"""
================================================================================
MÓDULO DE GERAÇÃO DE PLAYLIST - PERSONA BEATRIZ (MAINSTREAM)
================================================================================

OBJETIVO DO ARQUIVO:
    Orquestrar a criação automática da playlist para o perfil "Beatriz" no Spotify.
    Este módulo implementa uma estratégia de seleção baseada em "Popularidade Absoluta",
    simulando um ouvinte que consome o que está em alta no momento (Top Hits).

RESPONSABILIDADES:
    1. Carregar artistas semente de um dataset CSV.
    2. Consultar a API do Spotify para obter as faixas mais populares desses artistas.
    3. Aplicar algoritmo de ordenação global por popularidade (Score 0-100).
    4. Filtrar duplicatas (por URI) e selecionar o Top 100.
    5. Criar a playlist na conta do usuário e salvar as músicas (Like).

COMUNICAÇÃO:
    - Entrada: Lê 'beatriz/artistas_topbrasil_dados.csv'.
    - Saída: Criação de playlist e likes na conta Spotify autenticada.
    - Dependências: Utiliza funções auxiliares de 'functions'.
================================================================================
"""

import sys
import os

# Ajuste de path para garantir importação correta
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
diretorio_src = os.path.dirname(diretorio_atual)
sys.path.append(diretorio_src)

from functions import (
    load_artists_from_csv,
    extract_top_tracks_from_data,
    create_playlist,        
    add_tracks_to_playlist,
    like_tracks_slowly
)

def main():
    """
    Controlador principal do fluxo da Beatriz.
    """
    
    # --- 1. PAINEL DE CONTROLE ---
    print("--- PASSO 1: Carregando configurações para a 'Beatriz Mainstream' ---")
    
    CSV_FILE = r"C:\Users\marco\OneDrive\Documentos\projetos\TCC\data\raw\artistas_topbrasil_dados.csv"
    PLAYLIST_NAME = "Top Hits Brasil (Input Beatriz)"
    FINAL_PLAYLIST_SIZE = 100

    print(f"Lógica: Criar um ranking de músicas por popularidade da FAIXA e selecionar o Top {FINAL_PLAYLIST_SIZE}.")
    print("-" * 40)

    # --- 2. COLETA DE MÚSICAS (RANKING GLOBAL) ---
    print("\n--- PASSO 2: Coletando todas as top músicas de todos os artistas do CSV ---")
    
    all_artists = load_artists_from_csv(CSV_FILE, limit=100)
    
    if not all_artists:
        print("ERRO: Nenhum artista encontrado.")
        return

    # Lista para armazenar TODAS as músicas encontradas (Objeto completo)
    # Formato: [{'name': '...', 'uri': '...', 'popularity': 80}, ...]
    global_track_pool = []

    for artist in all_artists:
        # Pega as top tracks (retorna objetos completos com URI e Popularity via functions.py)
        tracks = extract_top_tracks_from_data(artist)
        
        # Filtra apenas dados válidos
        valid_tracks = []
        for t in tracks:
            # Garante que tem URI e Popularidade
            if isinstance(t, dict) and 'uri' in t and 'popularity' in t:
                valid_tracks.append(t)
        
        global_track_pool.extend(valid_tracks)
        print(f"  + Coletadas {len(valid_tracks)} músicas de '{artist['name']}'")

    print(f"\nColetadas {len(global_track_pool)} músicas no total para o ranking.")
    print("-" * 40)

    # --- 3. ORDENAÇÃO E DEDUPLICAÇÃO (CRÍTICO) ---
    print("\n--- PASSO 3: Ordenando e limpando duplicatas ---")
    
    # 1. Ordena pelo campo 'popularity' da música (do maior para o menor)
    global_track_pool.sort(key=lambda x: x['popularity'], reverse=True)
    
    # 2. Deduplicação por URI (O Segredo para resolver o problema de repetição)
    # Usamos um set para controle rápido e uma lista para manter a ordem do ranking
    unique_uris = []
    seen_uris = set()
    
    for track in global_track_pool:
        if track['uri'] not in seen_uris:
            unique_uris.append(track['uri'])
            seen_uris.add(track['uri'])
            
    print(f"Ranking limpo contém {len(unique_uris)} músicas únicas.")
    print("-" * 40)

    # --- 4. CORTE FINAL (TOP 100) ---
    print(f"\n--- PASSO 4: Selecionando as {FINAL_PLAYLIST_SIZE} músicas mais populares ---")
    
    if len(unique_uris) < FINAL_PLAYLIST_SIZE:
        final_track_uris = unique_uris
        print(f"AVISO: Apenas {len(final_track_uris)} músicas disponíveis no total (Meta era {FINAL_PLAYLIST_SIZE}).")
    else:
        # Pega exatamente as Top 100
        final_track_uris = unique_uris[:FINAL_PLAYLIST_SIZE]
        
    print(f"Playlist final pronta com {len(final_track_uris)} músicas.")

    # --- 5. PERSISTÊNCIA ---
    if not final_track_uris:
        print("ERRO: Lista vazia.")
        return

    playlist_id = create_playlist(PLAYLIST_NAME)
    if playlist_id:
        add_tracks_to_playlist(playlist_id, final_track_uris)
        
        print("\n--- PASSO 6: Curtindo as músicas (uma por uma) ---")
        like_tracks_slowly(final_track_uris)
    
    print("\n--- PROCESSO FINALIZADO! ---")
    print(f"Playlist '{PLAYLIST_NAME}' criada com sucesso.")

if __name__ == "__main__":
    main()