# gerar_relatorio_artistas.py

"""
Script principal para gerar um relatório CSV com informações detalhadas
dos artistas presentes na playlist "Top Brasil" do Spotify.
"""

# Importa as ferramentas necessárias do nosso módulo de funções
from functions import (
    extract_spotify_playlist_id,
    get_artists_from_playlist,
    get_full_artist_profiles,
    save_artists_to_csv
)

def main():
    """
    Função principal que orquestra todo o processo de geração do relatório.
    """
    # --- Configurações ---
    # Defina aqui a URL da playlist que você quer analisar.
    playlist_url = "https://open.spotify.com/playlist/5wguuPKXKvZr4AqIMt1nF0?si=b0c93450b3cd4bdc"
    
    # Defina o nome do arquivo que será salvo.
    output_csv_file = "artistas_topbrasil_dados.csv"

    print("--- Iniciando processo de geração de relatório de artistas ---")

    # Passo 1: Extrair o ID da URL da playlist.
    playlist_id = extract_spotify_playlist_id(playlist_url)
    print(playlist_id)
    
    # Passo 2: Buscar todos os artistas únicos da playlist.
    # A função já lida com a busca e a paginação internamente.
    unique_artists = get_artists_from_playlist(playlist_id)

    
    # Passo 3: Obter os perfis detalhados para cada artista encontrado.
    # A função já busca seguidores, popularidade, gêneros e top músicas.
    full_profiles = get_full_artist_profiles(unique_artists)
    
    # Passo 4: Salvar os dados compilados em um arquivo CSV, ordenado por popularidade.
    save_artists_to_csv(full_profiles, output_csv_file, sort_by='popularity')
    
    print("\n--- Processo finalizado com sucesso! ---")


# Garante que a função main() só será executada quando o script for chamado diretamente.
if __name__ == "__main__":
    main()