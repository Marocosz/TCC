# src/analysis/extrair_dados_playlist.py

"""
================================================================================
MÓDULO DE EXTRAÇÃO DE DADOS DE PLAYLISTS (DATASET BUILDER)
================================================================================

OBJETIVO DO ARQUIVO:
    Atuar como a ferramenta de extração e processamento de dados brutos (ETL) do TCC.
    Este script conecta à API do Spotify, baixa o conteúdo completo de playlists
    (seja a semente criada manualmente ou as recomendações da IA) e transforma
    esses dados em um DATASET (CSV) estruturado para posterior análise.

PARTE DO SISTEMA:
    Camada de Coleta/Análise (Analysis). É executado após a criação das playlists ou
    após o período de coleta de recomendações.

RESPONSABILIDADES:
    1. Gerenciamento de Configuração: Mapeia cada Persona à sua respectiva Playlist e arquivo de saída.
    2. Conexão Híbrida: Utiliza autenticação de Usuário (para ler playlists) e de Cliente (para metadados).
    3. Tratamento de Paginação: Garante que playlists com mais de 100 músicas sejam baixadas integralmente.
    4. Enriquecimento de Dados: Cruza dados da faixa com dados do artista (gêneros, popularidade).
    5. Persistência: Salva o resultado formatado como Dataset CSV.

COMUNICAÇÃO:
    - Externa: Spotify Web API (via biblioteca `spotipy`).
    - Interna: Gera arquivos em `data/processed/` que serão lidos pelos scripts de gráficos.

USO:
    python extrair_dados_playlist.py [nome_da_persona]
    python extrair_dados_playlist.py todas
================================================================================
"""

import spotipy
import sys
import os
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from dotenv import load_dotenv
import csv

# Carrega as credenciais do ambiente (CLIENT_ID, CLIENT_SECRET)
load_dotenv()

# ==============================================================================
# CONFIGURAÇÃO CENTRAL (MAPA DE DATASETS)
# ------------------------------------------------------------------------------
# Define as regras de execução: Qual playlist ler e onde salvar o DATASET.
# Permite a execução em lote ou individual sem alterar o código da função principal.
# ==============================================================================
CONFIG_DATASETS = {
    "beatriz": {
        "url": "https://open.spotify.com/playlist/43t30aNQ4w9JWGWNJZBycx?si=e02f6e26d2574b6e", 
        "output": "../../data/processed/dataset_Beatriz_playlist.csv"
    },
    "daniel": {
        "url": "https://open.spotify.com/playlist/6bOpB9LfJ5iu8Lert0mVv1?si=55ad0ed7dcb44b43",
        "output": "../../data/processed/dataset_Daniel_playlist.csv"
    },
    "ricardo": {
        "url": "https://open.spotify.com/playlist/4aHPLH7rqeJqQsgGrAlzw8?si=533c1fbe8aa24b7f",
        "output": "../../data/processed/dataset_Ricardo_playlist.csv"
    },
    "sofia": {
        "url": "https://open.spotify.com/playlist/1DnT0FX5aHNtjw3OzU2LG6?si=893eb9d2df19405d",
        "output": "../../data/processed/dataset_Sofia_playlist.csv"
    }
}

# --- Função Auxiliar ---
def ms_para_min_seg(ms):
    """
    Converte milissegundos para um formato legível 'min:seg'.
    
    Por que existe:
        A API retorna duração em int (ex: 180000), mas para relatórios
        humanos precisamos de strings (ex: '3:00').
        
    Args:
        ms (int/float): Duração bruta.
        
    Returns:
        str: Tempo formatado.
    """
    if not isinstance(ms, (int, float)):
        return "0:00"
    total_segundos = int(ms / 1000)
    minutos = total_segundos // 60
    segundos = total_segundos % 60
    return f"{minutos}:{segundos:02}"

