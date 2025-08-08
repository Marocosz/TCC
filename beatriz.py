from functions import criar_playlist, extract_spotify_playlist_id, adicionar_musicas_a_playlist

# criar_playlist("Teste")

id_playlist = extract_spotify_playlist_id("https://open.spotify.com/playlist/53LYfNVZn37jOe9YwMLI3v?si=41a0d170d8d7402d")
print(id_playlist)

adicionar_musicas_a_playlist(id_playlist, ["spotify:track:5LLJntbc3SvdXcYhRJZwKP"])