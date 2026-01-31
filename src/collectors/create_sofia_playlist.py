# TIPO DE ARQUIVO: RECEBE CSV

"""
================================================================================
ARQUITETURA DO TCC: GERADOR SOFIA (UNDERGROUND DEEP DIVE - LOOP FILL)
================================================================================

Objetivo do Arquivo:
    Gerar a playlist da Persona "Sofia", focada em Indie/Underground.
    O desafio aqui é a ESCASSEZ de dados: artistas desconhecidos tem poucas faixas.

Parte do Sistema:
    Collectors (Gerador de Dataset de Entrada).

Responsabilidades:
    1. Varredura Total: Coleta discografia completa (Álbuns + Singles).
    2. Estratégia de Preenchimento (Loop Fill):
       - Passada 1: Tenta pegar 8-13 músicas por artista.
       - Passada 2+: Se não encheu 200 slots, volta nos mesmos artistas e
         pega o "resto" do catálogo até completar.
    3. Ordenação Inversa: Prioriza músicas MENOS populares dentro do catálogo
       (Deep Cuts) mas a lista de artistas é ordenada do MENOR para o MAIOR.

Comunicação:
    - Entrada: CSV `data/raw/artistas_indie_dados.csv`.
    - Saída: Playlist 'Underground Deep Dive' no Spotify.

Uso:
    python src/collectors/create_sofia_playlist.py
"""

import sys
import os
import random
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# --- CONFIGURAÇÃO DE AMBIENTE ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
diretorio_src = os.path.dirname(diretorio_atual)
sys.path.append(diretorio_src)

from functions import (
    load_artists_from_csv,
    create_playlist,        
    add_tracks_to_playlist,
    like_tracks_slowly,
)

load_dotenv()

# Inicializa cliente
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-library-modify playlist-modify-public playlist-modify-private"
))

# --- CONFIGURAÇÕES ---
CONFIG = {
    "CSV_PATH": os.path.join(os.path.dirname(diretorio_src), "data", "raw", "artistas_indie_dados.csv"),
    "PLAYLIST_NAME": "Underground Deep Dive (Input Sofia)",
    "TOTAL_TARGET": 200,
    "TRACKS_PER_ARTIST_INITIAL": (8, 13) 
}

def clean_name(name):
    """Limpa nome para deduplicação simples, removendo sufixos."""
    return name.split(' -')[0].split(' (')[0].lower().strip()

def get_all_artist_tracks_sorted(artist_data):
    """
    Busca TODAS as faixas do artista e retorna ordenadas por popularidade CRESCENTE.

    Por que Crescente?
        Sofia busca o "Lado B", as joias escondidas. Queremos as músicas
        que os fãs hardcores conhecem, não os hits de rádio.

    Args:
        artist_data (dict): Dados do artista.

    Returns:
        list: Lista de dicionários [{'uri': ..., 'name': ..., 'popularity': ...}].
    """
    artist_id = artist_data.get('id')
    if not artist_id: return []

    try:
        # Busca catálogo (Album + Single)
        results = sp.artist_albums(artist_id, album_type='album,single', limit=50)
        albums = results['items']
        
        raw_uris = []
        for album in albums:
            tracks = sp.album_tracks(album['id'])
            for t in tracks['items']:
                raw_uris.append(t['uri'])
        
        raw_uris = list(set(raw_uris)) # Deduplica URIs
        
        # Fallback: Se não achar álbuns, pega Top Tracks (melhor que nada)
        if not raw_uris:
            top = sp.artist_top_tracks(artist_id, country='BR')['tracks']
            raw_uris = [t['uri'] for t in top]

        # Busca detalhes (Popularidade)
        full_tracks = []
        for i in range(0, len(raw_uris), 50):
            batch = raw_uris[i:i+50]
            if batch:
                res = sp.tracks(batch)
                full_tracks.extend([t for t in res['tracks'] if t])

        # Ordena: Menos popular -> Mais popular e retorna a lista completa
        # (O filtro de quantidade será feito no loop principal)
        full_tracks.sort(key=lambda x: x['popularity'])
        
        return full_tracks

    except Exception as e:
        print(f"    [Erro API] {artist_data['name']}: {e}")
        return []

