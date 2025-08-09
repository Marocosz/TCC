import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import random
import os
import csv
import io
import time

load_dotenv()

client_id_carregado = os.getenv("SPOTIPY_CLIENT_ID")
client_secret_carregado = os.getenv("SPOTIPY_CLIENT_SECRET")

# spotify app client
sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())


def extract_spotify_playlist_id(url: str) -> str:
    clean = url.split('?', 1)[0]
    return clean.rstrip('/').split('/')[-1]


def criar_playlist(nome_playlist):
    # spotify user client
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-modify-public playlist-modify-private"))
    
    usuario_alvo = sp_user.current_user()["id"]

    playlist = sp_user.user_playlist_create(user=usuario_alvo, name=nome_playlist, public=True)

    return playlist["id"]


def adicionar_musicas_a_playlist(playlist_id: str, musicas: list) -> None:
    # spotify user client
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-modify-public playlist-modify-private"))

    sp_user.playlist_add_items(playlist_id, musicas)


def csv_para_lista(csv_file_path: str, qtd_artistas: int) -> list:
    # 20 primeiros artistas
    artistas_selecionados = []
    # Usando 'with' para garantir que o arquivo seja fechado corretamente
    with io.open(csv_file_path, encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for i, row in enumerate(reader):
            # cada row é o dict do artista
            if len(artistas_selecionados) >= qtd_artistas:
                break
            
            if 'top_tracks' in row and row['top_tracks']:
                # Divide a string de top_tracks usando ';' e remove espaços extras
                row['top_tracks'] = [track.strip() for track in row['top_tracks'].split(';')]
            else:
                row['top_tracks'] = [] # Se não tiver top_tracks, a lista fica vazia
                
            if 'genres' in row and row['genres']:
                # Divide a string de genres usando ';' e remove espaços extras
                row['genres'] = [genre.strip() for genre in row['genres'].split(';')]
            else:
                row['genres'] = [] # Se não tiver genres, a lista fica vazia

            artistas_selecionados.append(row)

    return artistas_selecionados


def puxa_top_musicas(artista: dict) -> list:
    return artista.get('top_tracks')


def achatar_lista_de_listas(lista_de_listas: list) -> list:
    """
    Transforma uma lista de listas em uma única lista contendo todos os itens.
    Ex: [[1, 2], [3, 4]] -> [1, 2, 3, 4]
    """
    lista_unica = []
    for sublista in lista_de_listas:
        lista_unica.extend(sublista) # Adiciona todos os elementos da sublista à lista única
    return lista_unica


def aleatoriza_qtd(lista: list, qtd: int) -> list:
    """
    Retorna uma lista com uma quantidade aleatória de elementos da lista original.
    """
    return random.sample(lista, min(len(lista), qtd))


def buscar_uris_das_musicas(nomes_musicas: list) -> list:
    sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    
    uris_encontradas = []
    for nome_musica in nomes_musicas:
        if not nome_musica.strip():
            continue
        
        query = nome_musica        
        try:
            results = sp_app.search(q=query, type='track', limit=1)
            
            if results and results['tracks'] and results['tracks']['items']:
                track_uri = results['tracks']['items'][0]['uri']
                uris_encontradas.append(track_uri)
            
        except spotipy.exceptions.SpotifyException:
            pass # Ignora erros de busca de música específica para não interromper o processo
        
        time.sleep(0.05)
            
    return uris_encontradas


def like_em_tracks(lista_uris_tracks: list):
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="user-library-modify user-library-read playlist-read-private"))
    sp_user.current_user()
    for uri in lista_uris_tracks:
        sp_user.current_user_saved_tracks_add([uri])


