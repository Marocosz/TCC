"""
Diagnóstico OAuth — investiga POR QUE o endpoint /playlists/{id}/tracks
retorna 403 mesmo com app novo (Premium) e usuário autenticado.

Roda isolado, imprime resultado de várias rotas alternativas pra cada teste.
Se todas falharem, é uma restrição nova da Spotify Web API.
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials


def step(num, title):
    print(f"\n{'=' * 60}")
    print(f" PASSO {num}: {title}")
    print('=' * 60)


# Apaga .cache para forçar fresh OAuth
cache_path = '.cache'
if os.path.exists(cache_path):
    print(f"[i] Removendo {cache_path} antigo...")
    os.remove(cache_path)

step(1, "Verificando variáveis de ambiente")
print(f"  CLIENT_ID    = {os.getenv('SPOTIPY_CLIENT_ID', 'NAO_DEFINIDO')[:8]}...")
print(f"  REDIRECT_URI = {os.getenv('SPOTIPY_REDIRECT_URI', 'NAO_DEFINIDO')}")

step(2, "Forçando OAuth fresco — atenção: vai abrir o browser")
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope='playlist-read-private playlist-read-collaborative'))

# Quem está autenticado
me = sp.current_user()
print(f"  ✅ Logado como: {me['display_name']} (id={me['id']})")
print(f"  Produto Spotify: {me.get('product', 'N/A')}")
print(f"  Email: {me.get('email', '(escopo email não solicitado)')}")
print(f"  País: {me.get('country', 'N/A')}")

# Pega o token bruto pra fazer chamadas direto
token = sp.auth_manager.get_access_token(as_dict=True)['access_token']
print(f"  Token (primeiros 30 chars): {token[:30]}...")

PLAYLIST_ID = '0GJo96dZ1uXkcPU1YeOI89'  # Beatriz mirror

step(3, "Teste — endpoint /playlists/{id} (metadata)")
try:
    r = sp.playlist(PLAYLIST_ID, fields='name,public,owner.display_name,tracks.total')
    print(f"  ✅ OK: {r}")
except Exception as e:
    print(f"  ❌ ERRO: {str(e)[:200]}")

step(4, "Teste — sp.playlist_items DEFAULT (additional_types=track,episode)")
try:
    r = sp.playlist_items(PLAYLIST_ID, limit=3)
    print(f"  ✅ OK: {len(r['items'])} items")
except Exception as e:
    print(f"  ❌ ERRO: {str(e)[:200]}")

step(5, "Teste — sp.playlist_items SEM additional_types")
try:
    r = sp.playlist_items(PLAYLIST_ID, limit=3, additional_types=None)
    print(f"  ✅ OK: {len(r['items'])} items")
except Exception as e:
    print(f"  ❌ ERRO: {str(e)[:200]}")

step(6, "Teste — chamada RAW HTTP a /tracks (bypass spotipy)")
url = f"https://api.spotify.com/v1/playlists/{PLAYLIST_ID}/tracks?limit=3"
headers = {"Authorization": f"Bearer {token}"}
r = requests.get(url, headers=headers)
print(f"  HTTP {r.status_code}")
print(f"  Resposta: {r.text[:400]}")

step(7, "Teste — chamada RAW HTTP a /playlists/{id} pegando tracks embed")
url = f"https://api.spotify.com/v1/playlists/{PLAYLIST_ID}?fields=name,tracks.items(track(name,id))"
r = requests.get(url, headers=headers)
print(f"  HTTP {r.status_code}")
print(f"  Resposta: {r.text[:600]}")

step(8, "Teste — endpoint que SABEMOS que funciona: /me/tracks (saved tracks)")
try:
    r = sp.current_user_saved_tracks(limit=3)
    print(f"  ✅ OK: {r['total']} saved tracks no total")
except Exception as e:
    print(f"  ❌ ERRO: {str(e)[:200]}")

print(f"\n{'=' * 60}")
print(" DIAGNÓSTICO CONCLUÍDO. Cole TODO o output acima de volta.")
print('=' * 60)
