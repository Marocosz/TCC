# functions.py

"""
Uma coleção de funções utilitárias autossuficientes para interagir com a API do Spotify.
Cada função inicializa sua própria conexão com a API, simplificando sua chamada
em scripts externos.
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

# Carrego as minhas credenciais secretas do arquivo .env para o ambiente.
load_dotenv()


# --- 1. Gerenciamento de Playlists e Biblioteca (Requer Login do Usuário) ---

def create_playlist(playlist_name: str, public: bool = True) -> str:
    """
    Cria uma nova playlist para o usuário autenticado.
    """
    # Defino aqui as 'permissões' (escopos) que meu script vai pedir ao usuário.
    # Neste caso, permissão para criar/modificar playlists públicas e privadas.
    scope = "playlist-modify-public playlist-modify-private"
    
    # Crio o meu 'controle remoto' do Spotify, que age em nome do usuário que fizer o login.
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    
    # Pego o ID do usuário que está logado para dizer ao Spotify em qual conta criar a playlist.
    user_id = sp_user.current_user()["id"]
    
    # Aqui eu efetivamente mando o comando para criar a playlist com o nome que escolhi.
    playlist = sp_user.user_playlist_create(user=user_id, name=playlist_name, public=public)
    
    print(f"Playlist '{playlist_name}' criada com sucesso.")
    
    # A API me devolve várias informações da playlist criada, mas eu só preciso do ID dela.
    return playlist["id"]


def add_tracks_to_playlist(playlist_id: str, track_uris: list) -> None:
    """
    Adiciona uma lista de músicas a uma playlist específica, em lotes de 100.
    """
    scope = "playlist-modify-public playlist-modify-private"
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

    # A API só aceita adicionar 100 músicas por vez, então crio um loop que avança de 100 em 100.
    for i in range(0, len(track_uris), 100):
        # Em cada passo do loop, eu 'fatio' a minha lista grande para pegar um pedaço de até 100 URIs.
        batch = track_uris[i:i + 100]
        # Mando o comando para adicionar o lote de músicas de uma vez.
        sp_user.playlist_add_items(playlist_id, batch)
        print(f"Adicionado um lote de {len(batch)} músicas à playlist.")
    
    print("Todas as músicas foram adicionadas.")


def like_tracks(track_uris: list) -> None:
    """
    Salva (curte) uma lista de URIs de músicas na biblioteca do usuário.
    É uma ferramenta fundamental e flexível. Ela verifica antes de curtir para ser eficiente.
    Requer os escopos 'user-library-read' e 'user-library-modify'.
    """
    # Se a lista de URIs estiver vazia, não há nada a fazer, então eu aviso e saio da função.
    if not track_uris:
        print("Nenhuma URI de música fornecida para curtir.")
        return
        
    # Defino as permissões para ler a biblioteca (verificar) e modificá-la (curtir).
    scope = "user-library-read user-library-modify"
    # Crio meu 'controle remoto' do Spotify que age em nome do usuário.
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    
    print(f"--- Processando {len(track_uris)} músicas para curtir... ---")

    new_likes_count = 0
    # A API só aceita 50 músicas por vez, então crio um loop para processar em lotes.
    for i in range(0, len(track_uris), 50):
        # Pego um 'lote' de até 50 músicas da minha lista.
        batch = track_uris[i:i + 50]
        try:
            # Pergunto à API: "destas músicas, quais eu já curti antes?".
            is_already_liked = sp_user.current_user_saved_tracks_contains(tracks=batch)
            
            # Crio uma lista apenas com as músicas que eu ainda não curti.
            tracks_to_like = [uri for uri, liked in zip(batch, is_already_liked) if not liked]
            
            # Se houver de fato músicas novas para curtir neste lote...
            if tracks_to_like:
                # ...mando o comando para curti-las.
                sp_user.current_user_saved_tracks_add(tracks=tracks_to_like)
                new_likes_count += len(tracks_to_like)
                print(f"Adicionado 'like' a {len(tracks_to_like)} novas músicas neste lote.")
            else:
                print("Nenhuma música nova para curtir neste lote (todas já estavam na biblioteca).")
        except Exception as e:
            print(f"Ocorreu um erro ao processar um lote: {e}")
            
    print(f"\n--- Processo finalizado! Total de {new_likes_count} novas músicas foram curtidas. ---")


def like_all_tracks_in_playlist(playlist_id: str) -> None:
    """
    Curte todas as músicas de uma playlist que ainda não estão salvas na biblioteca.
    """
    # Peço permissão para ler playlists e a biblioteca, e também para modificar a biblioteca (curtir).
    scope = "user-library-read user-library-modify playlist-read-private"
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    print(f"--- Iniciando processo para curtir músicas da playlist ID: {playlist_id} ---")

    # Começo com uma lista vazia para guardar as URIs das músicas da playlist.
    track_uris = []
    # Peço a primeira página de músicas da playlist.
    results = sp_user.playlist_tracks(playlist_id)
    
    # Crio um loop para garantir que pego as músicas de TODAS as páginas da playlist.
    while results:
        # Para cada música encontrada na página atual...
        for item in results['items']:
            # ...verifico se é uma música de verdade e se tem uma URI...
            if item.get('track') and item['track'].get('uri'):
                # ...e adiciono a URI na minha lista.
                track_uris.append(item['track']['uri'])
        # Peço ao Spotipy para buscar a próxima página de resultados. Se não houver, o loop para.
        results = sp_user.next(results) if results['next'] else None

    if not track_uris:
        print("Nenhuma música encontrada na playlist.")
        return

    print(f"Encontradas {len(track_uris)} músicas. Verificando e curtindo em lotes...")
    new_likes_count = 0
    
    # Loop para processar as músicas em lotes de 50 (limite da API para curtir/verificar).
    for i in range(0, len(track_uris), 50):
        batch = track_uris[i:i + 50]
        try:
            # Pergunto à API: "destas 50 músicas, quais eu já curti antes?".
            # A resposta vem como uma lista de True/False.
            is_already_liked = sp_user.current_user_saved_tracks_contains(tracks=batch)
            
            # Crio uma nova lista apenas com as músicas que retornaram 'False' na verificação anterior.
            tracks_to_like = [uri for uri, liked in zip(batch, is_already_liked) if not liked]
            
            # Se de fato houver músicas novas para curtir neste lote...
            if tracks_to_like:
                # ...mando o comando para curti-las...
                sp_user.current_user_saved_tracks_add(tracks=tracks_to_like)
                # ...e atualizo minha contagem de novas curtidas.
                new_likes_count += len(tracks_to_like)
                print(f"Adicionado 'like' a {len(tracks_to_like)} novas músicas neste lote.")
            else:
                print("Nenhuma música nova para curtir neste lote (todas já estavam na biblioteca).")
        except Exception as e:
            print(f"Ocorreu um erro ao processar um lote para curtir músicas: {e}")
            
    print(f"\n--- Processo finalizado! Total de {new_likes_count} novas músicas foram curtidas. ---")


def unlike_all_tracks_in_playlist(playlist_id: str) -> None:
    """
    Remove o "like" de todas as músicas de uma playlist que estão na biblioteca do usuário.
    """
    scope = "user-library-read user-library-modify playlist-read-private"
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    print(f"--- Iniciando processo para remover likes da playlist ID: {playlist_id} ---")

    # A lógica para pegar todas as URIs da playlist é idêntica à da função de curtir.
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

    print(f"Encontradas {len(track_uris)} músicas. Verificando e removendo 'likes' em lotes...")
    unliked_count = 0
    
    # Loop para processar em lotes de 50.
    for i in range(0, len(track_uris), 50):
        batch = track_uris[i:i + 50]
        try:
            # Pergunto à API: "destas 50, quais estão atualmente curtidas?".
            is_currently_liked = sp_user.current_user_saved_tracks_contains(tracks=batch)
            # Crio uma lista apenas com as músicas que retornaram 'True'.
            tracks_to_unlike = [uri for uri, liked in zip(batch, is_currently_liked) if liked]

            # Se houver músicas para descurtir neste lote...
            if tracks_to_unlike:
                # ...mando o comando para remover o like delas.
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
    Remove o "like" de TODAS as músicas salvas na biblioteca do usuário.

    Esta é uma operação destrutiva e irreversível. Uma confirmação explícita
    do usuário é necessária antes que a exclusão seja executada.

    Requer os escopos 'user-library-read' (para buscar todas as músicas) e
    'user-library-modify' (para remover os likes).
    """
    # Define os escopos necessários para ler e modificar a biblioteca de músicas.
    scope = "user-library-read user-library-modify"
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

    # --- PASSO 1: BUSCAR TODAS AS MÚSICAS CURTIDAS ---
    print("Iniciando busca de todas as suas Músicas Curtidas. Isso pode demorar se a sua biblioteca for grande...")
    
    all_track_uris = []
    # Pede a primeira página (lote de 50) das músicas salvas.
    results = sp_user.current_user_saved_tracks(limit=50)
    
    # Loop de paginação para garantir que pegamos TODAS as músicas, não apenas as primeiras 50.
    while results:
        # Para cada música encontrada na página atual...
        for item in results['items']:
            # ...adiciono a URI dela na minha lista.
            if item.get('track') and item['track'].get('uri'):
                all_track_uris.append(item['track']['uri'])
        
        # Informo o progresso para o usuário não achar que o script travou.
        print(f"Progresso: {len(all_track_uris)} músicas encontradas...")
        
        # Peço ao Spotipy para buscar a próxima página de resultados. Se não houver, o loop para.
        results = sp_user.next(results) if results['next'] else None

    if not all_track_uris:
        print("\nVocê não tem nenhuma música curtida na sua biblioteca.")
        return

    # --- PASSO 2: TRAVA DE SEGURANÇA E CONFIRMAÇÃO ---
    total_songs = len(all_track_uris)
    print(f"\nBusca finalizada. Total de {total_songs} músicas encontradas na sua biblioteca.")
    
    # Exibe o aviso de perigo e pede a confirmação.
    print("\n" + "="*60)
    print("⚠️  AVISO: VOCÊ ESTÁ PRESTES A REMOVER TODAS AS SUAS MÚSICAS CURTIDAS! ⚠️")
    print("                 ESTA AÇÃO É PERMANENTE E IRREVERSÍVEL.")
    print("="*60)
    
    confirmation_phrase = "EU QUERO APAGAR TUDO"
    user_input = input(f"Para confirmar, digite a frase exata '{confirmation_phrase}': ")

    # Se a confirmação não for exata, o script é abortado com segurança.
    if user_input != confirmation_phrase:
        print("\nConfirmação incorreta. Operação cancelada. Nenhum like foi removido.")
        return

    # --- PASSO 3: EXCLUSÃO EM LOTES ---
    print("\nConfirmação recebida. Iniciando a remoção dos likes em lotes...")
    
    total_batches = (total_songs + 49) // 50  # Calcula quantos lotes serão necessários
    
    for i in range(0, total_songs, 50):
        batch = all_track_uris[i:i + 50]
        try:
            sp_user.current_user_saved_tracks_delete(tracks=batch)
            print(f"Lote {i//50 + 1}/{total_batches}: Like de {len(batch)} músicas foi removido.")
            # Adicionamos uma pequena pausa para sermos respeitosos com a API.
            time.sleep(0.5) 
        except Exception as e:
            print(f"Ocorreu um erro ao processar o lote {i//50 + 1}: {e}")
            
    print("\n--- PROCESSO DE EXCLUSÃO FINALIZADO! ---")
    print("Todas as músicas foram removidas da sua biblioteca de 'Músicas Curtidas'.")
    
    
