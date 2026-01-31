# TIPO DE ARQUIVO: RECEBE CSV

"""
================================================================================
ARQUITETURA DO TCC: GERADOR DANIEL (LO-FI / ORGANIC FOCUS)
================================================================================

Objetivo do Arquivo:
    Gerar a playlist da Persona "Daniel", focada em Lo-Fi/Focus e uma
    distribuição mais humanizada ("orgânica") das faixas.

Parte do Sistema:
    Collectors (Gerador de Dataset de Entrada).

Responsabilidades:
    1. Simulação Orgânica: Distribui faixas de forma desigual entre artistas
       para evitar a "roboticidade" de ter fixo 2 músicas por artista.
    2. Estratificação: Divide a playlist em 3 tiers (Vibe Setters, Flow Keepers, Textures).
    3. Construção: Seleciona as faixas e monta a playlist de 200 músicas.

Comunicação:
    - Entrada: CSV `data/raw/artistas_lofi_dados.csv`.
    - Saída: Playlist 'Focus Flow Organic' no Spotify.

Uso:
    python src/collectors/create_daniel_playlist.py
"""

import sys
import os
import random
import time

# --- CONFIGURAÇÃO DE AMBIENTE ---
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

# --- CONFIGURAÇÕES AJUSTÁVEIS ---
CONFIG = {
    "CSV_PATH": r"C:\Users\marco\OneDrive\Documentos\Pessoal\Projetos\TCC\data\raw\artistas_lofi_dados.csv",
    "PLAYLIST_NAME": "Focus Flow Organic (Input Daniel)",
    
    # Etapa 1: Vibe Setters (Alta densidade, mas variável)
    "STAGE_1": {
        "total_tracks": 60,
        "artist_range": (0, 10),    # Top 10 artistas
        "tracks_per_artist": (4, 8) # Entre 4 e 8 músicas (Média 6)
    },
    # Etapa 2: Flow Keepers (Média densidade)
    "STAGE_2": {
        "total_tracks": 80,
        "artist_range": (10, 30),   # Próximos 20 artistas
        "tracks_per_artist": (2, 6) # Entre 2 e 6 músicas (Média 4)
    },
    # Etapa 3: Textura (Baixa densidade)
    "STAGE_3": {
        "total_tracks": 60,
        "artist_start_index": 30,   # Do 31 em diante
        "pool_size_to_fetch": 150   # Analisa pool grande
    }
}

