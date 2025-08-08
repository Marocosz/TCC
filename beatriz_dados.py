import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
from functions import extract_spotify_playlist_id
import os
import csv

load_dotenv()

client_id_carregado = os.getenv("SPOTIPY_CLIENT_ID")
client_secret_carregado = os.getenv("SPOTIPY_CLIENT_SECRET")

# spotify app client
sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

# spotify user client
sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-read-private playlist-read-collaborative"))


# Playlists ===================================
playlist_topbrasil_url = "https://open.spotify.com/playlist/5LLJntbc3SvdXcYhRJZwKP?si=b2133b6c4ef24e0f"
playlist_topbrasil_id = extract_spotify_playlist_id(playlist_topbrasil_url)

results_items_topbrasil = sp_app.playlist_items(playlist_topbrasil_id, limit=50)

artistas_topbrasil = []
for item in results_items_topbrasil["items"]:
    if item.get("track"): # Garante que o item é uma música
        for artista in item["track"]["artists"]:
            artistas_topbrasil.append(artista["name"])

artistas_topbrasil_unicos = list(set(artistas_topbrasil))

artistas_topbrasil_infos = []
for artista in artistas_topbrasil_unicos:
    result_artista = sp_app.search(q=artista, type="artist", limit=1)
    uri_artista = result_artista["artists"]["items"][0]["uri"]
    follower_artista = result_artista["artists"]["items"][0]["followers"]["total"]
    genres_artista = result_artista["artists"]["items"][0]["genres"]
    popularity_artista = result_artista["artists"]["items"][0]["popularity"]
    toptracks_artista = sp_app.artist_top_tracks(uri_artista, country="BR")
    artistas_topbrasil_infos.append({
        "name": artista,
        "uri": uri_artista,
        "followers": follower_artista,
        "genres": genres_artista,
        "popularity": popularity_artista,
        "top_tracks": [track["name"] for track in toptracks_artista["tracks"]]
    })


artistas_ordenados_por_popularidade = sorted(artistas_topbrasil_infos, key=lambda item: item['popularity'], reverse=True)
nomes_dos_artistas_ordenados_por_popularidade = [artista['name'] for artista in artistas_ordenados_por_popularidade]

artistas_ordenados_por_followers = sorted(artistas_topbrasil_infos, key=lambda item: item['followers'], reverse=True)
nomes_dos_artistas_ordenados_por_followers = [artista['name'] for artista in artistas_ordenados_por_followers]

print(nomes_dos_artistas_ordenados_por_popularidade)
print(nomes_dos_artistas_ordenados_por_followers)


csv_file_name = "artistas_topbrasil_ordem_popularidade.csv"
csv_headers = ["name", "uri", "followers", "genres", "popularity", "top_tracks"]

with open(csv_file_name, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=csv_headers)

    # Escreva a linha de cabeçalho
    writer.writeheader()

    # Escreva os dados de cada artista
    for artista_info in artistas_ordenados_por_popularidade:
        # Criamos uma cópia do dicionário para modificá-lo antes de escrever,
        # sem alterar o original.
        artista_info_for_csv = artista_info.copy()

        # Convertemos a lista de gêneros e top_tracks para uma string.
        artista_info_for_csv["genres"] = "; ".join(artista_info_for_csv["genres"])
        artista_info_for_csv["top_tracks"] = "; ".join(artista_info_for_csv["top_tracks"])

        writer.writerow(artista_info_for_csv)