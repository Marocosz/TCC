# TIPO DE ARQUIVO: RECEBE LINK
# src/analysis/extrair_dados_playlist.py

"""
================================================================================
MÓDULO DE EXTRAÇÃO DE DADOS DE PLAYLISTS (DATASET BUILDER)
================================================================================

Objetivo do Arquivo:
    Atuar como a ferramenta de extração e processamento de dados brutos (ETL) do TCC.
    Este script conecta à API do Spotify, baixa o conteúdo completo de playlists
    (seja a semente criada manualmente ou as recomendações da IA) e transforma
    esses dados em um DATASET (CSV) estruturado para posterior análise.

Parte do Sistema:
    Analysis (Coleta de Dados Pós-Geração).

Responsabilidades:
    1. Gerenciamento de Configuração: Mapeia cada Persona à sua respectiva Playlist.
    2. Conexão Híbrida: Utiliza autenticação de Usuário e de Cliente.
    3. Tratamento de Paginação: Garante que playlists grandes sejam lidas por completo.
    4. Enriquecimento de Dados: Cruza dados da música com métricas do artista.
    5. Persistência: Grava o resultado em CSV na pasta 'data/processed/'.

Comunicação:
    - Externa: API do Spotify (Spotipy).
    - Interna: Gera CSVs base para `build_cross_graphs.py` e `build_personal_graphs.py`.

Uso:
    python src/analysis/extrair_dados_playlist.py [persona/todas]
"""

import spotipy
import sys
import os
import requests
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from dotenv import load_dotenv
import csv

# Carrega as credenciais do ambiente (CLIENT_ID, CLIENT_SECRET)
load_dotenv()


def fetch_playlist_items_v2(access_token, playlist_id):
    """
    Lê os itens de uma playlist usando o endpoint NOVO `/items` (Feb/2026).

    Por que existe:
        Em fevereiro/2026 a Spotify Web API depreciou o endpoint
        `/playlists/{id}/tracks` (que ainda é o usado pelo spotipy.playlist_items()
        em versões antigas) e o substituiu por `/playlists/{id}/items`. O endpoint
        antigo retorna 403 Forbidden mesmo para o owner, enquanto o novo funciona.

    Como funciona:
        Faz chamadas paginadas ao endpoint novo via requests, e ADAPTA a resposta
        para o schema antigo (cada item passa a ter chave 'track' em vez de 'item'),
        de modo que o resto do código que assume `item['track']` continua funcional.

    Args:
        access_token (str): Token OAuth do usuário (que precisa ser dono ou
            colaborador da playlist desde a mudança de Feb/2026).
        playlist_id (str): ID da playlist (sem prefixo "spotify:playlist:").

    Returns:
        list[dict]: Lista de itens no schema antigo, cada um com chave 'track'.
    """
    items = []
    offset = 0
    limit = 100
    headers = {"Authorization": f"Bearer {access_token}"}
    while True:
        url = (
            f"https://api.spotify.com/v1/playlists/{playlist_id}/items"
            f"?limit={limit}&offset={offset}"
        )
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        for raw in data.get("items", []):
            # Schema novo usa 'item'; schema antigo usa 'track'. Padroniza pro antigo
            # pra manter o resto do pipeline (montagem CSV) funcional sem refatorar.
            track = raw.get("item") or raw.get("track")
            if track:
                items.append({"track": track})
        if not data.get("next"):
            break
        offset += limit
    return items

# ==============================================================================
# CONFIGURAÇÃO CENTRAL (MAPA DE DATASETS)
# ------------------------------------------------------------------------------
# Define as regras de execução: Qual playlist ler e onde salvar o DATASET.
# Permite a execução em lote ou individual sem alterar o código da função principal.
# ==============================================================================
# Define a raiz do projeto dinamicamente
script_dir = os.path.dirname(os.path.abspath(__file__)) # src/analysis
project_root = os.path.dirname(os.path.dirname(script_dir)) # TCC root

