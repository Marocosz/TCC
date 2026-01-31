# src/functions.py

"""
================================================================================
MÓDULO DE UTILITÁRIOS E INTEGRAÇÃO COM SPOTIFY API
================================================================================

Objetivo do Arquivo:
    Atuar como a camada de infraestrutura e serviço do projeto. Este arquivo
    centraliza todas as comunicações com a API do Spotify, abstraindo a
    complexidade de autenticação, paginação e tratamento de erros.

Parte do Sistema:
    Backend / Integração Externa (Core Service).

Responsabilidades:
    1. Autenticação: Gerenciar OAuth 2.0 (usuário) e Client Credentials (app).
    2. Manipulação de Playlists: Criar, adicionar faixas e ler metadados.
    3. Gestão de Biblioteca: Adicionar/Remover 'likes' (Curtidas) em faixas.
    4. Mineração de Dados: Extrair discografias, perfis de artistas e top tracks.
    5. Persistência: Utilitários para salvar e carregar dados em CSV.

Comunicação:
    - Externa: API do Spotify (via biblioteca `spotipy`).
    - Interna: Importado por todos os scripts 'collectors' e 'analysis'.
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
    Cria uma nova playlist vazia na conta do usuário autenticado.

    O que faz:
        Autentica o usuário e solicita a criação de um recurso de playlist na API.
    
    Por que existe:
        É o primeiro passo para a montagem dos datasets/playlists das Personas.
        Sem criar o "container" (playlist), não podemos adicionar músicas.

    Quando é chamada:
        Pelos scripts collectors (ex: create_beatriz_playlist.py) logo após
        a seleção das faixas a serem adicionadas.

    Args:
        playlist_name (str): Título que aparecerá no Spotify.
        public (bool): Define a visibilidade (Pública/Privada).

    Returns:
        str: O ID único da playlist criada (ex: '3ZNXMWlJdHsrtYvla53nVA').
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
    Adiciona faixas a uma playlist existente em lotes (Batching).

    O que faz:
        Recebe uma lista longa de URIs e as envia para a playlist em grupos de 100.

    Por que existe:
        A API do Spotify limita a adição de faixas a 100 itens por requisição.
        Esta função abstrai essa complexidade dividindo automaticamente listas
        maiores em sub-lotes aceitáveis.

    Quando é chamada:
        Logo após `create_playlist`, para popular a playlist com as músicas selecionadas.

    Args:
        playlist_id (str): ID da playlist alvo.
        track_uris (list): Lista de strings com URIs (ex: ['spotify:track:xyz', ...]).
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
    Salva músicas na biblioteca "Músicas Curtidas" do usuário de forma otimizada.

    O que faz:
        Verifica quais músicas da lista já estão curtidas e adiciona apenas as novas.

    Por que existe:
        Para simular o "feedback explícito" da Persona. Ao curtir as músicas,
        damos sinais claros ao algoritmo do Spotify sobre as preferências do perfil.

    Regra de Otimização (Check-before-Write):
        Verifica se a música JÁ está curtida antes de tentar curtir novamente.
        Isso economiza requisições de escrita e evita erros redundantes.

    Args:
        track_uris (list): Lista de URIs para adicionar à biblioteca.
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
    Salva músicas individualmente com um atraso intencional (Throttling).

    O que faz:
        Processa uma a uma, verificando e curtindo, com pausa de 0.2s.

    Por que existe:
        Em operações longas ou massivas, o envio em lote pode disparar proteções
        de Rate Limit (Erro 429) do Spotify. Esta função prioriza a **robustez**
        sobre a velocidade, garantindo que todas as faixas sejam processadas.

    Quando usar:
        - Scripts de criação de playlist muito grandes (>500 músicas).
        - Ambientes onde a latência de rede é instável.

    Args:
        track_uris (list): Lista de URIs para processar.
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
    Copia todas as músicas de uma playlist externa para a Biblioteca do Usuário.

    O que faz:
        1. Lê todas as faixas da playlist alvo (paginado).
        2. Verifica quais ainda não estão salvas na biblioteca.
        3. Salva apenas as novas (Rate Limit friendly).

    Quando usar:
        Útil para capturar o estado de playlists dinâmicas (ex: Descobertas da Semana)
        antes que elas mudem, salvando tudo na biblioteca para análise posterior.

    Args:
        playlist_id (str): ID da playlist fonte.
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
    Remove da biblioteca do usuário todas as músicas presentes em uma determinada playlist.

    O que faz:
        Atua como uma "borracha seletiva". Remove o 'like' apenas das faixas
        que correspondem à playlist informada, mantendo o resto da biblioteca intacto.

    Args:
        playlist_id (str): ID da playlist de referência para remoção.
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
    Apaga TODAS as músicas da biblioteca de "Músicas Curtidas" (Reset Total).

    O que faz:
        Busca e remove todas as faixas do usuário.

    Perigo:
        - Ação destrutiva e irreversível.
        - Exige confirmação manual (input) no terminal para executar.

    Por que existe:
        Usada para "zerar" a conta de testes antes de aplicar uma nova Persona.
        Garante que o algoritmo de recomendação não seja influenciado por
        dados antigos de experimentos anteriores.
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
    Realiza uma auditoria de conformidade (Somente Leitura) na playlist.

    O que faz:
        Verifica música por música se ela está marcada como "Gostei" na biblioteca.
        Gera um relatório de discrepâncias no terminal.

    Por que existe:
        Para garantir a integridade do experimento. Se o script diz que "Beatriz gosta de X",
        precisamos confirmar se a conta realmente seguiu/curtiu X no Spotify.
        Detecta falhas silenciosas na API de Likes.

    Args:
        playlist_id (str): Playlist a ser auditada.
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
    Extrai a lista de artistas únicos presentes em uma playlist.

    O que faz:
        Baixa todas as faixas e usa um dicionário (Hash Map) para armazenar
        os artistas, garantindo automaticamente a unicidade (deduplicação)
        pela chave 'artist_id'.

    Args:
        playlist_id (str): ID da playlist a ser minerada.

    Returns:
        dict: Dicionário no formato { 'artist_id': 'artist_name', ... }.
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
    Enriquece uma lista de IDs de artistas com metadados detalhados da API.

    O que faz:
        1. Recebe IDs básicos ("quem são").
        2. Consulta a API para obter popularidade, gêneros e seguidores ("como são").
        3. Busca separadamente as "Top Tracks" de cada um ("o que tocam").

    Performance:
        - Detalhes (Popularidade/Gêneros): Busca em lotes de 50 (Muito Rápido).
        - Top Tracks: Busca individual por artista (Lento, mas necessário).

    Args:
        artists_dict (dict): Output da função `get_artists_from_playlist`.

    Returns:
        list: Lista de dicionários ricos, prontos para análise ou salvamento em CSV.
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
    Mapeia o catálogo completo (Álbuns de Estúdio) de um artista.

    O que faz:
        1. Busca o ID do artista pelo nome.
        2. Lista todos os álbuns (ignorando singles e compilações).
        3. Remove duplicatas (ex: versões Deluxe/Remaster) via normalização de string.
        4. Lista todas as faixas de cada álbum único encontrados.

    Args:
        artist_name (str): Nome do artista.

    Returns:
        dict: { 'Nome do Álbum': ['Faixa A', 'Faixa B'], ... }
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
    Converte nomes de músicas (texto) em URIs do Spotify (identificadores).

    O que faz:
        Realiza uma busca textual (`search`) na API para cada nome e retorna
        o primeiro resultado (mais relevante).

    Limitações:
        - Pode falhar se o nome for ambíguo.
        - Sujeita a Rate Limit mais agressivo que endpoints diretos.

    Args:
        track_names (list): Lista de nomes (ex: ["Bohemian Rhapsody", "Imagine"]).

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
    Persiste a lista de artistas enriquecida em um arquivo CSV.

    O que faz:
        - Ordena os dados conforme parâmetro.
        - Serializa campos complexos (listas) para strings.
        - Salva em disco criando pastas se necessário.

    Args:
        artists_data (list): Lista de dicionários (perfil completo).
        filename (str): Caminho absoluto de destino.
        sort_by (str): Campo chave para ordenação decrescente (Default: 'popularity').
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
                    # Desempacota lista
                    row_data["genres"] = "; ".join(row_data["genres"])
                if isinstance(row_data.get("top_tracks"), list):
                    row_data["top_tracks"] = "; ".join(row_data["top_tracks"])
                
                writer.writerow(row_data)
        print(f"Arquivo '{filename}' salvo com sucesso!")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar o arquivo CSV: {e}")


def load_artists_from_csv(file_path: str, limit: int) -> list:
    """
    Lê o CSV gerado por 'save_artists_to_csv' e reconstrói as estruturas de dados.

    O que faz:
        Faz o processo inverso (String -> Lista) para gêneros e faixas.
        Retorna apenas os primeiros N registros (limit).

    Args:
        file_path (str): Caminho do CSV.
        limit (int): Número máximo de artistas a carregar.

    Returns:
        list: Lista de dicionários de artistas.
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

    O que faz:
        Valida o ID do artista no dicionário e chama o endpoint `artist_top_tracks`.
    
    Correção de Segurança:
        Se o CSV for antigo e não tiver a coluna 'id', esta função tenta extrair
        o ID diretamente da coluna 'uri' (ex: 'spotify:artist:12345' -> '12345').

    Args:
        artist_data (dict): Dicionário com dados do artista.

    Returns:
        list: Lista de objetos 'track' completos da API.
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