def audit_playlist_liked_status(playlist_id: str) -> None:
    """
    Função de diagnóstico: Apenas lê e verifica o status de "curtida" de cada
    música em uma playlist, sem tentar modificar nada.
    Requer os escopos 'user-library-read' e 'playlist-read-private'.
    """
    # Defino permissões apenas para LER a playlist e a biblioteca do usuário.
    scope = "user-library-read playlist-read-private"
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

    # Começo uma lista vazia para guardar os detalhes das músicas da playlist.
    playlist_tracks = []
    # Peço a primeira página de músicas.
    results = sp_user.playlist_tracks(playlist_id)
    
    # Faço um loop para garantir que pego todas as músicas, mesmo que a playlist tenha mais de 100.
    while results:
        for item in results['items']:
            if item.get('track') and item['track'].get('uri'):
                # Guardo o nome e a URI de cada música.
                playlist_tracks.append({'name': item['track']['name'], 'uri': item['track']['uri']})
        # Peço a próxima página de resultados. O loop para quando não houver mais páginas.
        results = sp_user.next(results) if results['next'] else None

    if not playlist_tracks:
        print("Playlist não encontrada ou está vazia.")
        return

    print(f"--- Auditando {len(playlist_tracks)} músicas da playlist ---")
    
    not_liked_tracks = []
    # Processo a verificação em lotes de 50.
    for i in range(0, len(playlist_tracks), 50):
        # Pego um lote de até 50 músicas para verificar.
        batch = playlist_tracks[i:i + 50]
        # Extraio apenas as URIs deste lote.
        batch_uris = [track['uri'] for track in batch]
        
        try:
            # Envio o lote de URIs e pergunto à API quais delas estão curtidas.
            liked_status_list = sp_user.current_user_saved_tracks_contains(tracks=batch_uris)
            
            # Comparo a resposta (True/False) com a minha lista de músicas.
            for track_info, is_liked in zip(batch, liked_status_list):
                # Se uma música não está curtida (status é False)...
                if not is_liked:
                    # ...adiciono o nome dela na minha lista de "não curtidas".
                    not_liked_tracks.append(track_info['name'])
        except Exception as e:
            print(f"Ocorreu um erro ao auditar um lote: {e}")
    
    # No final, apresento o relatório.
    print("\n--- Relatório Final da Auditoria ---")
    if not not_liked_tracks:
        print("✅ CONFIRMADO: A API do Spotify reporta que TODAS as músicas desta playlist estão salvas.")
    else:
        print(f"🚨 ALERTA: A API reporta que {len(not_liked_tracks)} músicas NÃO estão salvas:")
        for name in not_liked_tracks:
            print(f"  - {name}")