# Config dos INPUTS (playlists-semente das personas, privadas).
# Output CSVs em data/inputs/, schema raw (será enriquecido depois).
CONFIG_INPUTS = {
    "beatriz": {
        "url": "https://open.spotify.com/playlist/50QfqvGmUpcIBmLpvKwYia?si=64567674fe704edc",
        "output": os.path.join(project_root, "data", "inputs", "dataset_Beatriz_input.csv")
    },
    "daniel": {
        "url": "https://open.spotify.com/playlist/4is9L43Z54V47i317eEU34?si=b6f80876aebf45fa",
        "output": os.path.join(project_root, "data", "inputs", "dataset_Daniel_input.csv")
    },
    "ricardo": {
        "url": "https://open.spotify.com/playlist/0M4gzc0tsCbCfZokdXgV7n?si=1997b691d05c4ede",
        "output": os.path.join(project_root, "data", "inputs", "dataset_Ricardo_input.csv")
    },
    "sofia": {
        "url": "https://open.spotify.com/playlist/38A45UlLoWNhgJqOOp1Prb?si=0e3c6e1e938b4961",
        "output": os.path.join(project_root, "data", "inputs", "dataset_Sofia_input.csv")
    }
}

# Config dos OUTPUTS (playlists espelho dos Daily Mixes, criadas em 2026-04-28
# após 40h de Smart Shuffle por persona, com duplicatas removidas).
# Cada persona é dona da própria → exige OAuth dela para ler /items.
CONFIG_RECOMMENDATIONS = {
    "beatriz": {
        "url": "https://open.spotify.com/playlist/0GJo96dZ1uXkcPU1YeOI89?si=3034ba22eb614e7f",
        "output": os.path.join(project_root, "data", "outputs", "dataset_Beatriz_output.csv")
    },
    "daniel": {
        "url": "https://open.spotify.com/playlist/0V7TjiOtU4wh2Ye0L4iwCd?si=88ca14da64474d51",
        "output": os.path.join(project_root, "data", "outputs", "dataset_Daniel_output.csv")
    },
    "ricardo": {
        "url": "https://open.spotify.com/playlist/5Gzczx57X6akiCW9wMzoIW?si=4a77d8be49ae435a",
        "output": os.path.join(project_root, "data", "outputs", "dataset_Ricardo_output.csv")
    },
    "sofia": {
        "url": "https://open.spotify.com/playlist/2pQuNqpp8xCDOKjZowmo0G?si=8abc6fdc7d984ae2",
        "output": os.path.join(project_root, "data", "outputs", "dataset_Sofia_output.csv")
    }
}

# Alias retrocompatível
CONFIG_DATASETS = CONFIG_INPUTS

# --- Função Auxiliar ---
def ms_para_min_seg(ms):
    """
    Converte milissegundos para um formato legível 'min:seg'.

    O que faz:
        Recebe um inteiro (ex: 184000) e retorna string formatada (ex: "3:04").

    Por que existe:
        A API retorna duração crua em int, mas relatórios exigem leitura humana.

    Quando é chamada:
        Durante a montagem da linha de dados para o CSV.
        
    Args:
        ms (int): Duração bruta em milissegundos.
        
    Returns:
        str: Tempo formatado ou "0:00" se inválido.
    """
    if not isinstance(ms, (int, float)):
        return "0:00"
    total_segundos = int(ms / 1000)
    minutos = total_segundos // 60
    segundos = total_segundos % 60
    return f"{minutos}:{segundos:02}"

