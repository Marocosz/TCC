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
        "https://open.spotify.com/playlist/2RxIuqmH1n5QCx0eUmmyCA?si=35f9751c7013485b", # Indie Pop 2010s
        "https://open.spotify.com/playlist/6XLvNXM2WLHTFspl0KULxN?si=5c775ab067bd4aa2", # Best of Indie 2014
        "https://open.spotify.com/playlist/3Q4tfVNqIE3HTxz21W9SLi?si=d0d5fbde896540f1"  # Best of Indie 2022
    ]
    
    # Defina o nome do arquivo que será salvo com os dados combinados.
    output_csv_file = "artistas_indie_dados.csv"

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