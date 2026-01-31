# TIPO DE ARQUIVO: RECEBE CSV

"""
================================================================================
ARQUITETURA DO TCC: GERADOR RICARDO (DEEP DIVE / DISCOGRAFIA REAL / STUDIO)
================================================================================

Objetivo do Arquivo:
    Gerar a playlist da Persona "Ricardo", que valoriza Álbuns Completos,
    versões de estúdio originais e rejeita singles soltos ou coletâneas.

Parte do Sistema:
    Collectors (Gerador de Dataset de Entrada).

Responsabilidades:
    1. Mineração Profunda: Escanear álbuns inteiros (não apenas Top Tracks).
    2. Curadoria: Filtrar versões "Live", "Deluxe", "Remaster" para manter a pureza.
    3. Distribuição Controlada: 70% Rock/Metal vs 30% Outros.
    4. Seleção: Escolher entre 8 e 16 músicas POR ARTISTA (alta profundidade).

Comunicação:
    - Entrada: CSV `data/raw/artistas_classicos_dados.csv`.
    - Saída: Playlist 'Clássicos Deep Dive' no Spotify.

Uso:
    python src/collectors/create_ricardo_playlist.py
"""

import sys
import os
import random
import ast
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# --- CONFIGURAÇÃO DE AMBIENTE ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
diretorio_src = os.path.dirname(diretorio_atual)
sys.path.append(diretorio_src)

# Importa funções auxiliares
from functions import (
    load_artists_from_csv,
    create_playlist,        
    add_tracks_to_playlist,
    like_tracks_slowly,
)

# Carrega variáveis de ambiente para Autenticação
load_dotenv()

# Inicializa cliente Spotify dedicado para este script
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-library-modify playlist-modify-public playlist-modify-private"
))

# --- CONFIGURAÇÕES ---
CONFIG = {
    "CSV_PATH": os.path.join(os.path.dirname(diretorio_src), "data", "raw", "artistas_classicos_dados.csv"),
    "PLAYLIST_NAME": "Clássicos Deep Dive (Input Ricardo)",
    "TOTAL_TARGET": 200,
    "MINORITY_PERCENTAGE": 0.30, # 30% Outros
    "TRACKS_PER_ARTIST": (8, 16), # Busca REAIS entre 8 e 16
    
    # [NOVO] Palavras proibidas para garantir "Versão de Estúdio"
    "FORBIDDEN_KEYWORDS": [
        "live", "ao vivo", "tour", "concert", "vivo", "acústico", "mtv", # Shows
        "soundtrack", "motion picture", "trilha sonora", "film", # Filmes (Remove Taron Egerton/Glee)
        "deluxe", "anniversary", "edition", "expanded", "demos", # Versões inchadas
        "remix", "mix", "edit", "instrumental" # Variações
    ]
}

def clean_name(name):
    """
    Normaliza o nome da faixa para permitir deduplicação.

    Args:
        name (str): Linkin Park - In The End (Remastered 2020)
    
    Returns:
        str: linkin park-in the end
    """
    return name.split(' -')[0].split(' (')[0].lower().strip()

def is_content_safe(name):
    """
    Filtro de Qualidade: Rejeita faixas com palavras-chave indesejadas (Live, Deluxe).

    Por que existe:
        Ricardo odeia ouvir aplausos no meio da música ou versões
        instrumentais/demo que não sejam a obra original.

    Args:
        name (str): Nome da música ou álbum.

    Returns:
        bool: True se for seguro (aprovado), False se for proibido.
    """
    n = name.lower()
    for bad_word in CONFIG["FORBIDDEN_KEYWORDS"]:
        if bad_word in n:
            return False
    return True

def is_rock_ecosystem(artist_genres):
    """
    Classificador de Gênero Simplificado.
    
    Lógica:
        Varre a lista de gêneros do artista procurando palavras-chave
        do universo Rock/Metal/Blues/Punk.

    Returns:
        bool: True se for do ecossistema Rock.
    """
    if isinstance(artist_genres, str):
        try: genres_list = ast.literal_eval(artist_genres)
        except: genres_list = [artist_genres.lower()]
    elif isinstance(artist_genres, list): genres_list = artist_genres
    else: return False

    if not genres_list: return False

    rock_keywords = [
        'rock', 'metal', 'punk', 'grunge', 'heavy', 'thrash', 
        'psychedelic', 'hard rock', 'shoegaze', 'new wave', 'britpop',
        'indie', 'alternative', 'blues rock', 'garage', 'rockabilly'
    ]

    for g in genres_list:
        if any(k in str(g).lower() for k in rock_keywords):
            return True
    return False

