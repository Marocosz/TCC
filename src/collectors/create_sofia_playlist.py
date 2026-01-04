# src/collectors/create_sofia_playlist.py

"""
================================================================================
MÓDULO DE GERAÇÃO DE PLAYLIST - PERSONA SOFIA (ALTERNATIVA / DESCOBERTA)
================================================================================

OBJETIVO DO ARQUIVO:
    Gerenciar a criação da playlist para o perfil "Sofia", focado em música 
    alternativa e descoberta de "Lado B". 
    
    FONTE DE DADOS:
    Lê o arquivo 'artistas_indie_dados.csv' gerado previamente.

RESPONSABILIDADES:
    1. Carregar lista de artistas do CSV 'indie'.
    2. Classificar esses artistas em dois grupos (Clusters): 
       - Populares (Top 50% de popularidade dentro da amostra).
       - Nicho (Bottom 50% de popularidade).
    3. Aplicar "Orçamento Ponderado":
       - Dar mais espaço (70%) para artistas de Nicho.
       - Dar menos espaço (30%) para artistas Populares.
    4. Aplicar "Filtro Anti-Hit" para artistas populares (ignorar as top 5 faixas).
    5. Explorar discografia completa (álbuns/singles) em vez de apenas Top Tracks.

COMUNICAÇÃO:
    - Entrada: data/raw/artistas_indie_dados.csv
    - Saída: Criação de playlist e likes na conta Spotify.
    - Dependências: Usa 'spotipy' intensivamente para navegação em álbuns.
================================================================================
"""

import random
import math
import sys
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# --- Configuração de Caminho para Importação de Módulos Locais ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
diretorio_src = os.path.dirname(diretorio_atual)
diretorio_raiz = os.path.dirname(diretorio_src)
sys.path.append(diretorio_src)

# Carrega variáveis de ambiente
load_dotenv(os.path.join(diretorio_raiz, '.env'))

from functions import (
    load_artists_from_csv,
    create_playlist,
    add_tracks_to_playlist,
    like_tracks_slowly,
    get_random_sample
)

# --- FUNÇÕES AUXILIARES ESPECÍFICAS DA PERSONA SOFIA ---

