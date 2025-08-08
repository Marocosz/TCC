import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import os

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