def extract_deep_discography(artist_data, target_count):
    """
    Realiza a mineração profunda (Deep Dive) na discografia do artista.

    O que faz:
        1. Busca todos os álbuns do tipo 'album' (nada de singles).
        2. Ordena por data de lançamento (cronológico).
        3. Itera sobre cada álbun extraindo faixas limpas (sem Live/Deluxe).
        4. Coleta IDs até atingir a meta (target_count).
        5. Ordena o resultado final por popularidade para garantir os melhores deep cuts.

    Args:
        artist_data (dict): Dicionário do artista.
        target_count (int): Quantas músicas queremos deste artista (ex: 12).

    Returns:
        list: Lista de URIs do Spotify.
    """
    artist_id = artist_data.get('id')
    artist_name = artist_data.get('name')
    if not artist_id: return []

    try:
        # 1. Busca Álbuns (Usa 'album_type=album' para ignorar singles e compilations)
        # Isso elimina a maioria das trilhas sonoras e coletâneas
        results = sp.artist_albums(artist_id, album_type='album', limit=50)
        albums = results['items']
        
        # Ordena álbuns por DATA (Prioriza lançamentos originais sobre remasters recentes)
        albums.sort(key=lambda x: x['release_date'])
        
        candidate_uris = []
        
        # 2. Coleta faixas dos álbuns com filtro de nome
        for album in albums:
            # Filtro no Nome do Álbum (ex: Remove "Live at Wembley")
            if not is_content_safe(album['name']):
                continue
            
            tracks = sp.album_tracks(album['id'])
            for t in tracks['items']:
                # Filtro no Nome da Música e filtro de Artista Principal
                # (Garante que não pegamos faixas onde ele é apenas feat irrelevante, embora album_tracks geralmente seja safe)
                if is_content_safe(t['name']):
                    candidate_uris.append(t['uri'])

        # Deduplicação de URIs
        candidate_uris = list(set(candidate_uris))
        
        if not candidate_uris:
            return []

        # 3. Batch Process para pegar Popularidade
        full_tracks_data = []
        for i in range(0, len(candidate_uris), 50):
            batch = candidate_uris[i:i+50]
            if not batch: continue
            
            details = sp.tracks(batch)
            for track in details['tracks']:
                if track:
                    full_tracks_data.append(track)

        # 4. Ordenação e Deduplicação por NOME LIMPO
        full_tracks_data.sort(key=lambda x: x['popularity'], reverse=True)
        
        unique_tracks = []
        seen_names = set()
        
        for track in full_tracks_data:
            # Limpa o nome (remove 'Remastered', etc)
            name_key = clean_name(track['name'])
            
            # Verifica novamente segurança do nome (redundância)
            if not is_content_safe(track['name']):
                continue

            if name_key not in seen_names:
                unique_tracks.append(track['uri'])
                seen_names.add(name_key)
            
            if len(unique_tracks) >= target_count:
                break
                
        return unique_tracks

    except Exception as e:
        print(f"    [Erro API] Falha ao processar discografia de {artist_name}: {e}")
        return []

def distribuir_cotas_organicas(target_tracks, artist_pool, min_tracks, max_tracks):
    """
    Sorteia quantos deep cuts pegar de cada artista.
    """
    selected_plan = [] 
    current_count = 0
    
    pool_sorted = sorted(artist_pool, key=lambda x: int(x.get('popularity', 0)), reverse=True)

    for artist in pool_sorted:
        if current_count >= target_tracks: break
        remaining = target_tracks - current_count
        
        # Sorteio orgânico entre 8 e 16
        qtd = random.randint(min_tracks, max_tracks)
        if qtd > remaining: qtd = remaining
        
        if qtd > 0:
            selected_plan.append((artist, qtd))
            current_count += qtd
            
    return selected_plan

