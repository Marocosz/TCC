# TIPO DE ARQUIVO: RECEBE CSV

"""
================================================================================
ARQUITETURA DO TCC: GERADOR DE PLAYLIST SIMPLIFICADO (TOP 200 ABSOLUTO)
================================================================================

Objetivo do Arquivo:
    Gerar a playlist da Persona "Beatriz", que representa o perfil de consumo
    Mainstream (Top Chart).

Parte do Sistema:
    Collectors (Coletores de Dados e Geração de Insumos).

Responsabilidades:
    1. Leitura: Carregar artistas "Top Brasil" do CSV raw.
    2. Mineração: Buscar as músicas mais populares DESSES artistas.
    3. Filtragem: Selecionar as 200 faixas com maior índice de popularidade absoluto.
    4. Persistência: Criar playlist no Spotify e salvar likes na conta.

Comunicação:
    - Entrada: CSV `data/raw/artistas_topbrasil_dados.csv`.
    - Saída: Playlist pública no Spotify e atualização da Biblioteca do Usuário.

Uso:
    python src/collectors/create_beatriz_playlist.py
"""

import sys
import os
import time

# --- CONFIGURAÇÃO DE AMBIENTE ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
diretorio_src = os.path.dirname(diretorio_atual)
sys.path.append(diretorio_src)

from functions import (
    load_artists_from_csv,
    extract_top_tracks_from_data,
    create_playlist,        
    add_tracks_to_playlist,
    like_tracks_slowly
)

# --- CONFIGURAÇÕES ---
# Definição estática das regras de negócio deste script
CONFIG = {
    # Caminho ajustado para funcionar localmente
    "CSV_PATH": r"c:\Users\marco\OneDrive\Documentos\Pessoal\Projetos\TCC\data\raw\artistas_topbrasil_dados.csv",
    "PLAYLIST_NAME": "Top Hits Brasil (Top 200 Absoluto)",
    "TARGET_SIZE": 200
}

def main():
    """
    Função Principal (Orquestrador).
    
    Fluxo de Execução:
        1. Carrega lista de artistas Mainstream.
        2. Varre o "Top 10" de cada artista para criar um pool massivo de candidatos.
        3. Ordena esse pool puramente por popularidade (Hits do momento).
        4. Corta nas top 200 músicas.
        5. Gera os artefatos no Spotify (Playlist + Likes).
    """
    print("\n" + "="*60)
    print(f"INICIANDO GERADOR SIMPLIFICADO: {CONFIG['PLAYLIST_NAME']}")
    print("="*60)

    # 1. Carregar Todos os Artistas
    # Limit=1000 para tentar pegar tudo que tiver no CSV
    all_artists = load_artists_from_csv(CONFIG['CSV_PATH'], limit=1000)
    
    if not all_artists:
        print("[!] Erro: CSV vazio ou não encontrado.")
        return
    
    print(f"Base carregada: {len(all_artists)} artistas encontrados.")
    print("Iniciando varredura de Top Tracks (isso pode demorar um pouco)...")

    # 2. Coletar TODAS as músicas possíveis de todos os artistas
    # Estratégia "Pool Gigante":
    # Em vez de decidir artista por artista, pegamos TUDO que é bom
    # e deixamos a métrica de popularidade decidir no final.
    all_tracks_pool = []
    seen_uris = set() # Para evitar duplicatas imediatas (ex: músicas em 2 álbuns)
    
    for i, artist in enumerate(all_artists):
        # Feedback visual a cada 10 artistas para não poluir demais o terminal
        if i % 10 == 0:
            print(f"  > Processando artista {i+1}/{len(all_artists)}: {artist['name']}...")
            
        tracks = extract_top_tracks_from_data(artist)
        
        for t in tracks:
            # Verifica se tem 'popularity' (segurança de tipo)
            if 'popularity' not in t:
                continue
                
            if t['uri'] not in seen_uris:
                all_tracks_pool.append(t)
                seen_uris.add(t['uri'])
    
    print(f"\nColeta finalizada. Total de músicas únicas encontradas: {len(all_tracks_pool)}")

    # 3. Ordenar por Popularidade (A Seleção Top Chart)
    # A essência da Beatriz: só importa o que está tocando MUITO.
    print("Ordenando músicas por popularidade...")
    all_tracks_pool.sort(key=lambda x: x['popularity'], reverse=True)

    # 4. Selecionar as Top 200
    top_tracks_selected = all_tracks_pool[:CONFIG['TARGET_SIZE']]
    
    final_uris = [t['uri'] for t in top_tracks_selected]
    
    # Exibe um preview das Top 5 para validação visual
    print("\n--- PREVIEW DAS TOP 5 MAIS POPULARES SELECIONADAS ---")
    for i, t in enumerate(top_tracks_selected[:5]):
        print(f"#{i+1} {t['name']} (Pop: {t['popularity']}) - {t['artists'][0]['name']}")
    print("..." + "\n")

    if not final_uris:
        print("ERRO: Nenhuma música selecionada.")
        return

    # 5. Criar Playlist e Salvar
    print(f"Criando playlist com {len(final_uris)} faixas...")
    
    playlist_id = create_playlist(CONFIG['PLAYLIST_NAME'])
    if playlist_id:
        add_tracks_to_playlist(playlist_id, final_uris)
        
        # Simula o comportamento de usuário "Gostar" das músicas
        print(f"\n--- Aplicando 'Likes' na conta... ---")
        like_tracks_slowly(final_uris)
        
    print(f"\n✅ SUCESSO! Playlist '{CONFIG['PLAYLIST_NAME']}' criada com as {len(final_uris)} músicas mais populares.")
 
 
if __name__ == "__main__":
    main()