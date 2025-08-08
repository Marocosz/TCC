from functions import (csv_para_lista, puxa_top_musicas, achatar_lista_de_listas, aleatoriza_qtd, 
adicionar_musicas_a_playlist, extract_spotify_playlist_id, buscar_uris_das_musicas)

a = csv_para_lista("artistas_topbrasil_ordem_popularidade.csv", 20)



lista_musicas = []

for artista in a:
    lista_musicas.append(puxa_top_musicas(artista))

lista_musicas_achatada = achatar_lista_de_listas(lista_musicas)

print(len(lista_musicas_achatada))

lista_final = aleatoriza_qtd(lista_musicas_achatada, 100)

print(len(lista_final))
print(lista_final)

uris_lista_final = buscar_uris_das_musicas(lista_final)

print(uris_lista_final)

adicionar_musicas_a_playlist("https://open.spotify.com/playlist/53LYfNVZn37jOe9YwMLI3v?si=7f64fbb41af544a6", uris_lista_final)