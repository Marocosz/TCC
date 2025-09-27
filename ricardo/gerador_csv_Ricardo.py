# Executado no dia 27/09/2025

"""
Script principal para gerar um relatório CSV com informações detalhadas
dos artistas presentes em MÚLTIPLAS playlists do Spotify.
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
    # Coloque aqui a lista de URLs das playlists que você quer analisar.
    # Adicione quantas URLs quiser.
    playlist_urls = [
        "https://open.spotify.com/playlist/5rehXNZUXxbia3eHmlcFz1?si=e1fa21a7534c4db4", # BRock 80
        "https://open.spotify.com/playlist/4uWqwCSd1Gb45U7QDgEPwf?si=baee1efb2a524ff9", # MPB Antigas - As Melhores e Mais Tocadas - Anos 80, 90, 2000 e Lançamentos
        "https://open.spotify.com/playlist/6hUvrs9p5b5pzQyYYbcTth?si=e9ab3e199edd4a88"  # Rock Classics
    ]
    
    # Defina o nome do arquivo que será salvo com os dados combinados.
    output_csv_file = "artistas_classicos_dados.csv"

    print("--- Iniciando processo de geração de relatório de artistas de MÚLTIPLAS playlists ---")

    # Dicionário que vai armazenar todos os artistas únicos encontrados.
    # Usar um dicionário garante que não teremos artistas duplicados.
    all_unique_artists = {}

    # Passo 1: Loop para processar cada playlist da lista
    for i, url in enumerate(playlist_urls):
        print(f"\n--- Processando playlist {i+1} de {len(playlist_urls)} ---")
        print(f"URL: {url}")
        
        # 1a: Extrair o ID da URL da playlist.
        playlist_id = extract_spotify_playlist_id(url)
        
        if not playlist_id:
            print(f"AVISO: Não foi possível extrair um ID da URL: {url}. Pulando para a próxima.")
            continue
        
        # 1b: Buscar todos os artistas únicos da playlist atual.
        artists_from_this_playlist = get_artists_from_playlist(playlist_id)

        # 1c: Adicionar os artistas encontrados ao nosso dicionário principal.
        # O método .update() junta os dicionários, ignorando duplicatas automaticamente.
        all_unique_artists.update(artists_from_this_playlist)
        print(f"Artistas únicos encontrados até agora: {len(all_unique_artists)}")
    
    print("\n--- Todas as playlists foram processadas. Compilando relatório final. ---")
    
    if not all_unique_artists:
        print("Nenhum artista foi encontrado nas playlists fornecidas. Encerrando.")
        return

    print(f"Total de {len(all_unique_artists)} artistas únicos encontrados.")

    # Passo 2: Obter os perfis detalhados para a lista combinada de artistas.
    # Isso é feito apenas uma vez, no final, para ser mais eficiente.
    full_profiles = get_full_artist_profiles(all_unique_artists)
    
    # Passo 3: Salvar os dados compilados em um único arquivo CSV.
    save_artists_to_csv(full_profiles, output_csv_file, sort_by='popularity')
    
    print(f"\n--- Processo finalizado com sucesso! Relatório salvo em '{output_csv_file}' ---")


# Garante que a função main() só será executada quando o script for chamado diretamente.
if __name__ == "__main__":
    main()