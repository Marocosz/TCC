# TIPO DE ARQUIVO: RECEBE CSV
# build_cross_graphs.py

"""
================================================================================
MÓDULO DE VISUALIZAÇÃO DE DADOS E GERAÇÃO DE INSIGHTS CRUZADOS
================================================================================

Objetivo do Arquivo:
    Transformar os dados tabulares brutos (CSV consolidado) em representações
    visuais (gráficos estáticos) que fundamentam a argumentação do TCC.
    Gera "provas visuais" da auditoria algorítmica, comparando o comportamento 
    das diferentes Personas lado a lado.

Parte do Sistema:
    Analysis (Visualização de Dados).

Responsabilidades:
    1. Carregamento e Tipagem: Ler o dataset consolidado e corrigir tipos de dados.
    2. Engenharia de Features: Criar colunas derivadas (ex: duração em segundos).
    3. Padronização Visual: Garantir que cada Persona tenha sempre a mesma cor.
    4. Geração de Figuras: Criar 6 tipos de gráficos comparativos.

Comunicação:
    - Entrada: 'data/processed/dataset_consolidada_input.csv'.
    - Saída: Arquivos .png em 'reports/figures/cross/'.

Uso:
    python src/analysis/build_cross_graphs.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import os

def calcular_top_generos(series_generos, top_n=10):
    """
    Processa a coluna de gêneros (strings compostas) para ranking.

    O que faz:
        Recebe uma série de strings (ex: "pop; rock"), quebra nos delimitadores,
        conta a frequência de cada termo individual e retorna os Top N.

    Por que existe:
        O Spotify retorna múltiplos gêneros concatenados. Para analisar diversidade
        real, precisamos contar "Pop" e "Rock" separadamente, não a combinação única.

    Quando é chamada:
        Durante a geração do Gráfico 2 (Diversidade de Gêneros).

    Args:
        series_generos (pd.Series): Coluna do DataFrame contendo strings de gêneros.
        top_n (int): Quantidade de itens a retornar (Default: 10).

    Returns:
        list: Lista de tuplas [('genero', contagem), ...] ordenada por frequência.
    """
    # Filtra nulos e converte para string para evitar erros de iteração
    generos_validos = series_generos.dropna().astype(str)
    
    # Tokenização: Separa a string composta pelo delimitador ';' usado na coleta
    lista_de_todos_os_generos = []
    for item in generos_validos:
        # Strip remove espaços em branco extras que podem duplicar contagens (ex: " pop" vs "pop")
        lista_de_todos_os_generos.extend([genre.strip() for genre in item.split(';') if genre.strip()])
    
    # Retorna os N mais comuns usando Counter (otimizado para contagem hashable)
    return Counter(lista_de_todos_os_generos).most_common(top_n)

def main():
    """
    Função Principal (Pipeline de Visualização).

    O que faz:
        1. Carrega o CSV consolidado.
        2. Aplica casting de tipos (numéricos e datas).
        3. Define paleta de cores consistente.
        4. Gera e salva 5 gráficos comparativos (Boxplots, Violins, Scatters).

    Por que existe:
        Para automatizar a geração de TODAS as figuras comparativas do TCC de uma vez.
    """
    # ==========================================================================
    # 1. CARREGAMENTO E PREPARAÇÃO DOS DADOS (ETL)
    # ==========================================================================
    print("--- PASSO 1: Carregando e preparando os dados do CSV consolidado ---")
    
    # Define a raiz do projeto dinamicamente
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))

    # Arquivo gerado pela etapa de consolidação anterior
    CSV_FILE = os.path.join(project_root, 'data', 'processed', 'dataset_consolidada_input.csv')
    OUTPUT_DIR = os.path.join(project_root, 'reports', 'figures', 'cross')

    # Garante a criação da pasta de saída
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{CSV_FILE}' não encontrado. Execute 'merge_datasets.py' primeiro.")
        return

    # Tratamento de Tipos (Casting)
    # Necessário pois CSV perde tipagem original
    df['album_release_year'] = pd.to_datetime(df['album_release_date'], errors='coerce').dt.year
    df['track_popularity'] = pd.to_numeric(df['track_popularity'], errors='coerce')
    df['artist_popularity'] = pd.to_numeric(df['artist_popularity'], errors='coerce')
    df['artist_followers'] = pd.to_numeric(df['artist_followers'], errors='coerce')
    
    # Normalização: ms para segundos
    df['duration_sec'] = pd.to_numeric(df.get('duration_ms'), errors='coerce') / 1000 

    print("Dados carregados e preparados com sucesso.")
    print("-" * 40)

    # ==========================================================================
    # 2. CONFIGURAÇÃO VISUAL GLOBAL
    # ==========================================================================
    
    # Paleta consistente: garante que cada Persona tenha sua cor fixa (Brand Identity do TCC)
    # Isso evita que as cores mudem dependendo de quantos dados existem no CSV.
    palette = {
        'beatriz': '#FF007F', # Rosa/Magenta (Pop/Vibrante)
        'ricardo': '#0000FF', # Azul (Clássico/Rock)
        'sofia':   '#800080', # Roxo (Indie/Misterioso)
        'daniel':  '#008000'  # Verde (Lo-Fi/Calmo)
    }
    order = ['beatriz', 'ricardo', 'sofia', 'daniel']
    
    # ==========================================================================
    # GRÁFICO 1: ANÁLISE DE POPULARIDADE (Mainstream vs Nicho)
    # --------------------------------------------------------------------------
    # Insight: Comparar a mediana e dispersão da popularidade das faixas.
    # Esperado: Beatriz no topo, Sofia em baixo.
    # ==========================================================================
    print("\n--- Gerando Gráfico 1: Popularidade (Box Plot) ---")
    plt.figure(figsize=(12, 8))
    sns.boxplot(data=df, x='persona', y='track_popularity', hue='persona', palette=palette, legend=False, order=order)
    plt.title('Distribuição da Popularidade das Músicas por Persona', fontsize=16)
    plt.xlabel('Persona', fontsize=12)
    plt.ylabel('Índice de Popularidade da Música (0-100)', fontsize=12)
    plt.savefig(os.path.join(OUTPUT_DIR, 'grafico_popularidade.png'))
    print(f"Gráfico 'grafico_popularidade.png' salvo.")
    
    # ==========================================================================
    # GRÁFICO 2: ANÁLISE DE DIVERSIDADE DE GÊNEROS
    # --------------------------------------------------------------------------
    # Insight: Verificar a "Entropia de Gênero" e bolhas de filtro.
    # Esperado: Daniel com distribuição mais plana (caos), Sofia com nichos específicos.
    # ==========================================================================
    print("\n--- Gerando Gráfico 2: Diversidade de Gêneros (Bar Chart) ---")
    fig, axes = plt.subplots(2, 2, figsize=(20, 15))
    axes = axes.flatten()
    
    for i, persona_name in enumerate(order):
        ax = axes[i]
        try:
            grupo_persona = df[df['persona'] == persona_name]
            top_generos = calcular_top_generos(grupo_persona['artist_genres'], top_n=10)
            
            if not top_generos: raise KeyError
            
            df_generos = pd.DataFrame(top_generos, columns=['genero', 'contagem'])
            sns.barplot(data=df_generos, x='contagem', y='genero', ax=ax, color=palette[persona_name], orient='h')
            ax.set_title(f'Top 10 Gêneros - {persona_name.capitalize()}', fontsize=14)
            ax.set_xlabel('Contagem de Músicas', fontsize=12)
        except (KeyError, IndexError):
            ax.set_title(f'Top 10 Gêneros - {persona_name.capitalize()} (Sem Dados)', fontsize=14)

    plt.tight_layout(pad=3.0)
    plt.savefig(os.path.join(OUTPUT_DIR, 'grafico_generos.png'))
    print(f"Gráfico 'grafico_generos.png' salvo.")

    # ==========================================================================
    # GRÁFICO 3: ANÁLISE TEMPORAL (Viés de Recência)
    # --------------------------------------------------------------------------
    # Insight: Distribuição dos anos de lançamento.
    # Esperado: Ricardo concentrado em 70s/80s/90s.
    # ==========================================================================
    print("\n--- Gerando Gráfico 3: Época Musical (Violin Plot) ---")
    plt.figure(figsize=(12, 8))
    sns.violinplot(data=df, x='persona', y='album_release_year', hue='persona', palette=palette, legend=False, order=order)
    plt.title('Distribuição do Ano de Lançamento das Músicas por Persona', fontsize=16)
    plt.xlabel('Persona', fontsize=12)
    plt.ylabel('Ano de Lançamento', fontsize=12)
    plt.savefig(os.path.join(OUTPUT_DIR, 'grafico_era_musical.png'))
    print(f"Gráfico 'grafico_era_musical.png' salvo.")

    # ==========================================================================
    # GRÁFICO 4: CONCENTRAÇÃO DE ARTISTAS
    # --------------------------------------------------------------------------
    # Insight: Medir repetitividade vs descoberta.
    # ==========================================================================
    print("\n--- Gerando Gráfico 4: Concentração de Artistas ---")
    fig, axes = plt.subplots(2, 2, figsize=(20, 15))
    axes = axes.flatten()
    
    for i, persona_name in enumerate(order):
        ax = axes[i]
        try:
            grupo_persona = df[df['persona'] == persona_name]
            top_artistas = grupo_persona['primary_artist_name'].value_counts().nlargest(10)
            sns.barplot(x=top_artistas.values, y=top_artistas.index, ax=ax, color=palette[persona_name], orient='h')
            ax.set_title(f'Top 10 Artistas Mais Frequentes - {persona_name.capitalize()}', fontsize=14)
            ax.set_xlabel('Número de Músicas na Playlist', fontsize=12)
        except (KeyError, IndexError):
            ax.set_title(f'Top 10 Artistas - {persona_name.capitalize()} (Sem Dados)', fontsize=14)

    plt.tight_layout(pad=3.0)
    plt.savefig(os.path.join(OUTPUT_DIR, 'grafico_concentracao_artistas.png'))
    print(f"Gráfico 'grafico_concentracao_artistas.png' salvo.")

    # ==========================================================================
    # GRÁFICO 5: ANÁLISE DE CAUDA LONGA (Pop vs Followers)
    # --------------------------------------------------------------------------
    # Insight: Relaciona Hype Atual (Popularidade) com Base de Fãs (Seguidores).
    # Uso de escala Log é crucial aqui.
    # ==========================================================================
    print("\n--- Gerando Gráfico 5: Popularidade vs. Seguidores ---")
    plt.figure(figsize=(14, 10))
    g = sns.scatterplot(data=df, x='artist_popularity', y='artist_followers', hue='persona', palette=palette, hue_order=order, s=100, alpha=0.7)
    g.set_yscale('log')
    plt.title('Análise de Nicho vs. Mainstream (Popularidade vs. Seguidores)', fontsize=16)
    plt.xlabel('Popularidade do Artista (Relevância Atual)', fontsize=12)
    plt.ylabel('Seguidores do Artista (Base de Fãs) - Escala Log', fontsize=12)
    plt.legend(title='Persona')
    plt.savefig(os.path.join(OUTPUT_DIR, 'grafico_pop_vs_followers.png'))
    print(f"Gráfico 'grafico_pop_vs_followers.png' salvo.")
    
if __name__ == "__main__":
    main()