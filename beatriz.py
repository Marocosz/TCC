from functions import (csv_para_lista, puxa_top_musicas, achatar_lista_de_listas, aleatoriza_qtd, 
adicionar_musicas_a_playlist, like_em_tracks, buscar_uris_das_musicas, criar_playlist)

# criar a playlist
id_playlist = criar_playlist("Playlist da Bia")

# Definindo os artistas (top 20 mais populares)
# OBS: Dados da playlist Top Brasil captados no dia 08/08
artistas_selecionados = csv_para_lista("artistas_topbrasil_ordem_popularidade.csv", 20)

# Cria uma lista com as top músicas desses artistas
lista_musicas = []
for artista in artistas_selecionados:
    lista_musicas.append(puxa_top_musicas(artista))

# Achata a lista para manipulação
lista_musicas = achatar_lista_de_listas(lista_musicas)

# Lista final com no máximo 100 músicas aleatórias das (len(lista_musicas)) escolhidas anteriormente
lista_musicas_final = aleatoriza_qtd(lista_musicas, 100)

print(lista_musicas_final)

# URIs das músicas selecionadas
uris_musicas = buscar_uris_das_musicas(lista_musicas_final)

# Adicionar músicas a playlist criada
adicionar_musicas_a_playlist(id_playlist, uris_musicas)

# Curtir músicas adicionadas
like_em_tracks(uris_musicas)