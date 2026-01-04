# src/functions.py

"""
================================================================================
MÓDULO DE UTILITÁRIOS E INTEGRAÇÃO COM SPOTIFY API
================================================================================

OBJETIVO DO ARQUIVO:
    Atuar como a camada de infraestrutura e serviço do projeto. Este arquivo
    centraliza todas as comunicações com a API do Spotify, abstraindo a
    complexidade de autenticação, paginação e tratamento de erros.

RESPONSABILIDADES:
    1. Autenticação (OAuth 2.0 e Client Credentials).
    2. Manipulação de Playlists (Criar, Adicionar, Ler).
    3. Gestão de Biblioteca do Usuário (Curtir/Descurtir músicas).
    4. Mineração de Dados (Extrair artistas, discografias e metadados).
    5. Persistência (Salvar e carregar dados em CSV).

INTEGRAÇÕES:
    - Utiliza a biblioteca `spotipy` como wrapper da Web API do Spotify.
    - É consumido pelos scripts "Collectors" (ex: gerador_playlists_mestre.py)
      e pelos scripts de Análise (ex: build_persona_raw_data.py).

================================================================================
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from dotenv import load_dotenv
import unicodedata
import csv
import random
import os
import io
import time
import requests

# Inicialização de variáveis de ambiente (carrega CLIENT_ID e CLIENT_SECRET)
load_dotenv()


# ==============================================================================
# SEÇÃO 1: GERENCIAMENTO DE PLAYLISTS E BIBLIOTECA (Escopo de Usuário)
# ------------------------------------------------------------------------------
# Estas funções exigem interação com o navegador para login do usuário, pois
# modificam dados privados (criar playlists, dar like em músicas).
# ==============================================================================

def create_playlist(playlist_name: str, public: bool = True) -> str:
    """
    Cria uma playlist vazia na conta do usuário logado.

    Contexto:
        Chamada no início do processo de geração de playlists para as Personas.
        Necessita do escopo de modificação de playlist.

    Args:
        playlist_name (str): Nome de exibição da playlist.
        public (bool): Se a playlist será visível no perfil (Default: True).

    Returns:
        str: O 'Spotify ID' da nova playlist (usado para adicionar músicas depois).
    """
    # Define escopos para permitir escrita em playlists públicas e privadas
    scope = "playlist-modify-public playlist-modify-private"
    
    # Inicializa o cliente autenticado (dispara o fluxo OAuth no browser se necessário)
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    
    # Obtém o ID do usuário atual para vincular a playlist a ele
    user_id = sp_user.current_user()["id"]
    
    # Executa a criação na API
    playlist = sp_user.user_playlist_create(user=user_id, name=playlist_name, public=public)
    
    print(f"Playlist '{playlist_name}' criada com sucesso.")
    
    # Retorna apenas o ID, que é o dado essencial para os próximos passos
    return playlist["id"]


def add_tracks_to_playlist(playlist_id: str, track_uris: list) -> None:
    """
    Adiciona faixas a uma playlist existente, respeitando os limites da API.

    Regra de Negócio / Limitação da API:
        O endpoint de adicionar faixas do Spotify aceita no MÁXIMO 100 URIs
        por requisição. Esta função implementa a lógica de lote (batching)
        para contornar essa limitação.

    Args:
        playlist_id (str): ID da playlist alvo.
        track_uris (list): Lista de strings contendo URIs do Spotify (ex: 'spotify:track:xyz').
    """
    scope = "playlist-modify-public playlist-modify-private"
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

    # Loop de processamento em lotes (Batch Processing)
    # Itera sobre a lista de 100 em 100 itens
    for i in range(0, len(track_uris), 100):
        # Fatia a lista principal para criar o sub-lote atual
        batch = track_uris[i:i + 100]
        
        # Envia o lote atual para a API
        sp_user.playlist_add_items(playlist_id, batch)
        print(f"Adicionado um lote de {len(batch)} músicas à playlist.")
    
    print("Todas as músicas foram adicionadas.")


def like_tracks(track_uris: list) -> None:
    """
    Salva músicas na biblioteca do usuário ("Músicas Curtidas") de forma otimizada.

    Estratégia de Otimização:
        Antes de tentar salvar, a função verifica quais músicas JÁ estão salvas.
        Isso evita chamadas de escrita redundantes e mantém o processo mais limpo.

    Args:
        track_uris (list): Lista de URIs para curtir.
    """
    if not track_uris:
        print("Nenhuma URI de música fornecida para curtir.")
        return
        
    # Escopos necessários: Ler biblioteca (verificar) e Modificar biblioteca (curtir)
    scope = "user-library-read user-library-modify"
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    
    print(f"--- Processando {len(track_uris)} músicas para curtir... ---")

    new_likes_count = 0
    
    # Batching: A API de 'User Library' limita operações a 50 itens por vez
    for i in range(0, len(track_uris), 50):
        batch = track_uris[i:i + 50]
        try:
            # Passo 1: Verificação (Read)
            # Retorna uma lista de booleanos [True, False, True...] correspondente ao lote
            is_already_liked = sp_user.current_user_saved_tracks_contains(tracks=batch)
            
            # Passo 2: Filtragem
            # Mantém apenas as URIs que retornaram False (não curtidas)
            tracks_to_like = [uri for uri, liked in zip(batch, is_already_liked) if not liked]
            
            # Passo 3: Ação (Write) - Apenas se houver itens novos
            if tracks_to_like:
                sp_user.current_user_saved_tracks_add(tracks=tracks_to_like)
                new_likes_count += len(tracks_to_like)
                print(f"Adicionado 'like' a {len(tracks_to_like)} novas músicas neste lote.")
            else:
                print("Nenhuma música nova para curtir neste lote (todas já estavam na biblioteca).")
        except Exception as e:
            print(f"Ocorreu um erro ao processar um lote: {e}")
            
    print(f"\n--- Processo finalizado! Total de {new_likes_count} novas músicas foram curtidas. ---")


def like_tracks_slowly(track_uris: list) -> None:
    """
    Salva músicas uma por uma com atraso intencional (Throttling).

    Por que essa função existe?
        Em scripts que rodam por muito tempo ou processam muitas músicas,
        o método em lote (batch) pode sofrer com Rate Limiting (Erro 429)
        ou timeouts. Esta abordagem é mais lenta, mas extremamente robusta
        para garantir que todas as músicas sejam processadas sem erros.

    Args:
        track_uris (list): Lista de URIs.
    """
    if not track_uris:
        print("Nenhuma URI de música fornecida para curtir.")
        return
        
    scope = "user-library-read user-library-modify"
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    
    print(f"--- Iniciando processo para curtir {len(track_uris)} músicas (uma por uma)... ---")

    new_likes_count = 0
    for i, uri in enumerate(track_uris):
        try:
            # Verifica individualmente
            is_already_liked = sp_user.current_user_saved_tracks_contains(tracks=[uri])[0]

            if not is_already_liked:
                sp_user.current_user_saved_tracks_add(tracks=[uri])
                print(f"  ({i+1}/{len(track_uris)}) ✅ Curtido: {uri}")
                new_likes_count += 1
            else:
                print(f"  ({i+1}/{len(track_uris)}) ⏭️ Já estava curtida: {uri}")

            # Throttling: Pausa de 200ms para evitar sobrecarregar a API
            time.sleep(0.2)

        except Exception as e:
            # Em caso de erro em uma música, o script não para, apenas loga e continua
            print(f"  ({i+1}/{len(track_uris)}) ❌ Erro ao curtir a música {uri}: {e}")
            
    print(f"\n--- Processo finalizado! Total de {new_likes_count} novas músicas foram curtidas. ---")


def like_all_tracks_in_playlist(playlist_id: str) -> None:
    """
    Transfere todas as músicas de uma Playlist específica para a Biblioteca do Usuário.

    Uso no Projeto:
        Pode ser usada para analisar playlists automáticas do Spotify (ex: Descobertas da Semana)
        e salvar as recomendações para análise posterior de permanência na biblioteca.
    """
    scope = "user-library-read user-library-modify playlist-read-private"
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    print(f"--- Iniciando processo para curtir músicas da playlist ID: {playlist_id} ---")

    # --- FASE 1: Coleta Completa (Paginação) ---
    track_uris = []
    results = sp_user.playlist_tracks(playlist_id)
    
    # Itera sobre todas as páginas de resultados da playlist
    while results:
        for item in results['items']:
            # Validação: Garante que o item é uma faixa válida e tem URI
            if item.get('track') and item['track'].get('uri'):
                track_uris.append(item['track']['uri'])
        
        # Avança para a próxima página, se existir
        results = sp_user.next(results) if results['next'] else None

    if not track_uris:
        print("Nenhuma música encontrada na playlist.")
        return

    # --- FASE 2: Processamento de Likes (Lógica de Lote) ---
    print(f"Encontradas {len(track_uris)} músicas. Verificando e curtindo em lotes...")
    new_likes_count = 0
    
    # Processa em blocos de 50 (limite da API)
    for i in range(0, len(track_uris), 50):
        batch = track_uris[i:i + 50]
        try:
            # Verifica estado atual
            is_already_liked = sp_user.current_user_saved_tracks_contains(tracks=batch)
            
            # Filtra apenas não curtidas
            tracks_to_like = [uri for uri, liked in zip(batch, is_already_liked) if not liked]
            
            if tracks_to_like:
                sp_user.current_user_saved_tracks_add(tracks=tracks_to_like)
                new_likes_count += len(tracks_to_like)
                print(f"Adicionado 'like' a {len(tracks_to_like)} novas músicas neste lote.")
            else:
                print("Nenhuma música nova para curtir neste lote (todas já estavam na biblioteca).")
        except Exception as e:
            print(f"Ocorreu um erro ao processar um lote para curtir músicas: {e}")
            
    print(f"\n--- Processo finalizado! Total de {new_likes_count} novas músicas foram curtidas. ---")


def unlike_all_tracks_in_playlist(playlist_id: str) -> None:
    """
    Remove da biblioteca do usuário as músicas que pertencem a uma playlist específica.
    Funciona como o inverso de 'like_all_tracks_in_playlist'.
    """
    scope = "user-library-read user-library-modify playlist-read-private"
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    print(f"--- Iniciando processo para remover likes da playlist ID: {playlist_id} ---")

    # --- FASE 1: Coleta (Igual à função de Like) ---
    track_uris = []
    results = sp_user.playlist_tracks(playlist_id)
    while results:
        for item in results['items']:
            if item.get('track') and item['track'].get('uri'):
                track_uris.append(item['track']['uri'])
        results = sp_user.next(results) if results['next'] else None

    if not track_uris:
        print("Nenhuma música encontrada na playlist.")
        return

    # --- FASE 2: Remoção (Lógica Inversa) ---
    print(f"Encontradas {len(track_uris)} músicas. Verificando e removendo 'likes' em lotes...")
    unliked_count = 0
    
    for i in range(0, len(track_uris), 50):
        batch = track_uris[i:i + 50]
        try:
            # Verifica se ESTÁ curtida (True)
            is_currently_liked = sp_user.current_user_saved_tracks_contains(tracks=batch)
            
            # Filtra para remover apenas as que ESTÃO curtidas
            tracks_to_unlike = [uri for uri, liked in zip(batch, is_currently_liked) if liked]

            if tracks_to_unlike:
                sp_user.current_user_saved_tracks_delete(tracks=tracks_to_unlike)
                unliked_count += len(tracks_to_unlike)
                print(f"Removido o 'like' de {len(tracks_to_unlike)} músicas neste lote.")
            else:
                print("Nenhuma música para descurtir neste lote (nenhuma estava na biblioteca).")
        except Exception as e:
            print(f"Ocorreu um erro ao processar um lote para remoção de likes: {e}")
            
    print(f"\n--- Processo finalizado! Total de {unliked_count} 'likes' foram removidos. ---")
    
    
def unlike_all_saved_tracks() -> None:
    """
    Limpa completamente a biblioteca de "Músicas Curtidas" do usuário.

    ALERTA DE SEGURANÇA:
        Esta é uma função destrutiva. Inclui um mecanismo de confirmação manual
        (input) para impedir execução acidental, já que a ação não pode ser desfeita.
    """
    scope = "user-library-read user-library-modify"
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

    # --- PASSO 1: Coleta de TODO o acervo (Pode ser demorado) ---
    print("Iniciando busca de todas as suas Músicas Curtidas. Isso pode demorar se a sua biblioteca for grande...")
    
    all_track_uris = []
    # Busca inicial com limite de 50
    results = sp_user.current_user_saved_tracks(limit=50)
    
    # Paginação para varrer a biblioteca inteira
    while results:
        for item in results['items']:
            if item.get('track') and item['track'].get('uri'):
                all_track_uris.append(item['track']['uri'])
        
        # Feedback visual de progresso
        print(f"Progresso: {len(all_track_uris)} músicas encontradas...")
        
        results = sp_user.next(results) if results['next'] else None

    if not all_track_uris:
        print("\nVocê não tem nenhuma música curtida na sua biblioteca.")
        return

    # --- PASSO 2: Mecanismo de Segurança (Confirmação) ---
    total_songs = len(all_track_uris)
    print(f"\nBusca finalizada. Total de {total_songs} músicas encontradas na sua biblioteca.")
    
    print("\n" + "="*60)
    print("AVISO: VOCÊ ESTÁ PRESTES A REMOVER TODAS AS SUAS MÚSICAS CURTIDAS! ⚠️")
    print("ESTA AÇÃO É PERMANENTE E IRREVERSÍVEL.")
    print("="*60)
    
    confirmation_phrase = "EU QUERO APAGAR TUDO"
    user_input = input(f"Para confirmar, digite a frase exata '{confirmation_phrase}': ")

    # Aborta se a frase não for exata
    if user_input != confirmation_phrase:
        print("\nConfirmação incorreta. Operação cancelada. Nenhum like foi removido.")
        return

    # --- PASSO 3: Exclusão em Massa (Lotes) ---
    print("\nConfirmação recebida. Iniciando a remoção dos likes em lotes...")
    
    total_batches = (total_songs + 49) // 50
    
    for i in range(0, total_songs, 50):
        batch = all_track_uris[i:i + 50]
        try:
            sp_user.current_user_saved_tracks_delete(tracks=batch)
            print(f"Lote {i//50 + 1}/{total_batches}: Like de {len(batch)} músicas foi removido.")
            # Pausa de segurança para não saturar a API durante deleção massiva
            time.sleep(0.5) 
        except Exception as e:
            print(f"Ocorreu um erro ao processar o lote {i//50 + 1}: {e}")
            
    print("\n--- PROCESSO DE EXCLUSÃO FINALIZADO! ---")
    print("Todas as músicas foram removidas da sua biblioteca de 'Músicas Curtidas'.")
    
    
def audit_playlist_liked_status(playlist_id: str) -> None:
    """
    Ferramenta de Diagnóstico (Read-Only).
    Verifica quais músicas de uma playlist o usuário NÃO curtiu ainda.

    Útil para:
        Validar se os scripts de sincronização (like_tracks) funcionaram corretamente
        sem alterar nenhum dado.
    """
    scope = "user-library-read playlist-read-private"
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

    # Coleta todas as músicas da playlist
    playlist_tracks = []
    results = sp_user.playlist_tracks(playlist_id)
    
    while results:
        for item in results['items']:
            if item.get('track') and item['track'].get('uri'):
                # Armazena nome para relatório legível e URI para verificação
                playlist_tracks.append({'name': item['track']['name'], 'uri': item['track']['uri']})
        results = sp_user.next(results) if results['next'] else None

    if not playlist_tracks:
        print("Playlist não encontrada ou está vazia.")
        return

    print(f"--- Auditando {len(playlist_tracks)} músicas da playlist ---")
    
    not_liked_tracks = []
    # Verifica status em lotes de 50
    for i in range(0, len(playlist_tracks), 50):
        batch = playlist_tracks[i:i + 50]
        batch_uris = [track['uri'] for track in batch]
        
        try:
            # Consulta API: Retorna lista de booleanos
            liked_status_list = sp_user.current_user_saved_tracks_contains(tracks=batch_uris)
            
            # Cruzamento de dados: Se False, adiciona à lista de discrepâncias
            for track_info, is_liked in zip(batch, liked_status_list):
                if not is_liked:
                    not_liked_tracks.append(track_info['name'])
        except Exception as e:
            print(f"Ocorreu um erro ao auditar um lote: {e}")
    
    print("\n--- Relatório Final da Auditoria ---")
    if not not_liked_tracks:
        print("✅ CONFIRMADO: A API do Spotify reporta que TODAS as músicas desta playlist estão salvas.")
    else:
        print(f"🚨 ALERTA: A API reporta que {len(not_liked_tracks)} músicas NÃO estão salvas:")
        for name in not_liked_tracks:
            print(f"  - {name}")


# ==============================================================================
# SEÇÃO 2: EXTRAÇÃO DE DADOS DO CATÁLOGO (Client Credentials)
# ------------------------------------------------------------------------------
# Estas funções NÃO exigem login de usuário. Elas acessam dados públicos do
# Spotify (artistas, álbuns, metadados) usando apenas Credenciais de Cliente.
# São ideais para mineração de dados em larga escala.
# ==============================================================================

def get_artists_from_playlist(playlist_id: str) -> dict:
    """
    Extrai todos os artistas únicos presentes em uma playlist.

    Estratégia:
        Varre todas as faixas da playlist e compila um dicionário de artistas.
        Usa dicionário (hash map) para garantir unicidade automaticamente.

    Returns:
        dict: { 'artist_id': 'artist_name', ... }
    """
    # Inicializa cliente "App" (apenas leitura pública)
    sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    print("Buscando músicas da playlist para extrair artistas...")
    
    unique_artists = {}
    
    # Coleta paginada de itens da playlist
    results = sp_app.playlist_items(playlist_id)
    playlist_items = results['items']
    while results['next']:
        results = sp_app.next(results)
        playlist_items.extend(results['items'])

    # Processamento dos itens para extração
    for item in playlist_items:
        if item.get("track") and item['track'].get('artists'):
            for artist in item["track"]["artists"]:
                # Adiciona ao dicionário se o ID ainda não existe
                if artist['id'] not in unique_artists:
                    unique_artists[artist['id']] = artist['name']
    
    print(f"Encontrados {len(unique_artists)} artistas únicos na playlist.")
    return unique_artists


def get_full_artist_profiles(artists_dict: dict) -> list:
    """
    Enriquece uma lista simples de artistas com metadados profundos.

    Dados coletados:
        - Popularidade (0-100)
        - Gêneros musicais associados
        - Número de seguidores
        - Top Tracks (Músicas mais famosas no Brasil)

    Performance:
        - Busca detalhes de artistas em lotes de 50 (Rápido).
        - Busca Top Tracks individualmente por artista (Lento - Limitação da API).

    Args:
        artists_dict (dict): Dicionário {id: nome} vindo de get_artists_from_playlist.

    Returns:
        list: Lista de dicionários com perfil completo dos artistas.
    """
    sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    print("Buscando detalhes dos perfis dos artistas...")
    
    artist_ids = list(artists_dict.keys())
    artist_profiles = []
    
    # Loop em lotes de 50 para o endpoint 'artists' (detalhes gerais)
    for i in range(0, len(artist_ids), 50):
        batch_ids = artist_ids[i:i + 50]
        try:
            # Chamada em lote otimizada
            artists_details = sp_app.artists(batch_ids)
            
            # Para cada artista detalhado, busca suas Top Tracks
            for artist_data in artists_details['artists']:
                # Chamada individual (Gargalo de performance aceitável para o escopo)
                top_tracks_result = sp_app.artist_top_tracks(artist_data['id'], country="BR")
                
                # Compilação do objeto final
                artist_profiles.append({
                    "id": artist_data['id'], # GARANTE QUE O ID SEJA SALVO NO CSV
                    "name": artist_data['name'], 
                    "uri": artist_data['uri'],
                    "followers": artist_data['followers']['total'], 
                    "genres": artist_data['genres'],
                    "popularity": artist_data['popularity'],
                    # Extrai apenas os nomes das faixas top
                    "top_tracks": [track['name'] for track in top_tracks_result["tracks"]]
                })
                print(f"  - Perfil de '{artist_data['name']}' obtido com sucesso.")
        except Exception as e:
            print(f"Ocorreu um erro ao buscar um lote de artistas: {e}")
            continue

    print("Todos os perfis de artistas foram obtidos.")
    return artist_profiles


def fetch_artist_discography(artist_name: str) -> dict:
    """
    Busca todos os álbuns de estúdio de um artista e lista suas faixas.

    Funcionalidades:
        - Busca o ID do artista pelo nome.
        - Filtra apenas lançamentos do tipo 'album' (ignora singles/compilações).
        - Normaliza nomes para remover duplicatas (ex: remove versões Deluxe repetidas).

    Returns:
        dict: { 'Nome do Álbum': ['Faixa 1', 'Faixa 2', ...], ... }
    """
    sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    
    # Passo 1: Resolver nome -> ID
    search_result = sp_app.search(q=f'artist:{artist_name}', type='artist', limit=1)
    if not search_result['artists']['items']:
        print(f"Artista '{artist_name}' não encontrado.")
        return {}
    
    artist = search_result['artists']['items'][0]
    artist_id = artist['id']
    print(f"Artista encontrado: '{artist['name']}' (ID: {artist_id})")

    # Passo 2: Buscar Álbuns (Paginado)
    all_album_releases = []
    results = sp_app.artist_albums(artist_id, album_type='album', limit=50)
    all_album_releases.extend(results['items'])
    while results['next']:
        results = sp_app.next(results)
        all_album_releases.extend(results['items'])
    
    # Passo 3: Filtragem de Duplicatas (Lógica de Normalização)
    unique_albums = []
    seen_album_names = set()
    for album in all_album_releases:
        # Usa função auxiliar para limpar "Deluxe", "Remaster", etc.
        normalized_name = normalize_album_name(album['name'])
        if normalized_name not in seen_album_names:
            seen_album_names.add(normalized_name)
            unique_albums.append(album)
    
    print(f"\nEncontrados {len(unique_albums)} álbuns de estúdio únicos para processar.")

    # Passo 4: Buscar Faixas de cada álbum
    artist_discography = {}
    for i, album in enumerate(unique_albums):
        print(f"Buscando faixas de '{album['name']}' ({i+1}/{len(unique_albums)})...")
        try:
            track_results = sp_app.album_tracks(album['id'], limit=50)
            tracks = track_results['items']
            while track_results['next']:
                track_results = sp_app.next(track_results)
                tracks.extend(track_results['items'])
            
            artist_discography[album['name']] = [track['name'] for track in tracks]
        except Exception as e:
            print(f"Não foi possível buscar faixas do álbum {album['id']}. Motivo: {e}")
            continue
            
    return artist_discography


def fetch_track_uris(track_names: list) -> list:
    """
    Converte uma lista de Nomes de Músicas em URIs do Spotify.
    
    Mecanismo:
        Realiza uma busca (Search) para cada nome e pega o primeiro resultado.
        
    Limitação:
        Pode haver imprecisão se existirem muitas músicas com o mesmo nome.
        Depende da relevância da busca do Spotify.

    Args:
        track_names (list): Lista de strings com nomes das faixas.

    Returns:
        list: Lista de URIs encontradas.
    """
    sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    found_uris = []
    print(f"Buscando URIs para {len(track_names)} músicas...")
    
    for name in track_names:
        if not name.strip(): continue
        try:
            # Busca simples pelo nome da faixa
            results = sp_app.search(q=name, type='track', limit=1)
            if results and results['tracks']['items']:
                found_uris.append(results['tracks']['items'][0]['uri'])
        except spotipy.exceptions.SpotifyException:
            pass 
        
        # Pausa leve para evitar sobrecarga (Rate Limit) na API de busca
        time.sleep(0.05)
            
    print(f"Encontradas {len(found_uris)} URIs.")
    return found_uris


# ==============================================================================
# SEÇÃO 3: PERSISTÊNCIA E DADOS (CSV)
# ------------------------------------------------------------------------------
# Funções auxiliares para salvar e carregar dados estruturados, permitindo
# que o projeto funcione em etapas sem perder o estado.
# ==============================================================================

def save_artists_to_csv(artists_data: list, filename: str, sort_by: str = 'popularity'):
    """
    Salva a lista de dicionários de artistas em um arquivo CSV.
    Inclui o campo 'id' para garantir compatibilidade futura.
    """
    if not artists_data:
        print("Nenhum dado de artista para salvar.")
        return

    print(f"Ordenando artistas por '{sort_by}' e preparando para salvar...")
    
    # Ordenação decrescente (do maior para o menor) baseada no campo escolhido
    sorted_artists = sorted(artists_data, key=lambda item: item.get(sort_by, 0), reverse=True)
    
    # ADICIONADO 'id' AOS HEADERS
    csv_headers = ["name", "id", "uri", "followers", "genres", "popularity", "top_tracks"]
    
    try:
        # Garante que a pasta existe antes de salvar
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=csv_headers)
            writer.writeheader()
            
            for artist_info in sorted_artists:
                # Cria cópia para não modificar o objeto original na memória
                row_data = artist_info.copy()
                
                # Serialização de listas para string (CSV friendly)
                if isinstance(row_data.get("genres"), list):
                    row_data["genres"] = "; ".join(row_data["genres"])
                if isinstance(row_data.get("top_tracks"), list):
                    row_data["top_tracks"] = "; ".join(row_data["top_tracks"])
                
                writer.writerow(row_data)
        print(f"Arquivo '{filename}' salvo com sucesso!")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar o arquivo CSV: {e}")


# ==============================================================================
# SEÇÃO 4: FUNÇÕES UTILITÁRIAS GERAIS
# ------------------------------------------------------------------------------
# Helpers para manipulação de strings, listas e leitura de arquivos.
# ==============================================================================

def load_artists_from_csv(file_path: str, limit: int) -> list:
    """
    Lê o CSV gerado por 'save_artists_to_csv' e reconstrói as estruturas de dados.
    Faz o processo inverso (String -> Lista) para gêneros e faixas.
    """
    selected_artists = []
    try:
        with io.open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for i, row in enumerate(reader):
                if i >= limit: break
                
                # Deserialização: String "rock; pop" -> Lista ["rock", "pop"]
                row['top_tracks'] = [track.strip() for track in row.get('top_tracks', '').split(';') if track.strip()]
                row['genres'] = [genre.strip() for genre in row.get('genres', '').split(';') if genre.strip()]
                
                selected_artists.append(row)
    except FileNotFoundError:
        print(f"Erro: O arquivo no caminho {file_path} não foi encontrado.")
        return []
    return selected_artists


def extract_top_tracks_from_data(artist_data: dict) -> list:
    """
    Busca as Top Tracks reais na API do Spotify usando o ID do artista.
    
    CORREÇÃO DE SEGURANÇA:
    Se o CSV for antigo e não tiver a coluna 'id', esta função tenta extrair
    o ID diretamente da coluna 'uri' (ex: 'spotify:artist:12345' -> '12345').
    """
    # Tenta pegar ID normal
    artist_id = artist_data.get('id')
    artist_name = artist_data.get('name', 'Desconhecido')
    
    # Se não tiver ID mas tiver URI, extrai o ID da URI
    if not artist_id and 'uri' in artist_data:
        try:
            # Ex: spotify:artist:4Z8W4fKeB5YxbusRsdQVPb -> split(':') -> pega o último
            artist_id = artist_data['uri'].split(':')[-1]
        except:
            pass # Falha silenciosa, retornará lista vazia abaixo
    
    if not artist_id:
        return []
    
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    
    try:
        # Busca as top tracks (Market='BR' garante músicas disponíveis aqui)
        results = sp.artist_top_tracks(artist_id, country='BR')
        # Retorna a lista completa de objetos (com URI, Name, Popularity, etc)
        return results.get('tracks', [])
    except Exception as e:
        print(f"Erro em functions.py ao buscar tracks de '{artist_name}': {e}")
        return []


def flatten_list_of_lists(list_of_lists: list) -> list:
    """
    Utilitário para transformar matrizes (lista de listas) em uma lista plana.
    Ex: [[1, 2], [3, 4]] -> [1, 2, 3, 4]
    """
    return [item for sublist in list_of_lists for item in sublist]


def get_random_sample(items: list, count: int) -> list:
    """
    Retorna uma amostragem aleatória segura.
    
    Proteção:
        Se 'count' for maior que o tamanho da lista, retorna a lista inteira
        em vez de gerar erro.
    """
    sample_size = min(len(items), count)
    return random.sample(items, sample_size)


def extract_spotify_playlist_id(url: str) -> str:
    """
    Limpa e extrai o ID de uma URL de playlist do Spotify.
    Remove parâmetros de query (como '?si=...') e barras extras.
    """
    clean_url = url.split('?', 1)[0]
    return clean_url.rstrip('/').split('/')[-1]


def normalize_album_name(name: str) -> str:
    """
    Padroniza nomes de álbuns para detecção de duplicatas.
    
    Lógica:
        - Remove acentos (NFKD).
        - Converte para minúsculas.
        - Remove termos comuns de edições especiais que não alteram a obra principal
          (ex: Deluxe Edition, Remastered).
    """
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('utf-8')
    name = name.lower()
    common_terms = ['(deluxe edition)', '(remastered)', '(remaster)', '(special edition)', '(ao vivo)', '(live)']
    
    for term in common_terms:
        name = name.replace(term, '')
    
    return name.strip()

def search_artists_by_genre(genre: str, limit: int = 20) -> list:
    """
    Busca artistas baseados em tags de gênero (ex: "indie pop").
    Útil para descobrir novos artistas fora das playlists semente.
    """
    sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    
    print(f"Buscando os {limit} artistas mais relevantes para o gênero '{genre}'...")
    
    # Sintaxe de busca específica do Spotify para gêneros
    query = f'genre:"{genre}"'
    
    try:
        results = sp_app.search(q=query, type='artist', limit=limit, market='BR')
        artists_found = results['artists']['items']
        
        if not artists_found:
            print(f"Nenhum artista encontrado para o gênero '{genre}'.")
            return []
            
        processed_artists = []
        for artist_data in artists_found:
            processed_artists.append({
                "name": artist_data['name'],
                "uri": artist_data['uri'],
                "followers": artist_data['followers']['total'],
                "genres": artist_data['genres'],
                "popularity": artist_data['popularity']
            })
        
        print(f"Busca finalizada. Encontrados {len(processed_artists)} artistas.")
        return processed_artists

    except Exception as e:
        print(f"Ocorreu um erro durante a busca por gênero: {e}")
        return []