# --- 2. Extração de Dados do Catálogo (Não Requer Login do Usuário) ---

def get_artists_from_playlist(playlist_id: str) -> dict:
    """Busca todas as músicas de uma playlist e retorna um dicionário de artistas únicos."""
    # Crio um cliente que não precisa de login, pois playlists públicas são dados gerais.
    sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    print("Buscando músicas da playlist para extrair artistas...")
    # Uso um dicionário para garantir que cada artista seja adicionado apenas uma vez.
    unique_artists = {}
    
    results = sp_app.playlist_items(playlist_id)
    playlist_items = results['items']
    # Garanto que vou pegar os artistas de todas as músicas, não apenas das 50 primeiras.
    while results['next']:
        results = sp_app.next(results)
        playlist_items.extend(results['items'])

    for item in playlist_items:
        if item.get("track") and item['track'].get('artists'):
            for artist in item["track"]["artists"]:
                # A chave do dicionário é o ID do artista (único), e o valor é o nome.
                # Se o ID já existir, nada acontece. Se for novo, ele é adicionado.
                if artist['id'] not in unique_artists:
                    unique_artists[artist['id']] = artist['name']
    
    print(f"Encontrados {len(unique_artists)} artistas únicos na playlist.")
    return unique_artists


def get_full_artist_profiles(artists_dict: dict) -> list:
    """Recebe um dicionário de artistas e busca seus perfis completos na API."""
    sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    print("Buscando detalhes dos perfis dos artistas...")
    artist_ids = list(artists_dict.keys())
    artist_profiles = []
    
    # Otimização: faço a busca dos perfis em lotes de 50 para ser mais rápido.
    for i in range(0, len(artist_ids), 50):
        batch_ids = artist_ids[i:i + 50]
        try:
            # Esta única chamada me retorna os detalhes de até 50 artistas de uma vez.
            artists_details = sp_app.artists(batch_ids)
            # Para cada perfil detalhado que recebi...
            for artist_data in artists_details['artists']:
                # ...eu ainda preciso fazer uma chamada individual para pegar as top 10 músicas no Brasil.
                top_tracks_result = sp_app.artist_top_tracks(artist_data['id'], country="BR")
                # Monto meu dicionário final com todas as informações que coletei.
                artist_profiles.append({
                    "name": artist_data['name'], "uri": artist_data['uri'],
                    "followers": artist_data['followers']['total'], "genres": artist_data['genres'],
                    "popularity": artist_data['popularity'],
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
    Busca a discografia de álbuns de estúdio de um artista, removendo duplicatas.
    """
    sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    
    # Primeiro, busco o artista pelo nome para encontrar seu ID único.
    search_result = sp_app.search(q=f'artist:{artist_name}', type='artist', limit=1)
    if not search_result['artists']['items']:
        print(f"Artista '{artist_name}' não encontrado.")
        return {}
    
    artist = search_result['artists']['items'][0]
    artist_id = artist['id']
    print(f"Artista encontrado: '{artist['name']}' (ID: {artist_id})")

    # Peço à API apenas os lançamentos do tipo 'album'.
    all_album_releases = []
    results = sp_app.artist_albums(artist_id, album_type='album', limit=50)
    all_album_releases.extend(results['items'])
    while results['next']:
        results = sp_app.next(results)
        all_album_releases.extend(results['items'])
    
    unique_albums = []
    seen_album_names = set() # Uso um 'set' para controlar os nomes de álbuns que já vi.
    for album in all_album_releases:
        # Normalizo o nome do álbum para tratar "Meu Album" e "Meu Album (Deluxe)" como iguais.
        normalized_name = normalize_album_name(album['name'])
        if normalized_name not in seen_album_names:
            seen_album_names.add(normalized_name)
            unique_albums.append(album)
    
    print(f"\nEncontrados {len(unique_albums)} álbuns de estúdio únicos para processar.")

    artist_discography = {}
    for i, album in enumerate(unique_albums):
        print(f"Buscando faixas de '{album['name']}' ({i+1}/{len(unique_albums)})...")
        try:
            # Para cada álbum, pego a lista de suas faixas.
            track_results = sp_app.album_tracks(album['id'], limit=50)
            tracks = track_results['items']
            while track_results['next']:
                track_results = sp_app.next(track_results)
                tracks.extend(track_results['items'])
            # Armazeno as faixas em um dicionário, usando o nome do álbum como chave.
            artist_discography[album['name']] = [track['name'] for track in tracks]
        except Exception as e:
            print(f"Não foi possível buscar faixas do álbum {album['id']}. Motivo: {e}")
            continue
            
    return artist_discography


def fetch_track_uris(track_names: list) -> list:
    """Busca no Spotify uma lista de nomes de músicas e retorna suas URIs."""
    sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    found_uris = []
    print(f"Buscando URIs para {len(track_names)} músicas...")
    for name in track_names:
        if not name.strip(): continue
        try:
            # Faço uma busca geral pela música e pego o primeiro resultado, que tem mais chance de ser o correto.
            results = sp_app.search(q=name, type='track', limit=1)
            if results and results['tracks']['items']:
                found_uris.append(results['tracks']['items'][0]['uri'])
        except spotipy.exceptions.SpotifyException:
            # Se uma música não for encontrada, eu simplesmente ignoro e continuo para a próxima.
            pass 
        # Faço uma pequena pausa para não sobrecarregar a API do Spotify.
        time.sleep(0.05)
            
    print(f"Encontradas {len(found_uris)} URIs.")
    return found_uris


# --- 3. Salvamento de Dados ---

def save_artists_to_csv(artists_data: list, filename: str, sort_by: str = 'popularity'):
    """Ordena os dados dos artistas e os salva em um arquivo CSV."""
    if not artists_data:
        print("Nenhum dado de artista para salvar.")
        return

    print(f"Ordenando artistas por '{sort_by}' e preparando para salvar...")
    # Uso a função 'sorted' do Python para ordenar minha lista de dicionários.
    # O 'key=lambda...' diz a ela para olhar o valor da chave 'popularity' ou 'followers' para ordenar.
    # 'reverse=True' garante que será do maior para o menor.
    sorted_artists = sorted(artists_data, key=lambda item: item.get(sort_by, 0), reverse=True)
    
    # Defino na mão quais colunas eu quero no meu CSV e em qual ordem.
    csv_headers = ["name", "uri", "followers", "genres", "popularity", "top_tracks"]
    try:
        # Abro o arquivo no modo de escrita ('w'). 'newline' e 'encoding' são boas práticas.
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            # Crio um "escritor" que sabe como lidar com dicionários.
            writer = csv.DictWriter(file, fieldnames=csv_headers)
            # Escrevo a primeira linha do arquivo, o cabeçalho.
            writer.writeheader()
            # Para cada artista na minha lista ordenada...
            for artist_info in sorted_artists:
                # ...crio uma cópia para não alterar meus dados originais...
                row_data = artist_info.copy()
                # ...transformo as listas de 'genres' e 'top_tracks' em texto, separado por "; "...
                row_data["genres"] = "; ".join(row_data["genres"])
                row_data["top_tracks"] = "; ".join(row_data["top_tracks"])
                # ...e escrevo a linha no arquivo.
                writer.writerow(row_data)
        print(f"Arquivo '{filename}' salvo com sucesso!")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar o arquivo CSV: {e}")


# --- 4. Funções Utilitárias Gerais ---

def load_artists_from_csv(file_path: str, limit: int) -> list:
    """Lê dados de artistas a partir de um arquivo CSV."""
    selected_artists = []
    try:
        with io.open(file_path, 'r', encoding='utf-8') as csvfile:
            # Crio um "leitor" que entende que cada linha é um dicionário.
            reader = csv.DictReader(csvfile)
            for i, row in enumerate(reader):
                if i >= limit: break
                # Faço o processo inverso do salvamento: transformo o texto de volta em listas.
                row['top_tracks'] = [track.strip() for track in row.get('top_tracks', '').split(';') if track.strip()]
                row['genres'] = [genre.strip() for genre in row.get('genres', '').split(';') if genre.strip()]
                selected_artists.append(row)
    except FileNotFoundError:
        print(f"Erro: O arquivo no caminho {file_path} não foi encontrado.")
        return []
    return selected_artists


def extract_top_tracks_from_data(artist_data: dict) -> list:
    """
    Extrai a lista 'top_tracks' do dicionário de dados de um artista,
    que foi carregado de um arquivo CSV.
    """
    return artist_data.get('top_tracks', [])


def flatten_list_of_lists(list_of_lists: list) -> list:
    """Transforma uma lista de listas em uma lista única."""
    # Esta é uma forma pythônica e eficiente de fazer um loop duplo.
    return [item for sublist in list_of_lists for item in sublist]


def get_random_sample(items: list, count: int) -> list:
    """Retorna uma amostra aleatória de uma lista."""
    # Pego o menor valor entre o que eu quero e o que eu tenho, para não dar erro.
    sample_size = min(len(items), count)
    # A função 'random.sample' já faz o trabalho de escolher aleatoriamente sem repetição.
    return random.sample(items, sample_size)


def extract_spotify_playlist_id(url: str) -> str:
    """Extrai o ID da playlist a partir de uma URL do Spotify."""
    # Pego só a parte da URL antes do "?", para remover parâmetros.
    clean_url = url.split('?', 1)[0]
    # Pego a última parte do endereço, que é o ID.
    return clean_url.rstrip('/').split('/')[-1]


def normalize_album_name(name: str) -> str:
    """
    Função auxiliar para limpar nomes de álbuns para comparações mais precisas.
    """
    # Decompõe caracteres como 'á' em 'a' + ´. O encode/decode remove o acento.
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('utf-8')
    name = name.lower()
    common_terms = ['(deluxe edition)', '(remastered)', '(remaster)', '(special edition)', '(ao vivo)', '(live)']
    # Remove textos comuns de edições especiais para que o nome base do álbum seja o mesmo.
    for term in common_terms:
        name = name.replace(term, '')
    # Remove espaços em branco extras no início ou no fim.
    return name.strip()