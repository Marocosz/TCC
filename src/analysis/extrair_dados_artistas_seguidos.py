# TIPO DE ARQUIVO: RECEBE LINK
# src/analysis/extrair_dados_artistas_seguidos.py

"""
================================================================================
MÓDULO DE EXTRAÇÃO DE DADOS DE ARTISTAS SEGUIDOS (AUDIT DATASET BUILDER)
================================================================================

Objetivo do Arquivo:
    Gerar o dataset de "Interesses Explícitos" do TCC.
    Este script identifica os artistas principais das playlists semente de cada 
    persona (aqueles que foram seguidos pelas contas) e extrai seus metadados 
    completos para análise estatística de perfil.

Parte do Sistema:
    Analysis (Coleta de Baseline).

Responsabilidades:
    1. Identificação de Alvos: Mapeia os artistas primários de cada nicho.
    2. Deduplicação: Garante que cada artista apareça apenas uma vez no dataset.
    3. Enriquecimento de Metadados: Busca popularidade, gêneros e volume de seguidores.
    4. Persistência: Gera arquivos CSV estruturados em 'data/processed/'.

Comunicação:
    - Externa: API do Spotify (Spotipy).
    - Interna: Provê dados para o cálculo de métricas de diversidade e viés.

Uso:
    python src/analysis/extrair_dados_artistas_seguidos.py [persona/todas]
"""

import spotipy
import sys
import os
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from dotenv import load_dotenv
import csv
import time

# Carrega as credenciais do ambiente (.env)
load_dotenv()

# ==============================================================================
# CONFIGURAÇÃO CENTRAL (MAPA DE ARTISTAS POR PERSONA)
# ------------------------------------------------------------------------------
# Reutiliza as URLs das playlists geradas para identificar os artistas seguidos.
# ==============================================================================
# Define a raiz do projeto dinamicamente
script_dir = os.path.dirname(os.path.abspath(__file__)) # src/analysis
project_root = os.path.dirname(os.path.dirname(script_dir)) # TCC root

CONFIG_ARTISTAS = {
    "beatriz": {
        "url": "https://open.spotify.com/playlist/50QfqvGmUpcIBmLpvKwYia?si=64567674fe704edc", 
        "output": os.path.join(project_root, "data", "processed", "dataset_Beatriz_artistas_seguidos.csv")
    },
    "daniel": {
        "url": "https://open.spotify.com/playlist/4is9L43Z54V47i317eEU34?si=b6f80876aebf45fa",
        "output": os.path.join(project_root, "data", "processed", "dataset_Daniel_artistas_seguidos.csv")
    },
    "ricardo": {
        "url": "https://open.spotify.com/playlist/0M4gzc0tsCbCfZokdXgV7n?si=1997b691d05c4ede",
        "output": os.path.join(project_root, "data", "processed", "dataset_Ricardo_artistas_seguidos.csv")
    },
    "sofia": {
        "url": "https://open.spotify.com/playlist/38A45UlLoWNhgJqOOp1Prb?si=0e3c6e1e938b4961",
        "output": os.path.join(project_root, "data", "processed", "dataset_Sofia_artistas_seguidos.csv")
    }
}

def extrair_dados_artistas(playlist_url: str, output_csv_file: str):
    """
    Executa o fluxo de extração de metadados dos artistas principais de uma playlist.

    O que faz:
        1. Acessa a playlist semente.
        2. Itera sobre todas as faixas e extrai o ID do primeiro artista (Principal).
        3. Envia IDs únicos para a API de 'artists' (batch request).
        4. Compila dados de popularidade e seguidores e salva em CSV.

    Por que existe:
        Para criar um baseline de "Quem a persona segue/gosta" para comparar
        com "O que a persona recebe" nas recomendações.

    Quando é chamada:
        Durante a fase de setup do experimento ou para auditoria.

    Args:
        playlist_url (str): Link da playlist que originou os seguidores.
        output_csv_file (str): Caminho para salvar o CSV de artistas.
    """
    print(f"\n--- Processando Artistas Seguidos: {output_csv_file.split('/')[-1]} ---")
    
    if not playlist_url:
        print("   [!] ERRO: URL de referência não encontrada.")
        return

    try:
        # 1. Autenticação para leitura de Playlist
        sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-read-private"))
        playlist_id = playlist_url.split('/')[-1].split('?')[0]

        # 2. Extração de IDs dos Artistas Principais
        print("Identificando artistas únicos nas playlists...")
        resultados = sp_user.playlist_items(playlist_id)
        itens = resultados['items']
        while resultados['next']:
            resultados = sp_user.next(resultados)
            itens.extend(resultados['items'])

        # Pegamos apenas o ID do primeiro artista de cada música (o artista principal)
        artist_ids_set = set()
        for item in itens:
            if item and item.get('track') and item['track']['artists']:
                artist_id = item['track']['artists'][0]['id']
                if artist_id:
                    artist_ids_set.append(artist_id) if isinstance(artist_ids_set, list) else artist_ids_set.add(artist_id)

        artist_ids = list(artist_ids_set)
        print(f"Total de {len(artist_ids)} artistas únicos identificados.")

        # 3. Busca de Detalhes (Popularidade, Gêneros, Seguidores)
        # Usamos ClientCredentials para melhor performance em dados públicos
        sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
        lista_final_artistas = []

        print("Enriquecendo dados dos artistas via API...")
        # Processamento em lotes de 50 (limite do Spotify)
        for i in range(0, len(artist_ids), 50):
            batch = artist_ids[i:i+50]
            artist_results = sp_app.artists(batch)
            
            for art in artist_results['artists']:
                info = {
                    'artist_name': art['name'],
                    'artist_id': art['id'],
                    'popularity': art['popularity'],
                    'followers_total': art['followers']['total'],
                    'genres': "; ".join(art['genres']),
                    'spotify_url': art['external_urls'].get('spotify', ''),
                    'image_url': art['images'][0]['url'] if art['images'] else 'N/A'
                }
                lista_final_artistas.append(info)
            
            time.sleep(0.2) # Evitar rate limit

        # 4. Salvamento do Dataset
        os.makedirs(os.path.dirname(output_csv_file), exist_ok=True)
        
        colunas = ['artist_name', 'artist_id', 'popularity', 'followers_total', 'genres', 'spotify_url', 'image_url']
        
        with open(output_csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=colunas)
            writer.writeheader()
            writer.writerows(lista_final_artistas)

        print(f"--- SUCESSO! Dataset de artistas salvo em: {output_csv_file} ---")

    except Exception as e:
        print(f"Ocorreu um erro no processamento: {e}")

def main():
    """
    Ponto de entrada do script.
    """
    if len(sys.argv) < 2:
        print("\nUso: python extrair_dados_artistas_seguidos.py [persona/todas]")
        return

    argumento = sys.argv[1].lower()

    if argumento == "todas" or argumento == "all":
        for persona, config in CONFIG_ARTISTAS.items():
            extrair_dados_artistas(config["url"], config["output"])
    else:
        config = CONFIG_ARTISTAS.get(argumento)
        if config:
            extrair_dados_artistas(config["url"], config["output"])
        else:
            print(f"ERRO: Persona '{argumento}' não encontrada.")

if __name__ == "__main__":
    main()