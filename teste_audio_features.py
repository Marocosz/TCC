# teste_final_analise.py

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import csv

load_dotenv()

# --- Funções Auxiliares (simplificadas) ---
def ms_para_min_seg(ms):
    if not isinstance(ms, (int, float)): return "0:00"
    segundos = int((ms / 1000) % 60)
    minutos = int((ms / (1000 * 60)) % 60)
    return f"{minutos}:{segundos:02}"

# --- Função Principal ---
def analisar_playlist_final_test(playlist_url: str, output_csv_file: str):
    print("--- INICIANDO TESTE FINAL (TUDO COM AUTH DE USUÁRIO) ---")
    
    try:
        # --- 1. AUTENTICAÇÃO ÚNICA DE USUÁRIO ---
        # Pedimos todas as permissões de leitura de uma vez
        scope = "playlist-read-private user-library-read"
        sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
        print("Autenticação de usuário criada.")

        # --- 2. BUSCAR MÚSICAS DA PLAYLIST ---
        print("Buscando todas as músicas da playlist...")
        playlist_id = playlist_url.split('/')[-1].split('?')[0]
        
        resultados = sp_user.playlist_items(playlist_id)
        itens_playlist = resultados['items']
        while resultados['next']:
            resultados = sp_user.next(resultados)
            itens_playlist.extend(resultados['items'])
            
        print(f"Total de {len(itens_playlist)} itens encontrados.")
        
        tracks = [item['track'] for item in itens_playlist if item and item.get('track')]
        track_ids = [track['id'] for track in tracks if track and track.get('id')]
        
        # --- 3. BUSCAR DADOS ADICIONAIS (AINDA USANDO AUTH DE USUÁRIO) ---
        print("\nTentando buscar dados adicionais com o token de usuário...")

        # Teste 3a: Audio Features
        print("--> Testando 'audio_features'...")
        audio_features = sp_user.audio_features(track_ids)
        audio_features_map = {feat['id']: feat for feat in audio_features if feat}
        print(f"--> SUCESSO! Obtidos audio features para {len(audio_features_map)} músicas.")

        # Teste 3b: Detalhes dos Artistas
        print("\n--> Testando 'artists'...")
        artist_ids = list(set(artist['id'] for track in tracks for artist in track['artists'] if artist and artist.get('id')))
        artist_details_map = {}
        for i in range(0, len(artist_ids), 50):
            batch = artist_ids[i:i+50]
            artist_results = sp_user.artists(batch)
            for artist in artist_results['artists']:
                artist_details_map[artist['id']] = artist
        print(f"--> SUCESSO! Obtidos detalhes para {len(artist_details_map)} artistas.")
        
        # Se chegamos até aqui, o resto vai funcionar.
        # ... (O código para montar e salvar o CSV continua o mesmo)
        print("\nMontando e salvando o arquivo CSV...")
        # ...

        print(f"\n--- ✅ SUCESSO TOTAL! ---")
        print(f"O script funcionou e o arquivo '{output_csv_file}' foi gerado (ou seria gerado).")


    except Exception as e:
        print("\n--- ❌ FALHA NO TESTE FINAL! ---")
        print("Ocorreu um erro:")
        print(e)

# --- SEÇÃO PRINCIPAL ---
if __name__ == '__main__':
    URL_DA_PLAYLIST = "https://open.spotify.com/playlist/6ayjzXrXpVQoea0rVvtGCI?si=f2aa9a2e75e04533"
    NOME_DO_ARQUIVO_CSV = "analise_teste_final.csv"
    analisar_playlist_final_test(URL_DA_PLAYLIST, NOME_DO_ARQUIVO_CSV)