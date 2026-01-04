# create_sofia_playlist.py

"""
================================================================================
MÓDULO DE GERAÇÃO DE PLAYLIST - PERSONA SOFIA (ALTERNATIVA / DESCOBERTA)
================================================================================

OBJETIVO DO ARQUIVO:
    Gerenciar a criação da playlist para o perfil "Sofia", focado em música 
    alternativa e descoberta de "Lado B". A estratégia desta persona é baseada 
    em uma playlist semente, mas aplica uma lógica de inversão de popularidade.

RESPONSABILIDADES:
    1. Analisar uma Playlist Semente para extrair o pool de artistas.
    2. Classificar esses artistas em dois grupos (Clusters): 
       - Populares (Top 50% de popularidade).
       - Nicho (Bottom 50% de popularidade).
    3. Aplicar "Orçamento Ponderado":
       - Dar mais espaço (70%) para artistas de Nicho.
       - Dar menos espaço (30%) para artistas Populares.
    4. Aplicar "Filtro Anti-Hit" para artistas populares (ignorar as top 5 faixas).
    5. Explorar discografia completa (álbuns/singles) em vez de apenas Top Tracks.

COMUNICAÇÃO:
    - Entrada: Playlist Semente do Spotify (URL definida no código).
    - Saída: Criação de playlist e likes na conta Spotify.
    - Dependências: Usa 'spotipy' intensivamente para navegação em álbuns.
================================================================================
"""

import random
import math
import sys
import os

# --- Configuração de Caminho para Importação de Módulos Locais ---
# Garante que o script possa encontrar o pacote 'src' mesmo rodando de uma subpasta.
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
diretorio_pai = os.path.dirname(diretorio_atual)
sys.path.append(diretorio_pai)

from functions import *
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# --- FUNÇÕES AUXILIARES ESPECÍFICAS DA PERSONA SOFIA ---

def get_primary_artists_from_playlist_pure(sp_client, playlist_id: str) -> dict:
    """
    Extrai todos os artistas principais (o primeiro creditado) de uma playlist semente.
    
    Por que existe:
        Para criar um universo musical baseado no gosto real da persona (simulado
        pela playlist semente), mas sem se prender às músicas específicas de lá.
    
    Retorno:
        dict: Dicionário {artist_id: artist_object} para garantir unicidade.
    """
    print("Buscando APENAS os artistas principais da playlist semente...")
    unique_artists = {}
    
    # Paginação para ler playlists grandes (>100 músicas)
    results = sp_client.playlist_items(playlist_id)
    playlist_items = results['items']
    while results['next']:
        results = sp_client.next(results)
        playlist_items.extend(results['items'])
        
    for item in playlist_items:
        # Validação de integridade dos dados da faixa
        if item.get("track") and item['track'] and item['track'].get('artists'):
            primary_artist = item["track"]["artists"][0]
            if primary_artist['id'] not in unique_artists:
                unique_artists[primary_artist['id']] = primary_artist
                
    return unique_artists

def get_artist_album_tracks_pure(sp_client, artist_id: str, limit_albums=5) -> list:
    """
    Busca faixas de álbuns e singles do artista, indo além das 'Top Tracks'.
    
    Regra de Negócio (Sofia):
        A persona Sofia busca "Lado B" e faixas não comerciais. Usar o endpoint
        padrão 'top-tracks' viciaria o resultado em hits. Esta função varre
        os álbuns para encontrar o catálogo profundo.
        
    Retorno:
        list: Lista de objetos de faixa completos (track objects).
    """
    all_track_ids = set()
    try:
        # Busca os álbuns mais recentes ou relevantes
        results = sp_client.artist_albums(artist_id, album_type='album,single', limit=limit_albums)
        
        # Itera sobre os álbuns para pegar os IDs das faixas
        for album in results['items']:
            track_results = sp_client.album_tracks(album['id'])
            for track in track_results['items']:
                if track and track.get('id'):
                    all_track_ids.add(track['id'])
    except Exception:
        return []
    
    # Hidratação dos dados:
    # A chamada anterior retorna objetos simplificados. Precisamos fazer uma nova
    # chamada (tracks) para obter metadados como 'popularity' de cada faixa.
    full_track_objects = []
    if all_track_ids:
        # Batching: A API permite no máximo 50 IDs por chamada
        for i in range(0, len(list(all_track_ids)), 50):
            batch_ids = list(all_track_ids)[i:i+50]
            try:
                tracks_info = sp_client.tracks(batch_ids)
                full_track_objects.extend([t for t in tracks_info['tracks'] if t])
            except Exception:
                continue
    return full_track_objects