def distribuir_cotas(total_alvo, num_artistas, min_p, max_p):
    """
    Calcula quantas músicas cada artista vai contribuir para a playlist.

    Lógica de Negócio:
        Em vez de uma divisão matemática exata (ex: 200/100 = 2), usamos
        aleatoriedade controlada para dar "peso" a determinados artistas,
        simulando a preferência real de um usuário.

    Args:
        total_alvo (int): Quantas músicas no total precisamos nesta etapa.
        num_artistas (int): Quantos artistas estão disponíveis.
        min_p (int): Mínimo de músicas por artista.
        max_p (int): Máximo de músicas por artista.

    Returns:
        list: Lista de inteiros representando a cota de cada artista.
    """
    if num_artistas == 0: return []
    
    # 1. Garante o mínimo para todos
    cotas = [min_p] * num_artistas
    saldo_restante = total_alvo - sum(cotas)
    
    # Fallback de segurança
    if saldo_restante < 0:
        return [max(1, total_alvo // num_artistas)] * num_artistas

    # 2. Distribui o saldo aleatoriamente (aqui nasce a variação orgânica)
    indices = list(range(num_artistas))
    while saldo_restante > 0:
        idx = random.choice(indices)
        # Só adiciona se não estourar o máximo desse artista
        if cotas[idx] < max_p:
            cotas[idx] += 1
            saldo_restante -= 1
        
        # Break de segurança se todos atingirem o máximo
        if all(c == max_p for c in cotas) and saldo_restante > 0:
            break 
            
    return cotas

def main():
    """
    Função Principal (Flow Builder).
    Executa a lógica de 3 estágios para montagem da playlist.
    """
    print("\n" + "="*60)
    print(f"INICIANDO GERADOR ORGÂNICO: {CONFIG['PLAYLIST_NAME']}")
    print("="*60)

    # 1. Carregar e Ordenar (Prioriza Artistas Populares do Nicho)
    all_artists = load_artists_from_csv(CONFIG['CSV_PATH'], limit=400)
    if not all_artists:
        print("[!] Erro: CSV vazio ou não encontrado.")
        return
    
    all_artists.sort(key=lambda x: int(x.get('popularity', 0)), reverse=True)
    print(f"Base carregada: {len(all_artists)} artistas ordenados por popularidade.")

    final_playlist_uris = []
    seen_uris = set() # Controle global de duplicidade

    # ==========================================================================
    # ETAPA 1: VIBE SETTERS (Top 10)
    # ==========================================================================
    # Define a "cara" da playlist. Poucos artistas com muitas músicas.
    print(f"\n--- [ETAPA 1] Vibe Setters (Top 10 -> {CONFIG['STAGE_1']['total_tracks']} faixas) ---")
    
    s1_cfg = CONFIG['STAGE_1']
    artists_s1 = all_artists[s1_cfg['artist_range'][0] : s1_cfg['artist_range'][1]]
    
    # Aqui a mágica acontece: uns terão 4, outros 7, outros 5...
    cotas_s1 = distribuir_cotas(
        s1_cfg['total_tracks'], 
        len(artists_s1), 
        s1_cfg['tracks_per_artist'][0], 
        s1_cfg['tracks_per_artist'][1]
    )

    count_s1 = 0
    for artist, quota in zip(artists_s1, cotas_s1):
        tracks = extract_top_tracks_from_data(artist)
        added = 0
        for t in tracks:
            if added >= quota: break
            if t['uri'] not in seen_uris:
                final_playlist_uris.append(t['uri'])
                seen_uris.add(t['uri'])
                added += 1
                count_s1 += 1
        print(f"  > {artist['name']}: {added} músicas (Meta variável: {quota})")

    # ==========================================================================
    # ETAPA 2: FLOW KEEPERS (Top 11-30)
    # ==========================================================================
    # Mantém o fluxo sem repetir demais os mesmos nomes.
    print(f"\n--- [ETAPA 2] Flow Keepers (Top 11-30 -> {CONFIG['STAGE_2']['total_tracks']} faixas) ---")
    
    s2_cfg = CONFIG['STAGE_2']
    artists_s2 = all_artists[s2_cfg['artist_range'][0] : s2_cfg['artist_range'][1]]
    
    cotas_s2 = distribuir_cotas(
        s2_cfg['total_tracks'], 
        len(artists_s2), 
        s2_cfg['tracks_per_artist'][0], 
        s2_cfg['tracks_per_artist'][1]
    )

    count_s2 = 0
    for artist, quota in zip(artists_s2, cotas_s2):
        tracks = extract_top_tracks_from_data(artist)
        added = 0
        for t in tracks:
            if added >= quota: break
            if t['uri'] not in seen_uris:
                final_playlist_uris.append(t['uri'])
                seen_uris.add(t['uri'])
                added += 1
                count_s2 += 1
        print(f"  > {artist['name']}: {added} músicas (Meta variável: {quota})")

    # ==========================================================================
    # ETAPA 3: TEXTURES (Variedade com Cauda Longa)
    # ==========================================================================
    # Preenche o restante com "descobertas" (1 ou 2 músicas por artista).
    print(f"\n--- [ETAPA 3] Textures (Top 31+ -> {CONFIG['STAGE_3']['total_tracks']} faixas) ---")
    
    s3_cfg = CONFIG['STAGE_3']
    target_s3 = s3_cfg['total_tracks']
    
    # Compensa qualquer falha das etapas anteriores para garantir os 200
    deficit = (s1_cfg['total_tracks'] - count_s1) + (s2_cfg['total_tracks'] - count_s2)
    if deficit > 0:
        print(f"  [!] Ajuste: Compensando {deficit} músicas faltantes.")
        target_s3 += deficit

    pool_artists = all_artists[s3_cfg['artist_start_index'] : s3_cfg['artist_start_index'] + s3_cfg['pool_size_to_fetch']]
    global_pool_tracks = []
    pool_seen_uris = set() # Evita duplicatas internas no pool
    
    print(f"  > Analisando catálogo de {len(pool_artists)} artistas restantes...")
    
    for artist in pool_artists:
        tracks = extract_top_tracks_from_data(artist)
        
        # Trava leve: Máximo 2 por artista nesta etapa para garantir rotatividade
        added_from_artist = 0
        for t in tracks:
            if added_from_artist >= 2: break 
            
            if t['uri'] not in seen_uris and t['uri'] not in pool_seen_uris:
                global_pool_tracks.append(t)
                pool_seen_uris.add(t['uri'])
                added_from_artist += 1
    
    # Ordena por popularidade (garante qualidade mínima mesmo na cauda longa)
    global_pool_tracks.sort(key=lambda x: x['popularity'], reverse=True)
    
    selected_s3 = global_pool_tracks[:target_s3]
    
    for t in selected_s3:
        final_playlist_uris.append(t['uri'])
        seen_uris.add(t['uri'])
        
    print(f"  > Selecionadas {len(selected_s3)} músicas de vários artistas.")

    # ==========================================================================
    # FINALIZAÇÃO
    # ==========================================================================
    print("\n" + "-"*40)
    print(f"RESUMO FINAL:")
    print(f"Etapa 1: {count_s1}")
    print(f"Etapa 2: {count_s2}")
    print(f"Etapa 3: {len(selected_s3)}")
    print(f"TOTAL: {len(final_playlist_uris)} músicas únicas.")
    print("-" * 40)

    if len(final_playlist_uris) == 0: return

    playlist_id = create_playlist(CONFIG['PLAYLIST_NAME'])
    if playlist_id:
        add_tracks_to_playlist(playlist_id, final_playlist_uris)
        print(f"\n--- Aplicando 'Likes' na conta... ---")
        like_tracks_slowly(final_playlist_uris)
        
    print(f"\n✅ SUCESSO! Playlist '{CONFIG['PLAYLIST_NAME']}' criada.")

if __name__ == "__main__":
    main()