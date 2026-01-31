# TIPO DE ARQUIVO: RECEBE CSV
# build_summaries.py

"""
================================================================================
MÓDULO DE GERAÇÃO DE RESUMOS ESTATÍSTICOS TEXTUAIS
================================================================================

Objetivo do Arquivo:
    Produzir relatórios em texto simples (.txt) contendo estatísticas descritivas
    fundamentais sobre cada playlist analisada. Estes resumos servem como
    "fichas técnicas" rápidas para consulta durante a escrita do TCC.

Parte do Sistema:
    Analysis (Relatórios Textuais).

Responsabilidades:
    1. Leitura de Datasets: Carregar os dados processados de cada Persona.
    2. Cálculo Estatístico: Computar médias (popularidade, ano), contagens
       (gêneros, artistas) e extremos (máximos/mínimos).
    3. Formatação: Converter dados brutos em texto legível para humanos.
    4. Persistência: Salvar os arquivos .txt organizados por persona.

Comunicação:
    - Entrada: CSVs de 'data/processed/'.
    - Saída: Arquivos .txt em 'reports/summaries/'.

Métricas Calculadas:
    - Volume total (músicas/artistas).
    - Índices de Popularidade (Média da faixa vs Média do artista).
    - Janela Temporal (Ano médio, música mais antiga/nova).
    - Estrutura (Duração média).
    - Top Gêneros e Artistas (Distribuição de frequência).

Uso:
    python src/analysis/build_summaries.py [nome_persona]
    python src/analysis/build_summaries.py all
"""

import pandas as pd
import os
import sys
from collections import Counter