def main():
    """
    Orquestrador da Playlist Sofia.
    Utiliza cache local para evitar múltiplas chamadas à API no Loop de Repescagem.
    """
    print("\n" + "="*60)
    print(f"INICIANDO GERADOR SOFIA (LOOP FILL): {CONFIG['PLAYLIST_NAME']}")
    print("="*60)

    # 1. Carregar Artistas
    all_artists = load_artists_from_csv(CONFIG['CSV_PATH'], limit=400)
    if not all_artists: return

    # Ordena: Menor Pop -> Maior Pop (Começa pelos mais desconhecidos)
    all_artists.sort(key=lambda x: int(x.get('popularity', 0)))
    
    print(f"Base: {len(all_artists)} artistas (Start Pop: {all_artists[0]['popularity']})")

    final_playlist_uris = []
    seen_uris = set()
    seen_names = set() # Controle de nome global para evitar covers/remixes

    # Cache local para não chamar API duas vezes para o mesmo artista no loop
    # Formato: { artist_id: [lista_de_tracks_ordenadas] }
    artist_tracks_cache = {}

    print("\n--- Fase 1: Coleta Inicial (8 a 13 faixas) ---")

    # Loop Principal (Repete até encher ou não ter mais nada)
    round_count = 1
    
    while len(final_playlist_uris) < CONFIG['TOTAL_TARGET']:
        
        tracks_added_in_round = 0
        
        for artist in all_artists:
            if len(final_playlist_uris) >= CONFIG['TOTAL_TARGET']: break
            
            # Carrega catálogo (se não estiver em cache)
            a_id = artist['id']
            if a_id not in artist_tracks_cache:
                print(f"  [Cache] Baixando discografia de {artist['name']}...")
                artist_tracks_cache[a_id] = get_all_artist_tracks_sorted(artist)
            
            # Recupera faixas disponíveis
            available_tracks = artist_tracks_cache[a_id]
            
            # Define quantas pegar nesta rodada
            if round_count == 1:
                quota = random.randint(CONFIG['TRACKS_PER_ARTIST_INITIAL'][0], CONFIG['TRACKS_PER_ARTIST_INITIAL'][1])
            else:
                # Nas rodadas seguintes, pega um pouco de cada vez para distribuir
                # o preenchimento entre todos os artistas restantes
                quota = 3 
            
            added_now = 0
            for track in available_tracks:
                if added_now >= quota: break
                
                # Checagens de duplicidade
                t_uri = track['uri']
                t_name_clean = clean_name(track['name'])
                
                if t_uri not in seen_uris and t_name_clean not in seen_names:
                    final_playlist_uris.append(t_uri)
                    seen_uris.add(t_uri)
                    seen_names.add(t_name_clean)
                    added_now += 1
                    tracks_added_in_round += 1
            
            if added_now > 0:
                print(f"    > {artist['name']}: +{added_now} faixas (Total Global: {len(final_playlist_uris)})")

        # Verifica se o loop travou (não conseguiu adicionar nada em uma rodada inteira)
        if tracks_added_in_round == 0:
            print("\n[!] Alerta: Discografias esgotadas! Não há mais músicas únicas disponíveis.")
            break
            
        round_count += 1
        print(f"\n--- Iniciando Rodada {round_count} (Buscando sobras...) ---")

    # Finalização
    print("\n" + "-"*40)
    print(f"RESUMO FINAL:")
    print(f"Total de Músicas: {len(final_playlist_uris)}")
    print("-" * 40)
    
    if len(final_playlist_uris) < 50:
        print("[!] Erro: Playlist muito pequena mesmo após repescagem.")
        return

    playlist_id = create_playlist(CONFIG['PLAYLIST_NAME'])
    if playlist_id:
        add_tracks_to_playlist(playlist_id, final_playlist_uris)
        print(f"\n--- Aplicando 'Likes' na conta... ---")
        like_tracks_slowly(final_playlist_uris)
        
    print(f"\n✅ SUCESSO! Playlist Sofia preenchida.")

if __name__ == "__main__":
    main()