# --- Função Principal ---
def extrair_e_salvar_dados(playlist_url: str, output_csv_file: str, use_oauth: bool = True, cache_path: str = ".cache"):
    """
    Executa o fluxo ETL (Extract, Transform, Load) para uma playlist específica.

    O que faz:
        1. Conecta ao Spotify (OAuth de usuário OU Client Credentials) e lê a playlist.
        2. Itera por todas as páginas (paginação) para coletar URIs.
        3. Conecta como App para baixar detalhes de artistas em lote (Performance).
        4. Compila metadados (popularidade, genres, dates) e salva em CSV.

    Por que existe:
        É o motor principal de coleta de dados do projeto.

    Quando é chamada:
        Pelo orquestrador `main` para cada persona solicitada.

    Args:
        playlist_url (str): Link completo da playlist.
        output_csv_file (str): Caminho absoluto de destino do arquivo.
        use_oauth (bool): Se True, usa OAuth (necessário para playlists privadas
            das próprias personas). Se False, usa Client Credentials — funciona
            apenas para playlists públicas (caso das playlists espelho de output).
    """
    print(f"\n--- Iniciando extração de dados: {os.path.basename(output_csv_file)} ---")

    # Validação simples para evitar execução com URLs não configuradas
    if "INSIRA" in playlist_url or not playlist_url:
        print("   [!] ERRO: URL não configurada.")
        return

    try:
        # ----------------------------------------------------------------------
        # ETAPA 1: BUSCAR MÚSICAS
        # ----------------------------------------------------------------------
        # Para playlists privadas (inputs): OAuth com scope playlist-read-private.
        # Para playlists públicas (outputs/mirrors): Client Credentials, sem login.
        print("Buscando todas as músicas da playlist...")

        if use_oauth:
            # Cache por persona evita conflito de tokens (cada persona faz seu
            # próprio OAuth). show_dialog=True força a tela de seleção de conta
            # toda vez (impede auto-autorização com conta logada anteriormente).
            scope = "playlist-read-private"
            auth_manager = SpotifyOAuth(scope=scope, cache_path=cache_path, show_dialog=True)
            print(f"   [i] Cache OAuth: {cache_path}")
            user_access_token = auth_manager.get_access_token(as_dict=False)
        else:
            print("   [i] Modo público (Client Credentials, sem OAuth).")
            cc_manager = SpotifyClientCredentials()
            user_access_token = cc_manager.get_access_token(as_dict=False)

        # Extração do ID da Playlist a partir da URL (remove query params)
        playlist_id = playlist_url.split('/')[-1].split('?')[0]

        # Endpoint NOVO /items (Feb/2026). Spotipy.playlist_items() ainda chama
        # o /tracks deprecated → 403 Forbidden. Por isso usamos a função custom
        # fetch_playlist_items_v2 que faz a chamada via requests + paginação.
        itens_playlist = fetch_playlist_items_v2(user_access_token, playlist_id)

        print(f"Total de {len(itens_playlist)} itens encontrados na playlist.")
        
        # Filtragem: Remove itens que não são músicas (ex: episódios de podcast ou nulos)
        tracks = [item['track'] for item in itens_playlist if item and item.get('track')]
        
        # ----------------------------------------------------------------------
        # ETAPA 2: BUSCAR DETALHES DOS ARTISTAS (Auth de Aplicativo)
        # ----------------------------------------------------------------------
        # Em fevereiro/2026 a Spotify Web API removeu os campos `popularity`,
        # `followers` e `genres` da resposta de /artists tanto via singular
        # quanto batch, para apps em Development Mode. Tentamos mesmo assim
        # (em apps com Extended Quota Mode ainda funciona); se falhar com 403
        # ou retornar campos vazios, o pipeline degrada graciosamente — os
        # dados desses 3 campos serão preenchidos depois via fontes externas
        # (MusicBrainz/Last.fm) pelo script enrich_external.py.
        print("Buscando detalhes dos artistas em lote (best-effort)...")

        sp_app = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

        artist_ids = list(set(
            artist['id'] for track in tracks for artist in track['artists'] if artist and artist.get('id')
        ))

        artist_details_map = {}
        try:
            for i in range(0, len(artist_ids), 50):
                batch_ids = artist_ids[i:i+50]
                artist_results = sp_app.artists(batch_ids)
                for artist in artist_results['artists']:
                    if artist:
                        artist_details_map[artist['id']] = artist
            print(f"   [✓] Detalhes obtidos via Spotify para {len(artist_details_map)} artistas.")
        except Exception as e:
            print(f"   [!] Spotify bloqueou enriquecimento de artistas (esperado em Dev Mode Feb/2026): {str(e)[:120]}")
            print(f"   [i] Será necessário rodar enrich_external.py para preencher popularity/followers/genres.")

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

            # Estrutura da Linha (Schema do CSV).
            # Campos perdidos pela mudança Feb/2026 da Web API (popularity da
            # track, popularity/followers/genres do artista) ficam vazios aqui
            # e serão preenchidos por enrich_external.py via fontes externas.
            followers_obj = primary_artist_details.get('followers') or {}
            linha = {
                'track_name': track.get('name', ''),
                'track_popularity': track.get('popularity') if track.get('popularity') is not None else '',
                'primary_artist_name': primary_artist_info.get('name', 'N/A'),
                'artist_popularity': primary_artist_details.get('popularity', ''),
                'artist_followers': followers_obj.get('total', '') if isinstance(followers_obj, dict) else '',
                'all_artists': all_artist_names,
                'artist_genres': "; ".join(primary_artist_details.get('genres', [])),
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

    Argumentos:
        sys.argv[1]: nome da persona ou 'todas'/'all'.
        sys.argv[2] (opcional): '--source=input' (default) ou '--source=output'.

    Modo input: usa CONFIG_INPUTS, lê playlists-semente privadas via OAuth.
    Modo output: usa CONFIG_RECOMMENDATIONS, lê playlists espelho públicas via
        Client Credentials (não exige login por persona).
    """
    if len(sys.argv) < 2:
        print("\nUso correto:")
        print("  python extrair_dados_playlist.py [persona|todas] [--source=input|output]")
        print("  Ex (input):  python extrair_dados_playlist.py todas")
        print("  Ex (output): python extrair_dados_playlist.py todas --source=output")
        print("\nPersonas configuradas:", ", ".join(CONFIG_INPUTS.keys()))
        return

    argumento = sys.argv[1].lower()

    # Determina source pelo segundo argumento (default = input)
    source = "input"
    for arg in sys.argv[2:]:
        if arg.startswith("--source="):
            source = arg.split("=", 1)[1].lower()

    if source == "output":
        config_map = CONFIG_RECOMMENDATIONS
        # Em fevereiro/2026 a Spotify Web API passou a exigir que o usuário
        # autenticado seja DONO ou COLABORADOR da playlist para ler seus tracks.
        # Como cada playlist espelho é de uma persona diferente, precisamos
        # autenticar como cada persona individualmente. Cache por persona.
        use_oauth = True
        print(">>> MODO OUTPUT (playlists espelho dos Daily Mixes)")
        print(">>> ATENÇÃO: cada persona faz seu próprio OAuth (4 logins).")
        print(">>> Use janelas anônimas separadas pra trocar de conta entre personas.")
    else:
        config_map = CONFIG_INPUTS
        use_oauth = True
        print(">>> MODO INPUT (playlists-semente / training)")

    def cache_for(persona_name):
        """Caminho de cache OAuth distinto por persona (evita conflito de tokens)."""
        if source == "output":
            return f".cache_{persona_name}"
        return ".cache"

    # Lógica de decisão: Todas vs Individual
    if argumento in ("all", "todas"):
        print(">>> INICIANDO EXTRAÇÃO EM LOTE (TODAS AS PERSONAS)")
        for persona, config in config_map.items():
            extrair_e_salvar_dados(
                config["url"], config["output"],
                use_oauth=use_oauth, cache_path=cache_for(persona)
            )
    else:
        config = config_map.get(argumento)
        if config:
            extrair_e_salvar_dados(
                config["url"], config["output"],
                use_oauth=use_oauth, cache_path=cache_for(argumento)
            )
        else:
            print(f"ERRO: Persona '{argumento}' não encontrada na configuração ({source}).")

if __name__ == '__main__':
    main()