# ==============================================================================
# SEÇÃO 4: FUNÇÕES UTILITÁRIAS GERAIS
# ------------------------------------------------------------------------------
# Helpers para manipulação de strings, listas e leitura de arquivos.
# ==============================================================================

def flatten_list_of_lists(list_of_lists: list) -> list:
    """
    Utilitário para transformar matrizes (lista de listas) em uma lista plana.
    
    O que faz:
        Converte [[1, 2], [3, 4]] em [1, 2, 3, 4].
        
    Args:
        list_of_lists (list): A lista aninhada.

    Returns:
        list: A lista achatada.
    """
    return [item for sublist in list_of_lists for item in sublist]


def get_random_sample(items: list, count: int) -> list:
    """
    Retorna uma amostragem aleatória segura.

    O que faz:
        Seleciona N itens aleatórios da lista.

    Proteção:
        Se 'count' for maior que o tamanho da lista, retorna a lista inteira
        em vez de gerar erro.

    Args:
        items (list): Lista fonte.
        count (int): Tamanho da amostra.

    Returns:
        list: Nova lista com a seleção aleatória.
    """
    sample_size = min(len(items), count)
    return random.sample(items, sample_size)


def extract_spotify_playlist_id(url: str) -> str:
    """
    Limpa e extrai o ID de uma URL de playlist do Spotify.

    O que faz:
        Remove parâmetros de query (como '?si=...') e barras extras da URL.
        
    Args:
        url (str): URL completa.

    Returns:
        str: ID limpo.
    """
    clean_url = url.split('?', 1)[0]
    return clean_url.rstrip('/').split('/')[-1]


def normalize_album_name(name: str) -> str:
    """
    Padroniza nomes de álbuns para detecção de duplicatas.

    O que faz:
        - Remove acentos (NFKD).
        - Converte para minúsculas.
        - Remove termos comuns de edições especiais que não alteram a obra principal.

    Args:
        name (str): Nome original.

    Returns:
        str: Nome normalizado.
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

    O que faz:
        Usa o operador `genre:"example"` na busca da API do Spotify.
        
    Args:
        genre (str): Termo do gênero.
        limit (int): Máximo de resultados.

    Returns:
        list: Lista de dicionários simplificados de artistas.
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