def distribuir_musicas_entre_artistas(total_musicas: int, num_artistas: int) -> list:
    """
    Algoritmo de distribuição inteira de carga.
    Evita divisões flutuantes (ex: 3.33 músicas) distribuindo o resto aleatoriamente.
    """
    if num_artistas == 0: return []
    distribuicao = [0] * num_artistas
    for _ in range(total_musicas):
        distribuicao[random.randint(0, num_artistas - 1)] += 1
    return distribuicao

def main():
    """
    Controlador principal do fluxo da Sofia.
    
    Estratégia "Robin Hood Musical":
        O algoritmo tira visibilidade dos artistas ricos (Populares) e dá 
        visibilidade aos pobres (Nicho). Além disso, quando obrigado a tocar 
        artistas famosos, o algoritmo evita seus maiores hits.
    """
    
    # --- 1. PAINEL DE CONTROLE ---
    print("--- PASSO 1: Carregando configurações da 'Curadoria Ponderada' ---")
    
    PLAYLIST_URL_SEMENTE = "https://open.spotify.com/playlist/5m7jvWtwE8OJ9DgzU6jhUu?si=d7c7e756ee9c4331" # Placeholder da URL
    NOVO_PLAYLIST_NAME = "Alternativa Pura (Input Sofia)"
    FINAL_PLAYLIST_SIZE = 100
    TARGET_INICIAL_DE_COLETA = 130 # Margem de segurança para deduplicação

    # Regra de Negócio: Definição dos Pesos (Orçamento)
    PROPORCAO_PLAYLIST_POR_TIER = {
        'populares': 0.3, # Apenas 30% para artistas mainstream
        'nicho': 0.7      # 70% focado em artistas desconhecidos/médios
    }
    print("-" * 40)

    # --- 2. COLETAR E CLASSIFICAR ARTISTAS (SEGMENTAÇÃO) ---
    # Analisa a playlist semente e divide os artistas em dois grupos baseados na mediana.
    print("\n--- PASSO 2: Coletando e classificando os artistas da playlist base ---")
    
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-read-private"))
    
    try:
        # 1. Extração
        artistas_simplificados_map = get_primary_artists_from_playlist_pure(sp, PLAYLIST_URL_SEMENTE.split('/')[-1].split('?')[0])
        
        # 2. Enriquecimento (buscar dados de popularidade do artista)
        todos_os_artistas_com_pop = get_full_artist_profiles(artistas_simplificados_map)
        
        # 3. Ordenação para corte
        todos_os_artistas_com_pop.sort(key=lambda x: int(x['popularity']), reverse=True)
        
        # 4. Segmentação (50/50 da lista encontrada)
        ponto_de_corte = len(todos_os_artistas_com_pop) // 2
        artistas_populares = todos_os_artistas_com_pop[:ponto_de_corte]
        artistas_nicho = todos_os_artistas_com_pop[ponto_de_corte:]

        print(f"Encontrados {len(todos_os_artistas_com_pop)} artistas principais. Divisão 50/50.")
        print("-" * 40)

    except Exception as e:
        print(f"ERRO: Não foi possível processar a playlist base. Erro: {e}")
        return

    # --- 3. COLETAR MÚSICAS COM LÓGICA PONDERADA ---
    # Aqui reside a lógica principal: Tratamento diferente para cada grupo de artistas.
    print("\n--- PASSO 3: Coletando músicas com a lógica Ponderada ---")
    
    track_uris_pool = []
    
    # GRUPO A: ARTISTAS POPULARES (Tratamento "Lado B")
    # Calcula quantas músicas pegar deste grupo (ex: 30% de 130 = ~39 músicas)
    orcamento_populares = int(TARGET_INICIAL_DE_COLETA * PROPORCAO_PLAYLIST_POR_TIER['populares'])
    distribuicao_populares = distribuir_musicas_entre_artistas(orcamento_populares, len(artistas_populares))
    
    print(f"\nProcessando artistas 'populares' (Orçamento: {orcamento_populares} músicas)...")
    
    for artist, total_a_pegar in zip(artistas_populares, distribuicao_populares):
        if total_a_pegar == 0: continue
        
        # Busca catálogo profundo (álbuns)
        todas_as_faixas_obj = get_artist_album_tracks_pure(sp, artist['uri'].split(':')[-1])
        
        # Ordena por popularidade da FAIXA
        todas_as_faixas_obj.sort(key=lambda x: x.get('popularity', 0), reverse=True)
        
        # FILTRO ANTI-HIT: Ignora as 5 faixas mais populares encontradas nos álbuns
        # PROTEÇÃO: Se o artista tiver poucas músicas (ex: EP de 4 faixas), 
        # não aplicamos o corte para não zerar a lista e perder o artista.
        if len(todas_as_faixas_obj) > 5:
            pool_musicas = todas_as_faixas_obj[5:] # Pega só "Lado B"
        else:
            pool_musicas = todas_as_faixas_obj # Se tem poucas, usa o que tem
        
        selecao_uris = get_random_sample([track['uri'] for track in pool_musicas], total_a_pegar)
        track_uris_pool.extend(selecao_uris)
        print(f"  + {len(selecao_uris)} URIs 'lado B' de '{artist['name']}'")

    # GRUPO B: ARTISTAS DE NICHO (Tratamento Livre)
    # Calcula o restante do orçamento (ex: ~91 músicas)
    orcamento_nicho = TARGET_INICIAL_DE_COLETA - orcamento_populares
    distribuicao_nicho = distribuir_musicas_entre_artistas(orcamento_nicho, len(artistas_nicho))
    
    print(f"\nProcessando artistas de 'nicho' (Orçamento: {orcamento_nicho} músicas)...")
    
    for artist, total_a_pegar in zip(artistas_nicho, distribuicao_nicho):
        if total_a_pegar == 0: continue
        
        # Busca catálogo profundo
        todas_as_faixas_obj = get_artist_album_tracks_pure(sp, artist['uri'].split(':')[-1])
        
        # Sem filtro anti-hit: Para artistas de nicho, qualquer música é válida/descoberta
        pool_musicas = todas_as_faixas_obj 
        
        selecao_uris = get_random_sample([track['uri'] for track in pool_musicas], total_a_pegar)
        track_uris_pool.extend(selecao_uris)
        print(f"  + {len(selecao_uris)} URIs aleatórias de '{artist['name']}'")

    # --- 4. MONTAGEM FINAL COM 100 MÚSICAS GARANTIDAS ---
    # Etapa padrão de limpeza e persistência.
    print("\n" + "-" * 40)
    print(f"\n--- PASSO 4: Montando a playlist final ---")

    unique_uris = list(set(track_uris_pool))
    print(f"Total de {len(unique_uris)} URIs únicas coletadas.")

    # Corte final para atingir exatamente 100 faixas
    if len(unique_uris) < FINAL_PLAYLIST_SIZE:
        final_track_uris = unique_uris
    else:
        final_track_uris = get_random_sample(unique_uris, FINAL_PLAYLIST_SIZE)
    
    print(f"Tamanho final da playlist: {len(final_track_uris)} músicas.")

    # Persistência no Spotify
    playlist_id = create_playlist(NOVO_PLAYLIST_NAME)
    if playlist_id:
        add_tracks_to_playlist(playlist_id, final_track_uris)
        print("\n--- PASSO 5: Curtindo as músicas (uma por uma) ---")
        like_tracks_slowly(final_track_uris)
    
    print("\n--- PROCESSO FINALIZADO! ---")

if __name__ == "__main__":
    main()