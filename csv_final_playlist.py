# analisar_playlist.py

import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from dotenv import load_dotenv
import csv

# Carrega as credenciais do ambiente
load_dotenv()

# --- Função Auxiliar ---
def ms_para_min_seg(ms):
    """Converte milissegundos para um formato legível 'min:seg'."""
    if not isinstance(ms, (int, float)):
        return "0:00"
    total_segundos = int(ms / 1000)
    minutos = total_segundos // 60
    segundos = total_segundos % 60
    return f"{minutos}:{segundos:02}"

# --- Função Principal ---
def analisar_e_salvar_playlist(playlist_url: str, output_csv_file: str):
    print("--- Iniciando análise da playlist (versão robusta) ---")
    
    try:
        # --- 1. BUSCAR MÚSICAS (com Auth de Usuário) ---
        print("Buscando todas as músicas da playlist...")
        
        scope = "playlist-read-private"
        sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
        
        playlist_id = playlist_url.split('/')[-1].split('?')[0]
        
        resultados = sp_user.playlist_items(playlist_id)
        itens_playlist = resultados['items']
        while resultados['next']:
            resultados = sp_user.next(resultados)
            itens_playlist.extend(resultados['items'])
            
        print(f"Total de {len(itens_playlist)} itens encontrados na playlist.")
        
        tracks = [item['track'] for item in itens_playlist if item and item.get('track')]
        
        # --- 2. BUSCAR DETALHES DOS ARTISTAS (com Auth de Aplicativo) ---
        print("Buscando detalhes dos artistas em lote...")
        
        sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

        artist_ids = list(set(
            artist['id'] for track in tracks for artist in track['artists'] if artist and artist.get('id')
        ))
        
        artist_details_map = {}
        for i in range(0, len(artist_ids), 50):
            batch_ids = artist_ids[i:i+50]
            artist_results = sp_app.artists(batch_ids)
            for artist in artist_results['artists']:
                artist_details_map[artist['id']] = artist
        
        print(f"Detalhes obtidos para {len(artist_details_map)} artistas.")

        # --- 3. MONTAR OS DADOS PARA O CSV ---
        print("Montando os dados para o arquivo CSV...")
        dados_finais_para_csv = []
        
        for track in tracks:
            if not track: continue

            primary_artist_info = track['artists'][0] if track['artists'] else {}
            primary_artist_id = primary_artist_info.get('id')
            primary_artist_details = artist_details_map.get(primary_artist_id, {})
            all_artist_names = "; ".join([artist['name'] for artist in track['artists']])

            linha = {
                'track_name': track['name'],
                'track_popularity': track['popularity'],
                'primary_artist_name': primary_artist_info.get('name', 'N/A'),
                'artist_popularity': primary_artist_details.get('popularity', 0), # Popularidade do artista principal
                'artist_followers': primary_artist_details.get('followers', {}).get('total', 0), # Seguidores
                'all_artists': all_artist_names,
                'artist_genres': "; ".join(primary_artist_details.get('genres', [])),
                'album_name': track['album']['name'],
                'album_release_date': track['album']['release_date'],
                'duration_readable': ms_para_min_seg(track.get('duration_ms')),
                'is_explicit': track['explicit'],
                'track_url': track['external_urls'].get('spotify', ''),
                'track_uri': track['uri']
            }
            dados_finais_para_csv.append(linha)

        # --- 4. SALVAR ARQUIVO CSV ---
        if not dados_finais_para_csv:
            print("Nenhum dado de música foi coletado.")
            return

        colunas = [
            'track_name', 'primary_artist_name', 'all_artists', 'album_name', 
            'track_popularity', 'artist_popularity', 'artist_followers', 'artist_genres', 
            'album_release_date', 'duration_readable', 'is_explicit', 'track_url', 'track_uri'
        ]
        
        print(f"Salvando dados no arquivo '{output_csv_file}'...")
        with open(output_csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=colunas)
            writer.writeheader()
            writer.writerows(dados_finais_para_csv)
            
        print(f"\n--- SUCESSO! Análise concluída e arquivo '{output_csv_file}' salvo. ---")

    except Exception as e:
        print(f"Ocorreu um erro: {e}")

# --- SEÇÃO PRINCIPAL PARA EXECUTAR O SCRIPT ---
if __name__ == '__main__':
    URL_DA_PLAYLIST = "https://open.spotify.com/playlist/6ayjzXrXpVQoea0rVvtGCI?si=f2aa9a2e75e04533"
    NOME_DO_ARQUIVO_CSV = "analise_playlist.csv"
    analisar_e_salvar_playlist(URL_DA_PLAYLIST, NOME_DO_ARQUIVO_CSV)