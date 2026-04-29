"""
Diagnóstico Marcos — testa se token OAuth do Marcos (Premium, dono do app)
retorna popularity / followers / genres no endpoint /artists/{id}.

Se SIM, separamos os 2 papéis no extrator:
- Persona OAuth → lê tracks da própria playlist (/playlists/{id}/items)
- Marcos OAuth → enriquece artistas (/artists/{id})

Se NÃO, esses campos foram removidos universalmente em Feb/2026 para apps
Development Mode, e teremos que buscar dados externos (MusicBrainz/Last.fm).
"""
import os, requests, json
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

# Faz OAuth fresco como Marcos (dono do app, Premium)
am = SpotifyOAuth(
    scope='playlist-read-private user-read-private',
    cache_path='.cache_marcos',
    show_dialog=True
)
sp = spotipy.Spotify(auth_manager=am)
token = am.get_access_token(as_dict=False)

me = sp.current_user()
print(f"Logado como: {me['display_name']} (product={me.get('product')})")
assert me['product'] == 'premium', "ATENÇÃO: faça login como Marcos (Premium)!"

ARTIST_ID = '1e2BbxgbpiLmPw5hQDEaPL'  # 7ove
H = {'Authorization': f'Bearer {token}'}

print("\n--- /artists/{id} com token MARCOS ---")
r = requests.get(f'https://api.spotify.com/v1/artists/{ARTIST_ID}', headers=H)
print(f"HTTP {r.status_code}")
print(f"Campos: {sorted(r.json().keys())}")
print(f"  popularity : {r.json().get('popularity', '<MISSING>')}")
print(f"  followers  : {r.json().get('followers', '<MISSING>')}")
print(f"  genres     : {r.json().get('genres', '<MISSING>')}")

print("\n--- /artists?ids=... batch com token MARCOS ---")
ids = ['1e2BbxgbpiLmPw5hQDEaPL', '6MvnyPinXRQbUCMsPoymhR']
r = requests.get(f'https://api.spotify.com/v1/artists?ids={",".join(ids)}', headers=H)
print(f"HTTP {r.status_code}")
if r.status_code == 200:
    arts = r.json().get('artists', [])
    print(f"Retornou {len(arts)} artistas")
    if arts:
        print(f"Campos do primeiro: {sorted(arts[0].keys())}")
        print(f"  popularity : {arts[0].get('popularity', '<MISSING>')}")
        print(f"  followers  : {arts[0].get('followers', '<MISSING>')}")
        print(f"  genres     : {arts[0].get('genres', '<MISSING>')}")
else:
    print(f"Body: {r.text[:300]}")

print("\n--- /tracks/{id} com token MARCOS (verificar popularity) ---")
r = requests.get('https://api.spotify.com/v1/tracks/7tFiyTwD0nx5a1eklYtX2J', headers=H)
print(f"HTTP {r.status_code}")
if r.status_code == 200:
    print(f"  track popularity: {r.json().get('popularity', '<MISSING>')}")

print("\nFIM. Cole o output.")
