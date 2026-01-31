# TIPO DE ARQUIVO: RECEBE LINK

"""
================================================================================
ARQUITETURA DO TCC: CONSTRUTOR DE BASE DE DADOS BRUTA (RAW DATA)
================================================================================

Objetivo do Arquivo:
    Este script é o ponto de partida do experimento. Sua função é "minerar" artistas
    de nichos específicos através de playlists curadas (seed playlists) no Spotify
    e criar a base de dados inicial (Raw Data).

Parte do Sistema:
    Analysis (Pipeline de Mineração).

Responsabilidades:
    1. Leitura de Fontes: Recebe URLs de playlists "semente" que definem o perfil.
    2. Extração de Identidades: Mapeia artistas únicos dessas playlists.
    3. Enriquecimento de Dados: Consulta a API para obter popularidade, gêneros e seguidores.
    4. Persistência: Salva os dados brutos em 'data/raw/', que alimentam os Collectors.

Comunicação:
    - Entrada: URLs configuradas no dicionário PERSONAS.
    - Saída: Arquivos CSV em 'data/raw/'.

Uso:
    python src/analysis/build_persona_raw_data.py [nome_da_persona]
    python src/analysis/build_persona_raw_data.py all
"""

import sys
import os

# --- CONFIGURAÇÃO DE AMBIENTE ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
diretorio_src = os.path.dirname(diretorio_atual)
sys.path.append(diretorio_src)

# Importação das funções utilitárias localizadas na pasta src
from functions import (
    extract_spotify_playlist_id,
    get_artists_from_playlist,
    get_full_artist_profiles,
    save_artists_to_csv
)

project_root = os.path.dirname(diretorio_src)

# --- CONFIGURAÇÃO DAS PERSONAS E FONTES DE DADOS ---
# Este dicionário centraliza as "regras" de onde buscar artistas para cada perfil.
# Os caminhos de output apontam para 'data/raw/'
PERSONAS = {
    "beatriz": {
        "urls": ["https://open.spotify.com/playlist/3ZNXMWlJdHsrtYvla53nVA?si=b448e5b5b5b4493c"], # Ex: Top Brasil
        "output": os.path.join(project_root, "data", "raw", "artistas_topbrasil_dados.csv")
    },
    "daniel": {
        "urls": ["https://open.spotify.com/playlist/1cVlDgSCIXIAOWFqWwEew2?si=0a229a6c9da84975"],
        "output": os.path.join(project_root, "data", "raw", "artistas_lofi_dados.csv")
    },
    "ricardo": {
        "urls": ["https://open.spotify.com/playlist/0W9QIdeE0rS9mkOiPY9tSa?si=4924da6010bb4853"],
        "output": os.path.join(project_root, "data", "raw", "artistas_classicos_dados.csv")
    },
    "sofia": {
        "urls": ["https://open.spotify.com/playlist/1q1mMCNcPx7uEWa5hwLvgv?si=1ec6fa3365684000"],
        "output": os.path.join(project_root, "data", "raw", "artistas_indie_dados.csv")
    }
}

def executar_coleta(nome_persona):
    """
    Orquestra a coleta de dados de uma persona específica.
    
    O que faz:
        1. Identifica a configuração (URLs e Output).
        2. Itera sobre as playlists semente para extrair IDs de artistas.
        3. Dedupica a lista de artistas encontrados.
        4. Busca metadados ricos (Popularidade, Followers) na API.
        5. Salva o resultado em CSV.

    Por que existe:
        Centraliza a lógica de ETL para reutilização em todas as personas.
    
    Quando é chamada:
        Pela função `main`, uma vez para cada persona solicitada.

    Args:
        nome_persona (str): O nome da chave no dicionário PERSONAS (ex: 'beatriz').
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
    if argumento == "all" or argumento == "todas":
        print("Iniciando processamento em lote de todas as personas...")
        for persona in PERSONAS.keys():
            executar_coleta(persona)
    else:
        # Processa apenas a persona solicitada
        executar_coleta(argumento)

if __name__ == "__main__":
    main()