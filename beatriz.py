# Supondo que o arquivo com as funções se chame "spotify_utils.py"
from functions import *

# --- Início do Script Principal ---

# 1. Criar a playlist
# A função 'criar_playlist' agora se chama 'create_playlist'.
playlist_id = create_playlist("Playlist da Bia")

# 2. Definir os artistas (top 20 mais populares)
# OBS: Dados da playlist Top Brasil captados no dia 08/08/2025
# A função 'csv_para_lista' agora se chama 'load_artists_from_csv'.
selected_artists = load_artists_from_csv("artistas_topbrasil_dados.csv", 20)

# 3. Criar uma lista com as top músicas desses artistas
music_list = []
for artist in selected_artists:
    # A função 'puxa_top_musicas' agora se chama 'extract_top_tracks_from_data'.
    music_list.append(extract_top_tracks_from_data(artist))

# 4. Achatar a lista de listas para manipulação
# A função 'achatar_lista_de_listas' agora se chama 'flatten_list_of_lists'.
music_list = flatten_list_of_lists(music_list)

# 5. Criar uma lista final com no máximo 100 músicas aleatórias
# A função 'aleatoriza_qtd' agora se chama 'get_random_sample'.
final_music_list = get_random_sample(music_list, 100)

print("Músicas selecionadas para a playlist:")
print(final_music_list)

# 6. Buscar as URIs das músicas selecionadas
# A função 'buscar_uris_das_musicas' agora se chama 'fetch_track_uris'.
track_uris = fetch_track_uris(final_music_list)

# 7. Adicionar as músicas à playlist criada
# A função 'adicionar_musicas_a_playlist' agora se chama 'add_tracks_to_playlist'.
add_tracks_to_playlist(playlist_id, track_uris)

# 8. Curtir as músicas da nova playlist
like_all_tracks_in_playlist(playlist_id)

print("\nProcesso finalizado! A playlist foi criada e as músicas foram adicionadas e curtidas.")