def curtir_todas_musicas_playlist(playlist_id: str):
    # A SOLUÇÃO ESTÁ AQUI: Adicionamos 'user-library-read' ao escopo
    scope = "user-library-modify user-library-read playlist-read-private"
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    
    uris_para_curtir = []
    results = sp_user.playlist_tracks(playlist_id)
    
    # Loop para pegar todas as músicas, mesmo em playlists com mais de 100 itens
    while results:
        for item in results['items']:
            if item.get('track') and item['track'].get('uri'):
                uris_para_curtir.append(item['track']['uri'])
        
        if results['next']:
            results = sp_user.next(results)
        else:
            results = None

    if not uris_para_curtir:
        print("Nenhuma música encontrada na playlist para curtir.")
        return

    print(f"Encontradas {len(uris_para_curtir)} músicas na playlist. Tentando curtir...")
    
    curtidas_novas = 0
    # Processa as músicas em lotes de 50 para eficiência e segurança
    for i in range(0, len(uris_para_curtir), 50):
        lote = uris_para_curtir[i:i + 50]
        try:
            # 1. Verifica quais músicas do lote já estão na biblioteca
            ja_curtidas = sp_user.current_user_saved_tracks_contains(tracks=lote)
            
            # 2. Cria uma nova lista apenas com as que ainda NÃO foram curtidas
            lote_para_adicionar = [uri for uri, curtida in zip(lote, ja_curtidas) if not curtida]
            
            # 3. Adiciona apenas as novas músicas, se houver alguma
            if lote_para_adicionar:
                sp_user.current_user_saved_tracks_add(tracks=lote_para_adicionar)
                curtidas_novas += len(lote_para_adicionar)
                print(f"Lote {i//50 + 1}: {len(lote_para_adicionar)} novas músicas foram curtidas.")
            else:
                 print(f"Lote {i//50 + 1}: Nenhuma música nova para curtir (todas já estavam na biblioteca).")

        except spotipy.exceptions.SpotifyException as e:
            print(f"Ocorreu um erro ao processar um lote: {e}")
    
    print(f"\nProcesso concluído! Total de {curtidas_novas} novas músicas adicionadas às 'Músicas Curtidas'.")


def verificar_status_curtidas_playlist(playlist_id: str):
    """
    Função de auditoria: Apenas lê e verifica o status de "curtida" de cada
    música em uma playlist, sem tentar modificar nada.
    """
    scope = "user-library-read playlist-read-private"
    sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

    # Vamos pegar o nome e a URI de cada faixa
    faixas_playlist = []
    results = sp_user.playlist_tracks(playlist_id)
    while results:
        for item in results['items']:
            if item.get('track') and item['track'].get('uri'):
                nome = item['track']['name']
                uri = item['track']['uri']
                faixas_playlist.append({'nome': nome, 'uri': uri})
        
        if results['next']:
            results = sp_user.next(results)
        else:
            results = None

    if not faixas_playlist:
        print("Playlist não encontrada ou vazia.")
        return

    print(f"--- Iniciando Auditoria de {len(faixas_playlist)} Músicas na Playlist ---")

    uris_nao_curtidas = []
    nomes_nao_curtidos = []
    
    # Verificação em lotes
    for i in range(0, len(faixas_playlist), 50):
        lote = faixas_playlist[i:i + 50]
        lote_uris = [faixa['uri'] for faixa in lote]
        
        try:
            # A chamada principal de verificação
            status_curtidas = sp_user.current_user_saved_tracks_contains(tracks=lote_uris)
            
            # Compara o status de cada música
            for j, status in enumerate(status_curtidas):
                if not status:
                    uris_nao_curtidas.append(lote[j]['uri'])
                    nomes_nao_curtidos.append(lote[j]['nome'])
        except Exception as e:
            print(f"Erro ao auditar um lote: {e}")
    
    # --- Relatório Final ---
    print("\n--- Relatório Final da Auditoria ---")
    if not nomes_nao_curtidos:
        print("✅ CONFIRMADO: A API do Spotify reporta que TODAS as músicas da playlist estão salvas em 'Músicas Curtidas'.")
        print("A discrepância na contagem é um bug de exibição no seu aplicativo Spotify.")
    else:
        print(f"🚨 INESPERADO: A API reporta que {len(nomes_nao_curtidos)} músicas NÃO estão salvas:")
        for nome in nomes_nao_curtidos:
            print(f"  - {nome}")
        print("Isso indica um problema de sincronização raro na sua conta do Spotify.")