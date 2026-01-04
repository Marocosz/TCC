# create_beatriz_playlist.py

"""
================================================================================
MÓDULO DE GERAÇÃO DE PLAYLIST - PERSONA BEATRIZ (MAINSTREAM)
================================================================================

OBJETIVO DO ARQUIVO:
    Orquestrar a criação automática da playlist para o perfil "Beatriz" no Spotify.
    Este módulo implementa uma estratégia de seleção baseada em "Popularidade Absoluta",
    simulando um ouvinte que consome o que está em alta no momento (Top Hits).

RESPONSABILIDADES:
    1. Carregar artistas semente de um dataset CSV.
    2. Consultar a API do Spotify para obter as faixas mais populares desses artistas.
    3. Aplicar algoritmo de ordenação global por popularidade (Score 0-100).
    4. Filtrar duplicatas e selecionar o Top N.
    5. Criar a playlist na conta do usuário e salvar as músicas (Like).

COMUNICAÇÃO:
    - Entrada: Lê 'beatriz/artistas_topbrasil_dados.csv'.
    - Saída: Criação de playlist e likes na conta Spotify autenticada.
    - Dependências: Utiliza funções auxiliares de 'functions'.
================================================================================
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from functions import (
    load_artists_from_csv,
    get_random_sample,
    fetch_track_uris,
    create_playlist,
    add_tracks_to_playlist,
    like_tracks_slowly 
)

def main():
    """
    Controlador principal do fluxo de geração da playlist.
    
    Lógica de Negócio (Perfil Beatriz):
        Diferente de outros perfis que podem usar aleatoriedade, este fluxo
        coleta TODAS as músicas populares dos artistas listados, junta tudo em
        um único "pool" e ordena decrescentemente pelo índice de popularidade
        do Spotify. O resultado são as 100 músicas mais "Mainstream" possíveis
        dentro do universo de artistas fornecido.
    """
    
    # --- 1. CONFIGURAÇÕES ---
    # Definição de constantes para controle de escopo e limites da API
    print("--- PASSO 1: Carregando configurações para a 'Beatriz Mainstream' ---")
    
    CSV_FILE = "beatriz/artistas_topbrasil_dados.csv"
    PLAYLIST_NAME = "Top Hits Brasil (Input Beatriz)"
    FINAL_PLAYLIST_SIZE = 100 # Tamanho alvo da playlist final
    ARTIST_SOURCE_LIMIT = 100 # Limite de leitura do CSV para evitar timeouts
    
    print(f"Lógica: Criar um ranking de músicas por popularidade da FAIXA e selecionar o Top {FINAL_PLAYLIST_SIZE}.")
    print("-" * 40)

    # --- 2. CRIAÇÃO DO "UNIVERSO MUSICAL" ---
    # Etapa de ETL (Extract): Carrega dados brutos e enriquece via API
    print("\n--- PASSO 2: Coletando todas as top músicas de todos os artistas do CSV ---")
    
    all_artists = load_artists_from_csv(CSV_FILE, limit=ARTIST_SOURCE_LIMIT)
    
    # Validação crítica: Sem artistas, o processo não pode continuar
    if not all_artists:
        print(f"ERRO: Não foi possível carregar artistas do arquivo '{CSV_FILE}'.")
        return

    # Inicialização do Cliente Spotify
    # Requer variáveis de ambiente configuradas (SPOTIPY_CLIENT_ID, etc.)
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth())
    
    # Repositório temporário para os objetos completos de música (Metadados + Popularidade)
    all_tracks_pool = []
    
    for artist in all_artists:
        try:
            # Extração do ID necessário para o endpoint 'artist_top_tracks'
            artist_id = artist['uri'].split(':')[-1]
            
            # Integração Spotify:
            # Busca as 10 faixas mais populares do artista no mercado 'BR'.
            # Retorna uma lista de objetos 'track' contendo o campo 'popularity'.
            top_tracks_objects = sp.artist_top_tracks(artist_id, country="BR")['tracks']
            
            all_tracks_pool.extend(top_tracks_objects)
            print(f"  + Coletadas {len(top_tracks_objects)} músicas de '{artist['name']}'")
            
        except Exception as e:
            # Tolerância a falhas: Se um artista falhar, o script segue para o próximo
            print(f"  AVISO: Não foi possível buscar músicas de '{artist['name']}'. Erro: {e}")
            
    print(f"\nColetadas {len(all_tracks_pool)} músicas no total para o ranking.")
    
    # --- 3. RANKING POR POPULARIDADE DA MÚSICA ---
    # Lógica Central da Persona Beatriz:
    # Ordena o pool inteiro baseando-se no atributo 'popularity' (0 a 100) do objeto track.
    # reverse=True garante que as músicas com maior score fiquem no topo.
    print("\n--- PASSO 3: Ordenando todas as músicas por sua popularidade individual ---")

    all_tracks_pool.sort(key=lambda track: track['popularity'], reverse=True)
    
    print("Ranking de músicas criado com sucesso.")
    print("-" * 40)

    # --- 4. SELEÇÃO E DEDUPLICAÇÃO ---
    # Transforma o Ranking em uma lista final de nomes, removendo duplicatas.
    # Necessário pois artistas diferentes podem ter feats na mesma música, 
    # ou a mesma música pode aparecer em álbuns diferentes.
    print(f"\n--- PASSO 4: Selecionando as {FINAL_PLAYLIST_SIZE} músicas mais populares do ranking ---")
    
    final_track_names = []
    seen_tracks = set() # Set para busca O(1) na verificação de duplicidade
    
    for track in all_tracks_pool:
        track_name = track['name']
        
        if track_name not in seen_tracks:
            final_track_names.append(track_name)
            seen_tracks.add(track_name)
        
        # Interrompe o loop assim que atingir o tamanho desejado da playlist
        if len(final_track_names) >= FINAL_PLAYLIST_SIZE:
            break
            
    print(f"Selecionadas {len(final_track_names)} músicas únicas para a playlist.")
    print("-" * 40)
    
    # --- 5. PERSISTÊNCIA (PLAYLIST & LIKES) ---
    # Converte os nomes escolhidos em URIs e realiza as ações de escrita na conta.
    print(f"\n--- PASSO 5: Montando a playlist final ---")

    # Busca as URIs finais para os nomes selecionados
    track_uris = fetch_track_uris(final_track_names)
    if not track_uris: return

    # Criação da Playlist vazia
    playlist_id = create_playlist(PLAYLIST_NAME)
    
    if playlist_id:
        # Povoamento da Playlist
        add_tracks_to_playlist(playlist_id, track_uris)
        
        # Ação de "Like" (Salvar na biblioteca)
        # Executado com delay (slowly) para evitar Rate Limit da API
        print("\n--- PASSO 6: Curtindo as músicas (uma por uma) ---")
        like_tracks_slowly(track_uris)
    
    print("\n--- PROCESSO FINALIZADO! ---")
    print(f"Playlist '{PLAYLIST_NAME}' criada com sucesso.")

if __name__ == "__main__":
    main()