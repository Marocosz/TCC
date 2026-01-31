# TIPO DE ARQUIVO: RECEBE CSV
# build_personal_graphs.py

"""
================================================================================
MÓDULO DE GERAÇÃO DE INSIGHTS VISUAIS POR PERSONA
================================================================================

Objetivo do Arquivo:
    Gerar um conjunto detalhado de gráficos estatísticos INDIVIDUAIS para cada
    Persona. Ao contrário do 'build_cross_graphs.py' que compara todos juntos,
    este script foca na análise profunda e isolada de cada perfil.

Parte do Sistema:
    Analysis (Visualização de Dados).

Responsabilidades:
    1. Leitura de Dados: Carregar os Datasets processados de cada Persona.
    2. Processamento Estatístico: Calcular frequências e distribuições.
    3. Visualização: Gerar 5 tipos de gráficos específicos (Histogramas, Barras).
    4. Persistência de Relatórios: Salvar as imagens PNG.

Comunicação:
    - Entrada: CSVs de 'data/processed/'.
    - Saída: Salva imagens PNG em 'reports/figures/[persona]/'.

Gráficos Gerados:
    1. Popularidade (Histograma)
    2. Top Gêneros (Bar Chart)
    3. Era Musical (Histograma)
    4. Concentração Artistica (Bar Chart)
    5. Scatter Popularidade vs Seguidores

Uso:
    python src/analysis/build_personal_graphs.py [nome_persona]
    python src/analysis/build_personal_graphs.py all
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import os
import sys

# Configurações visuais globais para o Seaborn (Estilo acadêmico/limpo)
sns.set_theme(style="whitegrid", rc={"axes.labelsize": 14, "xtick.labelsize": 12, "ytick.labelsize": 12})

def calcular_top_generos(series_generos, top_n=10):
    """
    Processa a coluna de gêneros (strings compostas) para ranking de frequência.
    
    O que faz:
        - Remove valores nulos.
        - Tokeniza strings separadas por ';' (ex: "pop; rock" -> ["pop", "rock"]).
        - Conta ocorrências e retorna os Top N.

    Por que existe:
        Permite analisar a diversidade real de gêneros, desagrupando termos compostos.

    Quando é chamada:
        Na geração do Gráfico 2 (Diversidade).
        
    Args:
        series_generos (pd.Series): Coluna do DataFrame com gêneros.
        top_n (int): Número de gêneros a retornar (Default: 10).
        
    Returns:
        list: Lista de tuplas [('genero', contagem), ...].
    """
    generos_validos = series_generos.dropna().astype(str)
    # List comprehension aninhada para flatten
    lista_de_todos_os_generos = [genre.strip() for item in generos_validos for genre in item.split(';') if genre.strip()]
    return Counter(lista_de_todos_os_generos).most_common(top_n)

def gerar_graficos_para_persona(persona, config):
    """
    Gera o pacote completo de gráficos para uma única persona.

    O que faz:
        Orquestra a leitura do CSV específico da persona e a plotagem de 5 visualizações.
    
    Por que existe:
        Encapsula a lógica de plotagem para permitir execução modular (uma persona ou todas).

    Args:
        persona (str): Nome da persona (ex: 'beatriz').
        config (dict): Dicionário contendo { 'csv_path': ..., 'output_folder': ... }.
    """
    print(f"\n{'='*20} GERANDO GRÁFICOS PARA: {persona.upper()} {'='*20}")
    
    csv_path = config['csv_path']
    output_folder = config['output_folder']

    # Garante que a pasta de destino exista antes de tentar salvar
    os.makedirs(output_folder, exist_ok=True)

    try:
        # Carregamento e Tratamento Inicial dos Dados
        df = pd.read_csv(csv_path)
        
        # Conversão de Tipos (Essencial para plotagem correta)
        df['album_release_year'] = pd.to_datetime(df['album_release_date'], errors='coerce').dt.year
        for col in ['track_popularity', 'artist_popularity', 'artist_followers']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        print(f"Arquivo '{csv_path}' carregado com sucesso.")
        
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{csv_path}' não encontrado. Pulando esta persona.")
        return

    # ======================================================================
    # GRÁFICO 1: ANÁLISE DE POPULARIDADE (Histograma)
    # ----------------------------------------------------------------------
    # Objetivo: Visualizar se a persona consome mais hits (curva à direita)
    # ou músicas desconhecidas (curva à esquerda).
    # ======================================================================
    print("  - Gerando Gráfico 1: Popularidade...")
    plt.figure(figsize=(10, 6))
    sns.histplot(data=df, x='track_popularity', kde=True, bins=20)
    plt.title(f'Insight 1: Distribuição da Popularidade das Músicas ({persona.capitalize()})', fontsize=16)
    plt.xlabel('Índice de Popularidade da Música')
    plt.ylabel('Contagem')
    plt.savefig(os.path.join(output_folder, 'insight_1_popularidade.png'))
    plt.close() # Libera memória

    # ======================================================================
    # GRÁFICO 2: DIVERSIDADE DE GÊNEROS (Bar Chart Horizontal)
    # ----------------------------------------------------------------------
    # Objetivo: Identificar a "bolha" de gêneros da persona.
    # ======================================================================
    print("  - Gerando Gráfico 2: Gêneros...")
    plt.figure(figsize=(12, 8))
    
    top_generos = calcular_top_generos(df['artist_genres'], top_n=10)
    
    if top_generos:
        df_generos = pd.DataFrame(top_generos, columns=['genero', 'contagem'])
        sns.barplot(data=df_generos, x='contagem', y='genero', orient='h')
        plt.title(f'Insight 2: Top 10 Gêneros Musicais ({persona.capitalize()})', fontsize=16)
        plt.xlabel('Contagem de Músicas')
        plt.ylabel('Gênero')
        plt.tight_layout()
        plt.savefig(os.path.join(output_folder, 'insight_2_generos.png'))
    plt.close()

    # ======================================================================
    # GRÁFICO 3: ANÁLISE TEMPORAL (Histograma)
    # ----------------------------------------------------------------------
    # Objetivo: Verificar o viés de recência ou nostalgia.
    # ======================================================================
    print("  - Gerando Gráfico 3: Época Musical...")
    plt.figure(figsize=(10, 6))
    # Filtra anos inválidos (NaN) para evitar erros no plot
    sns.histplot(data=df.dropna(subset=['album_release_year']), x='album_release_year', kde=True, bins=25)
    plt.title(f'Insight 3: A "Era Musical" da Playlist ({persona.capitalize()})', fontsize=16)
    plt.xlabel('Ano de Lançamento do Álbum')
    plt.ylabel('Contagem')
    plt.savefig(os.path.join(output_folder, 'insight_3_era_musical.png'))
    plt.close()

    # ======================================================================
    # GRÁFICO 4: CONCENTRAÇÃO DE ARTISTAS (Bar Chart)
    # ----------------------------------------------------------------------
    # Objetivo: Medir repetitividade. Se poucos artistas dominam o gráfico,
    # indica baixa variedade.
    # ======================================================================
    print("  - Gerando Gráfico 4: Concentração de Artistas...")
    plt.figure(figsize=(12, 8))
    top_artistas = df['primary_artist_name'].value_counts().nlargest(15)
    sns.barplot(x=top_artistas.values, y=top_artistas.index, orient='h')
    plt.title(f'Insight 4: Top 15 Artistas Mais Frequentes ({persona.capitalize()})', fontsize=16)
    plt.xlabel('Número de Músicas na Playlist')
    plt.ylabel('Artista')
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, 'insight_4_concentracao_artistas.png'))
    plt.close()

    # ======================================================================
    # GRÁFICO 5: POPULARIDADE VS. SEGUIDORES (Scatter Plot Logarítmico)
    # ----------------------------------------------------------------------
    # Objetivo: Analisar o perfil dos artistas (Mainstream vs Indie).
    # Escala Log usada no eixo Y para visualizar melhor a disparidade de seguidores.
    # ======================================================================
    print("  - Gerando Gráfico 5: Natureza da Fama...")
    plt.figure(figsize=(12, 8))
    # Remove duplicatas de artistas para não enviesar o gráfico com pontos repetidos
    df_artists = df.drop_duplicates(subset=['primary_artist_name'])
    
    g = sns.scatterplot(data=df_artists, x='artist_popularity', y='artist_followers', s=100, alpha=0.7)
    g.set_yscale('log')
    
    plt.title(f'Insight 5: Perfil de Fama dos Artistas ({persona.capitalize()})', fontsize=16)
    plt.xlabel('Popularidade do Artista (Hype Recente)')
    plt.ylabel('Seguidores do Artista (Base de Fãs) - Escala Log')
    plt.grid(True, which="both", ls="--")
    plt.savefig(os.path.join(output_folder, 'insight_5_pop_vs_followers.png'))
    plt.close()
    
    print(f"  -> Gráficos para {persona.upper()} salvos na pasta '{output_folder}'.")

def main():
    """
    Fluxo principal de geração de relatórios visuais.
    Gerencia argumentos de CLI para decidir se gera para 'all' ou específica.
    """
    # --- 1. PAINEL DE CONTROLE (CONFIGURAÇÕES) ---
    print("--- Iniciando a geração de insights individuais por persona ---")
    
    # Define a raiz do projeto dinamicamente
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    
    # Caminhos base
    data_processed_dir = os.path.join(project_root, 'data', 'processed')
    reports_figures_dir = os.path.join(project_root, 'reports', 'figures')

    # Mapeamento Central: Define onde buscar os dados e onde salvar os gráficos.
    ARQUIVOS_DAS_PERSONAS = {
        'beatriz': {
            'csv_path': os.path.join(data_processed_dir, 'dataset_Beatriz_playlist.csv'),
            'output_folder': os.path.join(reports_figures_dir, 'beatriz')
        },
        'daniel': {
            'csv_path': os.path.join(data_processed_dir, 'dataset_Daniel_playlist.csv'),
            'output_folder': os.path.join(reports_figures_dir, 'daniel')
        },
        'ricardo': {
            'csv_path': os.path.join(data_processed_dir, 'dataset_Ricardo_playlist.csv'),
            'output_folder': os.path.join(reports_figures_dir, 'ricardo')
        },
        'sofia': {
            'csv_path': os.path.join(data_processed_dir, 'dataset_Sofia_playlist.csv'),
            'output_folder': os.path.join(reports_figures_dir, 'sofia')
        }
    }

    # --- 2. CONTROLE DE EXECUÇÃO (Argumentos CLI) ---
    if len(sys.argv) < 2:
        print("\n[!] Uso: python build_personal_graphs.py [nome_persona | all]")
        print("    Ex: python build_personal_graphs.py beatriz")
        return

    argumento = sys.argv[1].lower()

    if argumento == "all":
        print("Modo: Gerar gráficos para TODAS as personas.")
        for persona, config in ARQUIVOS_DAS_PERSONAS.items():
            gerar_graficos_para_persona(persona, config)
    else:
        if argumento in ARQUIVOS_DAS_PERSONAS:
            print(f"Modo: Gerar gráficos apenas para {argumento.upper()}.")
            gerar_graficos_para_persona(argumento, ARQUIVOS_DAS_PERSONAS[argumento])
        else:
            print(f"ERRO: Persona '{argumento}' não encontrada.")
            print(f"Opções válidas: {list(ARQUIVOS_DAS_PERSONAS.keys())} ou 'all'")

    print(f"\n{'='*20} PROCESSO FINALIZADO {'='*20}")

if __name__ == "__main__":
    main()