# --- Função Auxiliar ---
def formatar_duracao(segundos):
    """
    Converte uma duração em segundos (float) para formato de relógio (MM:SS).
    
    O que faz:
        Recebe segundos (ex: 225.5) e formata para string (ex: "3:45").
    
    Por que existe:
        Facilita a leitura humana das durações médias nos relatórios.

    Quando é chamada:
        No final do cálculo estatístico, antes de escrever no arquivo .txt.

    Args:
        segundos (float): Tempo em segundos.
        
    Returns:
        str: String formatada (ex: "3:45") ou "N/A" se nulo.
    """
    if pd.isna(segundos):
        return "N/A"
    minutos = int(segundos // 60)
    segundos_restantes = int(segundos % 60)
    return f"{minutos}:{segundos_restantes:02}"

def gerar_resumo_persona(persona, info):
    """
    Processa os dados e gera o arquivo de texto para uma única persona.

    O que faz:
        1. Carrega o CSV.
        2. Calcula todas as estatísticas (Médias, Top Lists, Ranges).
        3. Formata e escreve um relatório TXT estruturado.

    Por que existe:
        Para consolidar os "Key Performance Indicators" (KPIs) de cada perfil
        de forma textual, facilitando citações no texto do TCC.

    Args:
        persona (str): Nome da persona.
        info (dict): Configuração de caminhos {csv_path, output_folder}.
    """
    print(f"\n{'='*20} GERANDO RESUMO PARA: {persona.upper()} {'='*20}")
    
    csv_path = info['csv_path']
    output_folder = info['output_folder']
    # Define o caminho final do arquivo de texto com padrão: summarie_Nome.txt
    output_path = os.path.join(output_folder, f'summarie_{persona.capitalize()}.txt')

    # Garante a existência da pasta de destino
    os.makedirs(output_folder, exist_ok=True)

    try:
        # Carregamento do Dataset
        df = pd.read_csv(csv_path)
        
        # --- Limpeza e Tipagem de Dados (Data Cleaning) ---
        # Conversão necessária pois CSVs não guardam tipos de dados (tudo é texto/número genérico).
        df['album_release_year'] = pd.to_datetime(df['album_release_date'], errors='coerce').dt.year
        df['track_popularity'] = pd.to_numeric(df['track_popularity'], errors='coerce')
        df['artist_popularity'] = pd.to_numeric(df['artist_popularity'], errors='coerce')
        # Converte ms para segundos para cálculo de média
        df['duration_sec'] = pd.to_numeric(df.get('duration_ms'), errors='coerce') / 1000
        
        print(f"Arquivo '{csv_path}' carregado com sucesso.")
        
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{csv_path}' não encontrado. Pulando esta persona.")
        return

    # --- CÁLCULO DAS ESTATÍSTICAS DESCRITIVAS ---
    
    # Métricas de Volume
    total_musicas = len(df)
    artistas_unicos = df['primary_artist_name'].nunique()
    
    # Ranking de Artistas (Frequência absoluta)
    contagem_artistas = df['primary_artist_name'].value_counts()

    # Processamento de Gêneros (Explosão de strings compostas)
    # Transforma "pop; rock" em contagens separadas para Pop e Rock
    generos_validos = df['artist_genres'].dropna().astype(str)
    # List comprehension + Split: Técnica padrão para achatar listas de listas (flatten)
    lista_de_todos_os_generos = [genre.strip() for item in generos_validos for genre in item.split(';') if genre.strip()]
    todos_os_generos_ordenados = Counter(lista_de_todos_os_generos).most_common()

    # Médias e Extremos
    media_pop_musica = df['track_popularity'].mean()
    media_pop_artista = df['artist_popularity'].mean()
    
    ano_medio = df['album_release_year'].mean()
    ano_min = df['album_release_year'].min()
    ano_max = df['album_release_year'].max()
    
    duracao_media_seg = df['duration_sec'].mean()
    duracao_media_formatada = formatar_duracao(duracao_media_seg)

    # --- ESCRITA DO RELATÓRIO (IO) ---
    print(f"  - Salvando resumo em '{output_path}'...")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # Cabeçalho
        f.write(f"=============== RESUMO DA PLAYLIST: {persona.upper()} ===============\n\n")
        
        # Bloco 1: Visão Geral
        f.write("--- MÉTRICAS GERAIS ---\n")
        f.write(f"Total de Músicas: {total_musicas}\n")
        f.write(f"Total de Artistas Únicos: {artistas_unicos}\n\n")
        
        # Bloco 2: Popularidade (Indicador de Mainstream)
        f.write("--- MÉTRICAS DE POPULARIDADE ---\n")
        f.write(f"Popularidade Média das Músicas: {media_pop_musica:.2f} / 100\n")
        f.write(f"Popularidade Média dos Artistas: {media_pop_artista:.2f} / 100\n\n")
        
        # Bloco 3: Temporalidade (Indicador de Recência/Nostalgia)
        f.write("--- MÉTRICAS TEMPORAIS (ERA MUSICAL) ---\n")
        f.write(f"Ano Médio de Lançamento: {ano_medio:.0f}\n")
        f.write(f"Música Mais Antiga (ano): {int(ano_min) if not pd.isna(ano_min) else 'N/A'}\n")
        f.write(f"Música Mais Nova (ano): {int(ano_max) if not pd.isna(ano_max) else 'N/A'}\n\n")
        
        # Bloco 4: Estrutura
        f.write("--- MÉTRICAS ESTRUTURAIS ---\n")
        f.write(f"Duração Média das Músicas: {duracao_media_formatada}\n\n")

        # Bloco 5: Gêneros Detalhados
        f.write("--- LISTA COMPLETA DE GÊNEROS (por frequência) ---\n")
        for i, (genero, contagem) in enumerate(todos_os_generos_ordenados):
            ocorrencia_str = "ocorrência" if contagem == 1 else "ocorrências"
            f.write(f"  {i+1}. {genero} ({contagem} {ocorrencia_str})\n")
        f.write("\n")

        # Bloco 6: Artistas Detalhados
        f.write("--- CONCENTRAÇÃO DE ARTISTAS (Nº de Músicas por Artista) ---\n")
        for artista, contagem in contagem_artistas.items():
            f.write(f"  - {artista}: {contagem} música(s)\n")
    
    print(f"  -> Resumo para {persona.upper()} salvo com sucesso.")

# --- Função Principal ---
def main():
    """
    Fluxo principal de processamento e geração de relatórios de texto.
    """
    print("--- Iniciando a geração de resumos textuais por persona ---")
    
    # Define a raiz do projeto dinamicamente
    script_dir = os.path.dirname(os.path.abspath(__file__)) # src/analysis
    project_root = os.path.dirname(os.path.dirname(script_dir)) # TCC root

    # Mapeamento de Configuração:
    # Define onde estão os dados brutos e onde salvar o relatório final.
    ARQUIVOS_DAS_PERSONAS = {
        'beatriz': {
            'csv_path': os.path.join(project_root, 'data', 'processed', 'dataset_Beatriz_playlist.csv'),
            'output_folder': os.path.join(project_root, 'reports', 'summaries')
        },
        'daniel': {
            'csv_path': os.path.join(project_root, 'data', 'processed', 'dataset_Daniel_playlist.csv'),
            'output_folder': os.path.join(project_root, 'reports', 'summaries')
        },
        'ricardo': {
            'csv_path': os.path.join(project_root, 'data', 'processed', 'dataset_Ricardo_playlist.csv'),
            'output_folder': os.path.join(project_root, 'reports', 'summaries')
        },
        'sofia': {
            'csv_path': os.path.join(project_root, 'data', 'processed', 'dataset_Sofia_playlist.csv'),
            'output_folder': os.path.join(project_root, 'reports', 'summaries')
        }
    }

    # --- CONTROLE DE EXECUÇÃO (Argumentos CLI) ---
    if len(sys.argv) < 2:
        print("\n[!] Uso: python build_summaries.py [nome_persona | all]")
        print("    Ex: python build_summaries.py beatriz")
        return

    argumento = sys.argv[1].lower()

    if argumento == "all":
        print("Modo: Gerar resumos para TODAS as personas.")
        for persona, info in ARQUIVOS_DAS_PERSONAS.items():
            gerar_resumo_persona(persona, info)
    else:
        if argumento in ARQUIVOS_DAS_PERSONAS:
            print(f"Modo: Gerar resumo apenas para {argumento.upper()}.")
            gerar_resumo_persona(argumento, ARQUIVOS_DAS_PERSONAS[argumento])
        else:
            print(f"ERRO: Persona '{argumento}' não encontrada.")
            print(f"Opções válidas: {list(ARQUIVOS_DAS_PERSONAS.keys())} ou 'all'")

    print(f"\n{'='*20} PROCESSO FINALIZADO {'='*20}")

if __name__ == "__main__":
    main()