def get_artist_album_tracks_pure(sp_client, artist_id: str, limit_albums=5) -> list:
    """
    Busca faixas de álbuns e singles do artista, indo além das 'Top Tracks'.
    
    Regra de Negócio (Sofia):
        A persona Sofia busca "Lado B" e faixas não comerciais. Usar o endpoint
        padrão 'top-tracks' viciaria o resultado em hits. Esta função varre
        os álbuns para encontrar o catálogo profundo.
        
    Retorno:
        list: Lista de objetos de faixa completos (track objects) com 'uri' e 'popularity'.
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
        lista_ids = list(all_track_ids)
        for i in range(0, len(lista_ids), 50):
            batch_ids = lista_ids[i:i+50]
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
    print("--- PASSO 1: Carregando configurações da 'Curadoria Ponderada' (Sofia) ---")
    
    # Inicializa cliente Spotify Localmente (Para acesso à API de álbuns)
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-modify-public user-library-modify"))

    # Arquivo CSV Fonte
    CSV_FILE = r"C:\Users\marco\OneDrive\Documentos\projetos\TCC\data\raw\artistas_indie_dados.csv"
    NOVO_PLAYLIST_NAME = "Alternativa Pura (Input Sofia)"
    FINAL_PLAYLIST_SIZE = 100
    TARGET_INICIAL_DE_COLETA = 130 # Margem de segurança para deduplicação

    # Regra de Negócio: Definição dos Pesos (Orçamento)
    PROPORCAO_PLAYLIST_POR_TIER = {
        'populares': 0.3, # Apenas 30% para artistas mainstream
        'nicho': 0.7      # 70% focado em artistas desconhecidos/médios
    }
    print("-" * 40)

    # --- 2. COLETAR E CLASSIFICAR ARTISTAS (SEGMENTAÇÃO VIA CSV) ---
    # Analisa o CSV e divide os artistas em dois grupos baseados na mediana.
    print("\n--- PASSO 2: Coletando e classificando os artistas do CSV ---")
    
    try:
        # 1. Carregamento do CSV
        todos_os_artistas = load_artists_from_csv(CSV_FILE, limit=200)
        
        if not todos_os_artistas:
            print("ERRO CRÍTICO: CSV vazio ou não encontrado.")
            return

        # 2. Tratamento de Dados (Converter popularidade para int e extrair ID da URI se precisar)
        artistas_validos = []
        for a in todos_os_artistas:
            try:
                a['popularity'] = int(a.get('popularity', 0))
                # Garante que temos o ID para buscar álbuns
                if 'id' not in a or not a['id']:
                    if 'uri' in a:
                        a['id'] = a['uri'].split(':')[-1]
                
                if a.get('id'):
                    artistas_validos.append(a)
            except:
                continue

        # 3. Ordenação por Popularidade (Decrescente)
        artistas_validos.sort(key=lambda x: x['popularity'], reverse=True)
        
        # 4. Segmentação (50/50 da lista encontrada)
        # Quem está na metade de cima é "Popular" (relativamente), quem está embaixo é "Nicho"
        ponto_de_corte = len(artistas_validos) // 2
        artistas_populares = artistas_validos[:ponto_de_corte]
        artistas_nicho = artistas_validos[ponto_de_corte:]

        print(f"Total processado: {len(artistas_validos)} artistas.")
        print(f"Grupo Populares: {len(artistas_populares)} artistas (Média Pop: Alta)")
        print(f"Grupo Nicho: {len(artistas_nicho)} artistas (Média Pop: Baixa)")
        print("-" * 40)

    except Exception as e:
        print(f"ERRO: Não foi possível processar a base de dados. Erro: {e}")
        return

    # --- 3. COLETAR MÚSICAS COM LÓGICA PONDERADA ---
    # Aqui reside a lógica principal: Tratamento diferente para cada grupo de artistas.
    print("\n--- PASSO 3: Coletando músicas com a lógica Ponderada (Exploração de Álbuns) ---")
    
    track_uris_pool = []
    
    # GRUPO A: ARTISTAS POPULARES (Tratamento "Lado B")
    # Calcula quantas músicas pegar deste grupo (ex: 30% de 130 = ~39 músicas)
    orcamento_populares = int(TARGET_INICIAL_DE_COLETA * PROPORCAO_PLAYLIST_POR_TIER['populares'])
    distribuicao_populares = distribuir_musicas_entre_artistas(orcamento_populares, len(artistas_populares))
    
    print(f"\nProcessando artistas 'populares' (Orçamento: {orcamento_populares} músicas)...")
    
    for artist, total_a_pegar in zip(artistas_populares, distribuicao_populares):
        if total_a_pegar == 0: continue
        
        # Busca catálogo profundo (álbuns e singles)
        # Nota: Usamos o ID que garantimos no passo 2
        todas_as_faixas_obj = get_artist_album_tracks_pure(sp, artist['id'])
        
        # Ordena por popularidade da FAIXA (para identificar os hits)
        todas_as_faixas_obj.sort(key=lambda x: x.get('popularity', 0), reverse=True)
        
        # FILTRO ANTI-HIT: Ignora as 5 faixas mais populares encontradas nos álbuns
        # PROTEÇÃO: Se o artista tiver poucas músicas (ex: EP de 4 faixas), 
        # não aplicamos o corte para não zerar a lista e perder o artista.
        if len(todas_as_faixas_obj) > 5:
            pool_musicas = todas_as_faixas_obj[5:] # Pega só "Lado B"
        else:
            pool_musicas = todas_as_faixas_obj # Se tem poucas, usa o que tem (Fallback)
        
        # Extrai apenas as URIs para seleção
        uris_disponiveis = [track['uri'] for track in pool_musicas]
        
        # Garante que não pede mais do que existe
        selecao_uris = get_random_sample(uris_disponiveis, total_a_pegar)
        track_uris_pool.extend(selecao_uris)
        print(f"  + {len(selecao_uris)} URIs 'lado B' de '{artist['name']}'")

    # GRUPO B: ARTISTAS DE NICHO (Tratamento Livre)
    # Calcula o restante do orçamento (ex: ~91 músicas)
    orcamento_nicho = TARGET_INICIAL_DE_COLETA - orcamento_populares
    distribuicao_nicho = distribuir_musicas_entre_artistas(orcamento_nicho, len(artistas_nicho))
    
    print(f"\nProcessando artistas de 'nicho' (Orçamento: {orcamento_nicho} músicas)...")
    
    for artist, total_a_pegar in zip(artistas_nicho, distribuicao_nicho):
        if total_a_pegar == 0: continue
        
        # Busca catálogo profundo
        todas_as_faixas_obj = get_artist_album_tracks_pure(sp, artist['id'])
        
        # Sem filtro anti-hit: Para artistas de nicho, qualquer música é válida/descoberta
        pool_musicas = todas_as_faixas_obj 
        
        uris_disponiveis = [track['uri'] for track in pool_musicas]
        
        selecao_uris = get_random_sample(uris_disponiveis, total_a_pegar)
        track_uris_pool.extend(selecao_uris)
        print(f"  + {len(selecao_uris)} URIs aleatórias de '{artist['name']}'")

    # --- 4. MONTAGEM FINAL COM 100 MÚSICAS GARANTIDAS ---
    # Etapa padrão de limpeza e persistência.
    print("\n" + "-" * 40)
    print(f"\n--- PASSO 4: Montando a playlist final ---")

    unique_uris = list(set(track_uris_pool))
    print(f"Total de {len(unique_uris)} URIs únicas coletadas.")

    # Corte final para atingir exatamente 100 faixas
    if len(unique_uris) < FINAL_PLAYLIST_SIZE:
        print(f"AVISO: Total ({len(unique_uris)}) menor que a meta. Usando todas.")
        final_track_uris = unique_uris
    else:
        final_track_uris = get_random_sample(unique_uris, FINAL_PLAYLIST_SIZE)
    
    print(f"Tamanho final da playlist: {len(final_track_uris)} músicas.")

    # Persistência no Spotify
    # Verifica se a lista não está vazia
    if not final_track_uris:
        print("ERRO: Nenhuma música selecionada.")
        return

    playlist_id = create_playlist(NOVO_PLAYLIST_NAME)
    if playlist_id:
        add_tracks_to_playlist(playlist_id, final_track_uris)
        print("\n--- PASSO 5: Curtindo as músicas (uma por uma) ---")
        like_tracks_slowly(final_track_uris)
    
    print("\n--- PROCESSO FINALIZADO! ---")

if __name__ == "__main__":
    main()