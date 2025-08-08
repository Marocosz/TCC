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


def adicionar_musicas_a_playlist(playlist_id, musicas):
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


def buscar_uris_das_musicas(sp_app: spotipy.Spotify, nomes_musicas: list, nome_artista_para_refinar: str = None) -> list:
    uris_encontradas = []
    
    for nome_musica in nomes_musicas:
        if not nome_musica.strip():
            continue
        
        query = nome_musica
        if nome_artista_para_refinar:
            query = f"{nome_musica} artist:\"{nome_artista_para_refinar}\""
        
        try:
            results = sp_app.search(q=query, type='track', limit=1)
            
            if results and results['tracks'] and results['tracks']['items']:
                track_uri = results['tracks']['items'][0]['uri']
                uris_encontradas.append(track_uri)
            
        except spotipy.exceptions.SpotifyException:
            pass # Ignora erros de busca de música específica para não interromper o processo
        
        time.sleep(0.05)
            
    return uris_encontradas