# --- Função Principal ---
def extrair_e_salvar_dados(playlist_url: str, output_csv_file: str):
    """
    Executa o fluxo ETL (Extract, Transform, Load) para uma playlist específica.

    Fluxo Lógico:
    1. Autentica como Usuário para acessar a playlist (mesmo se privada).
    2. Itera sobre as páginas da playlist para baixar todas as faixas.
    3. Autentica como Aplicação para buscar metadados de artistas (melhor rate limit).
    4. Cruza as informações e salva o Dataset em CSV.

    Args:
        playlist_url (str): Link ou URI da playlist no Spotify.
        output_csv_file (str): Caminho relativo onde o arquivo será salvo.
    """
    print(f"\n--- Iniciando extração de dados: {output_csv_file.split('/')[-1]} ---")
    
    # Validação simples para evitar execução com URLs não configuradas
    if "INSIRA" in playlist_url or not playlist_url:
        print("   [!] ERRO: URL não configurada no dicionário CONFIG_DATASETS.")
        return

    try:
        # ----------------------------------------------------------------------
        # ETAPA 1: BUSCAR MÚSICAS (Auth de Usuário)
        # ----------------------------------------------------------------------
        # Usa escopo 'playlist-read-private' para garantir leitura irrestrita.
        print("Buscando todas as músicas da playlist...")
        
        scope = "playlist-read-private"
        sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
        
        # Extração do ID da Playlist a partir da URL (remove query params)
        playlist_id = playlist_url.split('/')[-1].split('?')[0]
        
        # Paginação Automática:
        # O Spotify entrega max 100 itens por request. O loop 'while' garante
        # que playlists maiores sejam baixadas na íntegra.
        resultados = sp_user.playlist_items(playlist_id)
        itens_playlist = resultados['items']
        while resultados['next']:
            resultados = sp_user.next(resultados)
            itens_playlist.extend(resultados['items'])
            
        print(f"Total de {len(itens_playlist)} itens encontrados na playlist.")
        
        # Filtragem: Remove itens que não são músicas (ex: episódios de podcast ou nulos)
        tracks = [item['track'] for item in itens_playlist if item and item.get('track')]
        
        # ----------------------------------------------------------------------
        # ETAPA 2: BUSCAR DETALHES DOS ARTISTAS (Auth de Aplicativo)
        # ----------------------------------------------------------------------
        # Troca para Client Credentials Flow.
        # Motivo: Dados de artistas são públicos e esse método tem limites
        # de requisição (Rate Limits) mais altos que o token de usuário.
        print("Buscando detalhes dos artistas em lote...")
        
        sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

        # Deduplicação:
        # Cria lista de IDs únicos para não consultar o mesmo artista várias vezes.
        artist_ids = list(set(
            artist['id'] for track in tracks for artist in track['artists'] if artist and artist.get('id')
        ))
        
        artist_details_map = {}
        
        # Processamento em Lote (Batching):
        # A API 'artists' aceita até 50 IDs. Iteramos em blocos para otimizar rede.
        for i in range(0, len(artist_ids), 50):
            batch_ids = artist_ids[i:i+50]
            artist_results = sp_app.artists(batch_ids)
            for artist in artist_results['artists']:
                # Mapa de acesso rápido (ID -> Objeto Artista)
                artist_details_map[artist['id']] = artist
        
        print(f"Detalhes obtidos para {len(artist_details_map)} artistas.")

        # ----------------------------------------------------------------------
        # ETAPA 3: MONTAR DADOS E NORMALIZAR
        # ----------------------------------------------------------------------
        print("Montando os dados para o dataset CSV...")
        dados_finais_para_csv = []
        
        for track in tracks:
            if not track: continue

            # Definição do Artista Principal (primeiro da lista)
            primary_artist_info = track['artists'][0] if track['artists'] else {}
            primary_artist_id = primary_artist_info.get('id')
            
            # Enriquecimento: Busca dados no mapa criado na Etapa 2
            primary_artist_details = artist_details_map.get(primary_artist_id, {})
            all_artist_names = "; ".join([artist['name'] for artist in track['artists']])

            # Estrutura da Linha (Schema do CSV)
            linha = {
                'track_name': track['name'],
                'track_popularity': track['popularity'],
                'primary_artist_name': primary_artist_info.get('name', 'N/A'),
                'artist_popularity': primary_artist_details.get('popularity', 0), # Métrica chave para análise de mainstream
                'artist_followers': primary_artist_details.get('followers', {}).get('total', 0), # Métrica chave para análise de nicho
                'all_artists': all_artist_names,
                'artist_genres': "; ".join(primary_artist_details.get('genres', [])), # Gêneros vêm do Artista
                'album_name': track['album']['name'],
                'album_release_date': track['album']['release_date'],
                'duration_readable': ms_para_min_seg(track.get('duration_ms')),
                'is_explicit': track['explicit'],
                'track_url': track['external_urls'].get('spotify', ''),
                'track_uri': track['uri']
            }
            dados_finais_para_csv.append(linha)

        # ----------------------------------------------------------------------
        # ETAPA 4: SALVAR ARQUIVO (Persistência)
        # ----------------------------------------------------------------------
        if not dados_finais_para_csv:
            print("Nenhum dado de música foi coletado.")
            return

        # Garante que a pasta de destino exista
        os.makedirs(os.path.dirname(output_csv_file), exist_ok=True)

        colunas = [
            'track_name', 'primary_artist_name', 'all_artists', 'album_name', 
            'track_popularity', 'artist_popularity', 'artist_followers', 'artist_genres', 
            'album_release_date', 'duration_readable', 'is_explicit', 'track_url', 'track_uri'
        ]
        
        print(f"Salvando dataset no arquivo '{output_csv_file}'...")
        
        with open(output_csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=colunas)
            writer.writeheader()
            writer.writerows(dados_finais_para_csv)
            
        print(f"\n--- SUCESSO! Extração concluída e dataset '{output_csv_file}' salvo. ---")

    except Exception as e:
        print(f"Ocorreu um erro: {e}")

# --- SEÇÃO PRINCIPAL (ORQUESTRADOR) ---
def main():
    """
    Ponto de entrada do script.
    Lê os argumentos do terminal e decide se executa para uma persona ou para todas.
    """
    # Verifica se o usuário passou argumentos
    if len(sys.argv) < 2:
        print("\nUso correto:")
        print("  python extrair_dados_playlist.py [nome_da_persona]")
        print("  Exemplo: python extrair_dados_playlist.py beatriz")
        print("  Para todas: python extrair_dados_playlist.py todas")
        print("\nPersonas configuradas:", ", ".join(CONFIG_DATASETS.keys()))
        return

    argumento = sys.argv[1].lower()

    # Lógica de decisão: Todas vs Individual
    if argumento == "all":
        print(">>> INICIANDO EXTRAÇÃO EM LOTE (TODAS AS PERSONAS)")
        for persona, config in CONFIG_DATASETS.items():
            extrair_e_salvar_dados(config["url"], config["output"])
    else:
        # Busca configuração da persona específica
        config = CONFIG_DATASETS.get(argumento)
        if config:
            extrair_e_salvar_dados(config["url"], config["output"])
        else:
            print(f"ERRO: Persona '{argumento}' não encontrada na configuração.")

if __name__ == '__main__':
    main()