def main():
    """
    Orquestrador da Playlist Ricardo.
    """
    print("\n" + "="*60)
    print(f"INICIANDO GERADOR RICARDO (DEEP DIVE / STUDIO): {CONFIG['PLAYLIST_NAME']}")
    print("="*60)

    # 1. Carregar Artistas
    all_artists = load_artists_from_csv(CONFIG['CSV_PATH'], limit=800)
    if not all_artists: return

    # 2. Classificação
    rock_group = []
    others_group = []

    print("--- Classificando Ecossistemas ---")
    for artist in all_artists:
        if is_rock_ecosystem(artist.get('genres', [])):
            rock_group.append(artist)
        else:
            others_group.append(artist)
            
    print(f" [Rock]: {len(rock_group)} artistas.")
    print(f" [Outros]: {len(others_group)} artistas.")

    # 3. Metas
    target_others = int(CONFIG['TOTAL_TARGET'] * CONFIG['MINORITY_PERCENTAGE']) # 60
    target_rock = CONFIG['TOTAL_TARGET'] - target_others # 140

    # 4. Planejamento
    plan_rock = distribuir_cotas_organicas(
        target_rock, rock_group, 
        CONFIG['TRACKS_PER_ARTIST'][0], CONFIG['TRACKS_PER_ARTIST'][1]
    )
    
    plan_others = distribuir_cotas_organicas(
        target_others, others_group, 
        CONFIG['TRACKS_PER_ARTIST'][0], CONFIG['TRACKS_PER_ARTIST'][1]
    )

    full_plan = plan_rock + plan_others
    random.shuffle(full_plan)

    # 5. Coleta DEEP DIVE
    final_playlist_uris = []
    seen_uris = set()
    used_artist_ids = set([p[0]['id'] for p in full_plan]) # Rastreia quem já foi usado

    print("\n--- Extraindo Discografia (Filtrando Live/Deluxe/Soundtrack) ---")
    
    for i, (artist, quota) in enumerate(full_plan):
        tracks = extract_deep_discography(artist, quota)
        
        added = 0
        for uri in tracks:
            if uri not in seen_uris:
                final_playlist_uris.append(uri)
                seen_uris.add(uri)
                added += 1
        
        tipo = "ROCK" if is_rock_ecosystem(artist.get('genres')) else "OUTROS"
        print(f"  > [{i+1}/{len(full_plan)}] {artist['name']} ({tipo}): {added} faixas (Meta: {quota})")

    # 6. Rede de Segurança (Garantir 200 Músicas)
    # Como filtramos 'Live' e 'Deluxe', pode ser que alguns artistas entreguem menos que a cota.
    # Se faltar música, pegamos novos artistas do CSV.
    
    while len(final_playlist_uris) < CONFIG['TOTAL_TARGET']:
        deficit = CONFIG['TOTAL_TARGET'] - len(final_playlist_uris)
        print(f"\n[!] Déficit de {deficit} músicas. Buscando artistas extras no CSV...")
        
        # Procura artistas no pool original que ainda não usamos
        found_new = False
        sorted_all = sorted(all_artists, key=lambda x: int(x.get('popularity', 0)), reverse=True)
        
        for artist in sorted_all:
            if artist['id'] not in used_artist_ids:
                # Tenta pegar entre 5 e 10 músicas desse novo artista
                quota_extra = min(deficit, random.randint(5, 10))
                
                print(f"    + Adicionando reserva: {artist['name']} (Tentando {quota_extra})")
                tracks = extract_deep_discography(artist, quota_extra)
                
                added_extra = 0
                for uri in tracks:
                    if uri not in seen_uris:
                        final_playlist_uris.append(uri)
                        seen_uris.add(uri)
                        added_extra += 1
                
                if added_extra > 0:
                    used_artist_ids.add(artist['id'])
                    found_new = True
                    deficit -= added_extra
                
                if len(final_playlist_uris) >= CONFIG['TOTAL_TARGET']:
                    break
        
        if not found_new:
            print("[!] Alerta Crítico: Não há mais artistas no CSV para completar a playlist.")
            break

    # 7. Finalização
    print("\n" + "-"*40)
    print(f"RESUMO FINAL:")
    print(f"Total de Músicas: {len(final_playlist_uris)}")
    print("-" * 40)
    
    if len(final_playlist_uris) < 50:
        print("[!] Erro: Playlist muito pequena.")
        return

    playlist_id = create_playlist(CONFIG['PLAYLIST_NAME'])
    if playlist_id:
        add_tracks_to_playlist(playlist_id, final_playlist_uris)
        print(f"\n--- Aplicando 'Likes' na conta... ---")
        like_tracks_slowly(final_playlist_uris)
        
    print(f"\n✅ SUCESSO! Playlist Deep Dive do Ricardo criada.")

if __name__ == "__main__":
    main()