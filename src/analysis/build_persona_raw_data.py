"""
================================================================================
ARQUITETURA DO TCC: CONSTRUTOR DE BASE DE DADOS BRUTA (RAW DATA)
================================================================================
Ideia Central:
Este script é o ponto de partida do experimento. Sua função é "minerar" artistas
de nichos específicos através de playlists curadas (seed playlists) no Spotify.

O script:
1. Recebe uma ou mais URLs de playlists que definem o perfil de uma Persona.
2. Extrai todos os artistas únicos dessas playlists para evitar duplicatas.
3. Consulta a API do Spotify para obter perfis detalhados (popularidade, gêneros, seguidores).
4. Salva esses dados em arquivos CSV na pasta 'data/raw/', que serão utilizados
   posteriormente pelos scripts de criação de playlists (collectors).

Uso:
    python build_persona_raw_data.py [nome_da_persona]
    python build_persona_raw_data.py todas
================================================================================
"""

import sys
import os

# Importação das funções utilitárias localizadas na pasta src
from functions import (
    extract_spotify_playlist_id,
    get_artists_from_playlist,
    get_full_artist_profiles,
    save_artists_to_csv
)

# --- CONFIGURAÇÃO DAS PERSONAS E FONTES DE DADOS ---
# Este dicionário centraliza as "regras" de onde buscar artistas para cada perfil.
# Os caminhos de output agora apontam corretamente para 'data/raw/'
PERSONAS = {
    "beatriz": {
        "urls": ["https://open.spotify.com/playlist/37i9dQZF1DX4YSJy4vUr9R"], # Ex: Top Brasil
        "output": "../../data/raw/artistas_topbrasil_dados.csv"
    },
    "daniel": {
        "urls": [
            "https://open.spotify.com/playlist/37i9dQZF1DX8Uebic0v7S6", # Lofi Beats
            "https://open.spotify.com/playlist/37i9dQZF1DXdbX4ghqPb9u", # Lofi Rain
            "https://open.spotify.com/playlist/37i9dQZF1DWWQRvui9Df7x"  # Lofi Sleep
        ],
        "output": "../../data/raw/artistas_lofi_dados.csv"
    },
    "ricardo": {
        "urls": [
            "https://open.spotify.com/playlist/37i9dQZF1DX1clS6T8O89S", # BRock 80
            "https://open.spotify.com/playlist/37i9dQZF1DXbSbmS0pX79a", # MPB Antigas
            "https://open.spotify.com/playlist/37i9dQZF1DX2Nc3B70Yv1t"  # Rock Classics
        ],
        "output": "../../data/raw/artistas_classicos_dados.csv"
    },
    "sofia": {
        "urls": [
            "https://open.spotify.com/playlist/37i9dQZF1DX26fS49p5pY6", # Indie Pop
            "https://open.spotify.com/playlist/37i9dQZF1DXa9is9v8mY9R", # Best of Indie 2024
            "https://open.spotify.com/playlist/37i9dQZF1DX4S8XfUpS5z8"  # Indie Chill
        ],
        "output": "../../data/raw/artistas_indie_dados.csv"
    }
}

def executar_coleta(nome_persona):
    """
    Orquestra a coleta de dados de uma persona específica.
    
    Argumentos:
        nome_persona (str): O nome da chave no dicionário PERSONAS.
    """
    config = PERSONAS.get(nome_persona.lower())
    
    if not config:
        print(f"ERRO: Persona '{nome_persona}' não encontrada no dicionário de configurações.")
        return

    print(f"\n{'='*60}")
    print(f"INICIANDO FASE DE MINERAÇÃO: {nome_persona.upper()}")
    print(f"{'='*60}")

    # Dicionário temporário para armazenar artistas e evitar IDs duplicados
    # entre diferentes playlists da mesma persona.
    all_unique_artists = {}

    # Passo 1: Extração de IDs e nomes de artistas
    for i, url in enumerate(config["urls"]):
        print(f"\n[Playlist {i+1}/{len(config['urls'])}] Extraindo IDs da URL...")
        
        # Converte URL em ID de playlist (ex: 'https://.../playlist/123' -> '123')
        playlist_id = extract_spotify_playlist_id(url)
        
        if not playlist_id:
            print(f"AVISO: Não foi possível processar a URL: {url}")
            continue
        
        # Busca artistas únicos dentro da playlist atual
        artists = get_artists_from_playlist(playlist_id)
        
        # Atualiza o dicionário mestre da persona com novos artistas encontrados
        all_unique_artists.update(artists)
        print(f"-> Artistas únicos acumulados até agora: {len(all_unique_artists)}")

    if not all_unique_artists:
        print(f"ERRO: Nenhum artista válido foi encontrado para a persona {nome_persona}.")
        return

    # Passo 2: Enriquecimento de Dados via API
    # Com a lista de IDs em mãos, buscamos popularidade, gêneros e seguidores.
    print(f"\nConsultando perfis detalhados de {len(all_unique_artists)} artistas no Spotify...")
    full_profiles = get_full_artist_profiles(all_unique_artists)
    
    # Passo 3: Persistência de Dados
    # Salva o resultado final em CSV, ordenando pelos artistas mais populares.
    # O caminho do arquivo é garantido pelo dicionário de configuração.
    save_artists_to_csv(full_profiles, config["output"], sort_by='popularity')
    
    print(f"\n✅ SUCESSO: Base de dados da {nome_persona.capitalize()} salva em:")
    print(f"   > {config['output']}")

def main():
    """
    Ponto de entrada do script. Gerencia os argumentos de linha de comando.
    """
    # Verifica se o usuário esqueceu de passar a persona como argumento
    if len(sys.argv) < 2:
        print("\n[!] ERRO DE USO. Tente:")
        print("    python build_persona_raw_data.py [nome_da_persona]")
        print("    Exemplo: python build_persona_raw_data.py beatriz")
        print("\nPersonas configuradas:", ", ".join(PERSONAS.keys()))
        print("Ou use 'todas' para processar todo o ecossistema.")
        return

    argumento = sys.argv[1].lower()

    # Opção para automatizar o processamento de todos os perfis de uma vez
    if argumento == "all":
        print("Iniciando processamento em lote de todas as personas...")
        for persona in PERSONAS.keys():
            executar_coleta(persona)
    else:
        # Processa apenas a persona solicitada
        executar_coleta(argumento)

if __name__ == "__main__":
    main()