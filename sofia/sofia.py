import random
import math
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from functions import * # Importa todas as nossas ferramentas

def distribuir_musicas_entre_artistas(total_musicas: int, num_artistas: int) -> list:
    """
    Função auxiliar que distribui um número total de músicas de forma
    aleatória entre um número de artistas.
    """
    if num_artistas == 0: return []
    distribuicao = [0] * num_artistas
    for _ in range(total_musicas):
        indice_artista = random.randint(0, num_artistas - 1)
        distribuicao[indice_artista] += 1
    return distribuicao

def main():
    """
    Função principal que cria uma nova playlist de 100 músicas com base
    na lógica de curadoria "50/50", com garantia de tamanho.
    """
    # --- 1. PAINEL DE CONTROLE (CONFIGURAÇÕES) ---
    print("--- PASSO 1: Carregando configurações da 'Curadoria 50/50' ---")
    
    # IMPORTANTE: Cole aqui a URL da playlist que servirá como base
    PLAYLIST_URL_SEMENTE = "https://open.spotify.com/playlist/5m7jvWtwE8OJ9DgzU6jhUu?si=f4d4bec3da7a4c58"
    
    NOVO_PLAYLIST_NAME = "playlist Indie Alternativa (Input Sofia)"
    FINAL_PLAYLIST_SIZE = 100

    print(f"Playlist base: {PLAYLIST_URL_SEMENTE}")
    print(f"Nova playlist a ser criada: {NOVO_PLAYLIST_NAME}")
    print("-" * 40)

    # --- 2. COLETAR E CLASSIFICAR OS ARTISTAS DA PLAYLIST BASE ---
    print("\n--- PASSO 2: Coletando e classificando os artistas da playlist base ---")
    
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-read-private"))
    
    try:
        artist_ids_map = get_artists_from_playlist(extract_spotify_playlist_id(PLAYLIST_URL_SEMENTE))
        todos_os_artistas = get_full_artist_profiles(artist_ids_map)
        todos_os_artistas.sort(key=lambda x: x['popularity'], reverse=True)
        
        ponto_de_corte = len(todos_os_artistas) // 2
        artistas_populares = todos_os_artistas[:ponto_de_corte]
        artistas_nicho = todos_os_artistas[ponto_de_corte:]

        print(f"Encontrados {len(todos_os_artistas)} artistas. Divisão:")
        print(f"  - {len(artistas_populares)} artistas na 'metade superior' (mais populares)")
        print(f"  - {len(artistas_nicho)} artistas na 'metade inferior' (menos populares)")
        print("-" * 40)

    except Exception as e:
        print(f"ERRO: Não foi possível ler ou processar os artistas da playlist base. Erro: {e}")
        return

    # --- 3. DISTRIBUIR O "ORÇAMENTO" DE 100 MÚSICAS ---
    print("\n--- PASSO 3: Distribuindo aleatoriamente a quantidade de músicas por artista ---")
    
    orcamento_populares = FINAL_PLAYLIST_SIZE // 2
    orcamento_nicho = FINAL_PLAYLIST_SIZE - orcamento_populares

    distribuicao_populares = distribuir_musicas_entre_artistas(orcamento_populares, len(artistas_populares))
    distribuicao_nicho = distribuir_musicas_entre_artistas(orcamento_nicho, len(artistas_nicho))

    print(f"{orcamento_populares} músicas serão distribuídas entre os artistas populares.")
    print(f"{orcamento_nicho} músicas serão distribuídas entre os artistas de nicho.")
    print("-" * 40)
    
    # --- 4. COLETAR MÚSICAS COM A LÓGICA CONDICIONAL ---
    print("\n--- PASSO 4: Coletando as músicas com a lógica condicional ---")
    
    track_names_pool = []

    print("\nProcessando artistas da 'metade superior'...")
    for artist, total_a_pegar in zip(artistas_populares, distribuicao_populares):
        if total_a_pegar == 0: continue
        artist_top_tracks = artist.get('top_tracks', [])
        if len(artist_top_tracks) < 3: continue
        
        pool_musicas = artist_top_tracks[3:]
        selecao = get_random_sample(pool_musicas, total_a_pegar)
        track_names_pool.extend(selecao)
        print(f"  + {len(selecao)} músicas 'lado B' de '{artist['name']}'")

    print("\nProcessando artistas da 'metade inferior'...")
    for artist, total_a_pegar in zip(artistas_nicho, distribuicao_nicho):
        if total_a_pegar == 0: continue
        artist_top_tracks = artist.get('top_tracks', [])
        
        pool_musicas = artist_top_tracks
        selecao = get_random_sample(pool_musicas, total_a_pegar)
        track_names_pool.extend(selecao)
        print(f"  + {len(selecao)} músicas aleatórias de '{artist['name']}'")

    # --- 5. MONTAGEM FINAL COM GARANTIA DE 100 MÚSICAS ---
    print("\n" + "-" * 40)
    print(f"\n--- PASSO 5: Montando a playlist final ---")

    unique_tracks = list(set(track_names_pool))
    print(f"Total de {len(unique_tracks)} músicas únicas selecionadas na coleta inicial.")

    # MUDANÇA: Lógica completa de preenchimento para garantir 100 músicas
    if len(unique_tracks) < FINAL_PLAYLIST_SIZE:
        print(f"Faltam {FINAL_PLAYLIST_SIZE - len(unique_tracks)} músicas. Buscando preenchimento de contexto...")
        
        # O pote de sobras vem APENAS dos artistas já selecionados
        sobras_pool = []
        for artist in (artistas_populares + artistas_nicho):
            sobras_pool.extend(artist.get('top_tracks', []))
        
        # Limpa o pote de sobras, removendo as músicas que já temos
        sobras_limpas = list(set(sobras_pool) - set(unique_tracks))
        
        musicas_necessarias = FINAL_PLAYLIST_SIZE - len(unique_tracks)
        
        # Pega o que falta do pote de sobras contextualizado
        preenchimento = get_random_sample(sobras_limpas, musicas_necessarias)
        unique_tracks.extend(preenchimento)
        print(f"Adicionadas {len(preenchimento)} músicas extras do mesmo contexto de artistas.")

    # Ajuste final para garantir o tamanho exato
    if len(unique_tracks) > FINAL_PLAYLIST_SIZE:
        final_track_names = get_random_sample(unique_tracks, FINAL_PLAYLIST_SIZE)
    else:
        final_track_names = unique_tracks
    
    print(f"Tamanho final da playlist: {len(final_track_names)} músicas.")

    track_uris = fetch_track_uris(final_track_names)
    if not track_uris: return

    playlist_id = create_playlist(NOVO_PLAYLIST_NAME)
    if playlist_id:
        add_tracks_to_playlist(playlist_id, track_uris)
        print("\n--- PASSO 6: Curtindo as músicas (uma por uma) ---")
        like_tracks_slowly(track_uris)
    
    print("\n--- PROCESSO FINALIZADO! ---")

if __name__ == "__main__":
    main()