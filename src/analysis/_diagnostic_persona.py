"""
Diagnóstico Persona — usa o .cache_daniel já gerado pra confirmar:
1. Quem está autenticado
2. Qual produto (Premium/Free)
3. Se a playlist espelho aparece em current_user_playlists()
4. Se o OAuth Daniel consegue ler /me/playlists/{id}/tracks
"""

import os
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()


def step(num, title):
    print(f"\n{'=' * 60}")
    print(f" PASSO {num}: {title}")
    print('=' * 60)


# Usa o cache_daniel JÁ EXISTENTE (não força login novo)
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope='playlist-read-private playlist-read-collaborative user-read-private',
    cache_path='.cache_daniel',
    show_dialog=False  # usa cache
))

step(1, "Quem está autenticado pelo .cache_daniel?")
me = sp.current_user()
print(f"  display_name: {me['display_name']}")
print(f"  id          : {me['id']}")
print(f"  product     : {me.get('product', 'N/A')}  ← Premium ou Free?")
print(f"  country     : {me.get('country', 'N/A')}")

PLAYLIST_DANIEL = '0V7TjiOtU4wh2Ye0L4iwCd'

step(2, "A playlist espelho está em current_user_playlists()?")
try:
    playlists = sp.current_user_playlists(limit=50)
    achou = False
    for pl in playlists['items']:
        if pl['id'] == PLAYLIST_DANIEL:
            print(f"  ✅ ENCONTRADA: '{pl['name']}' (owner: {pl['owner']['display_name']}, total tracks: {pl['tracks']['total']})")
            achou = True
            break
    if not achou:
        print(f"  ❌ NAO ENCONTRADA entre as {len(playlists['items'])} primeiras playlists do user.")
        print(f"  Total de playlists do user: {playlists['total']}")
        print(f"  Primeiras 5: {[p['name'] for p in playlists['items'][:5]]}")
except Exception as e:
    print(f"  ERRO: {str(e)[:300]}")

step(3, "Qual o ESCOPO do token cacheado?")
token_info = sp.auth_manager.get_cached_token()
print(f"  Scopes concedidos: {token_info.get('scope', 'N/A')}")
print(f"  Token type       : {token_info.get('token_type', 'N/A')}")

token = token_info['access_token']
HEADERS = {"Authorization": f"Bearer {token}"}

step(4, "RAW HTTP /me/playlists/{id}/tracks (Daniel lendo a própria)")
url = f"https://api.spotify.com/v1/playlists/{PLAYLIST_DANIEL}/tracks?limit=3"
r = requests.get(url, headers=HEADERS)
print(f"  HTTP {r.status_code}")
print(f"  Body: {r.text[:500]}")

step(5, "RAW HTTP /playlists/{id}/items (endpoint NOVO Feb/2026)")
url = f"https://api.spotify.com/v1/playlists/{PLAYLIST_DANIEL}/items?limit=3"
r = requests.get(url, headers=HEADERS)
print(f"  HTTP {r.status_code}")
print(f"  Body: {r.text[:500]}")

step(6, "RAW HTTP /me/tracks (saved tracks — exige user-library-read scope)")
url = "https://api.spotify.com/v1/me/tracks?limit=3"
r = requests.get(url, headers=HEADERS)
print(f"  HTTP {r.status_code}")
print(f"  Body: {r.text[:300]}")

print(f"\n{'=' * 60}")
print(" Cole o output completo de volta.")
print('=' * 60)
