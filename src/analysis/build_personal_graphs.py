# build_personal_graphs.py

"""
================================================================================
MÓDULO DE GERAÇÃO DE INSIGHTS VISUAIS POR PERSONA
================================================================================

OBJETIVO DO ARQUIVO:
    Gerar um conjunto detalhado de gráficos estatísticos INDIVIDUAIS para cada
    Persona. Ao contrário do 'gerar_graficos.py' que compara todos juntos,
    este script foca na análise profunda e isolada de cada perfil.

RESPONSABILIDADES:
    1. Leitura de Dados: Carregar os Datasets processados de cada Persona.
    2. Processamento Estatístico: Calcular frequências de gêneros, artistas e distribuição temporal.
    3. Visualização: Gerar 5 tipos de gráficos específicos (Histogramas, Barras, Dispersão).
    4. Persistência de Relatórios: Salvar as imagens geradas na pasta de relatórios.

COMUNICAÇÃO:
    - Entrada: Lê arquivos CSV de 'data/processed/'.
    - Saída: Salva imagens PNG em 'reports/figures/[persona]/'.

GRÁFICOS GERADOS:
    1. Distribuição de Popularidade (Histograma)
    2. Top Gêneros Musicais (Bar Chart)
    3. Era Musical / Ano de Lançamento (Histograma Temporal)
    4. Concentração de Artistas (Bar Chart)
    5. Dispersão Popularidade vs Seguidores (Scatter Plot)
================================================================================
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import os

# Configurações visuais globais para o Seaborn (Estilo acadêmico/limpo)
sns.set_theme(style="whitegrid", rc={"axes.labelsize": 14, "xtick.labelsize": 12, "ytick.labelsize": 12})

def calcular_top_generos(series_generos, top_n=10):
    """
    Processa a coluna de gêneros (strings compostas) para ranking de frequência.
    
    Lógica:
        - Remove valores nulos.
        - Tokeniza strings separadas por ';' (ex: "pop; rock" -> ["pop", "rock"]).
        - Conta ocorrências e retorna os Top N.
        
    Args:
        series_generos (pd.Series): Coluna do DataFrame com gêneros.
        top_n (int): Número de gêneros a retornar.
        
    Returns:
        list: Lista de tuplas [('genero', contagem), ...].
    """
    generos_validos = series_generos.dropna().astype(str)
    lista_de_todos_os_generos = [genre.strip() for item in generos_validos for genre in item.split(';') if genre.strip()]
    return Counter(lista_de_todos_os_generos).most_common(top_n)

def main():
    """
    Fluxo principal de geração de relatórios visuais.
    """
    # --- 1. PAINEL DE CONTROLE (CONFIGURAÇÕES) ---
    print("--- Iniciando a geração de insights individuais por persona ---")
    
    # Mapeamento Central: Define onde buscar os dados e onde salvar os gráficos.
    # ATUALIZAÇÃO: Caminhos ajustados para a nova estrutura de pastas (data/processed e reports/figures).
    ARQUIVOS_DAS_PERSONAS = {
        'beatriz': {
            'csv_path': '../../data/processed/dataset_Beatriz_playlist.csv',
            'output_folder': '../../reports/figures/beatriz/'
        },
        'daniel': {
            'csv_path': '../../data/processed/dataset_Daniel_playlist.csv',
            'output_folder': '../../reports/figures/daniel/'
        },
        'ricardo': {
            'csv_path': '../../data/processed/dataset_Ricardo_playlist.csv',
            'output_folder': '../../reports/figures/ricardo/'
        },
        'sofia': {
            'csv_path': '../../data/processed/dataset_Sofia_playlist.csv',
            'output_folder': '../../reports/figures/sofia/'
        }
    }

    # --- 2. LOOP DE GERAÇÃO (Itera sobre cada Persona configurada) ---
    for persona, info in ARQUIVOS_DAS_PERSONAS.items():
        print(f"\n{'='*20} GERANDO GRÁFICOS PARA: {persona.upper()} {'='*20}")
        
        csv_path = info['csv_path']
        output_folder = info['output_folder']

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
            continue

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

    print(f"\n{'='*20} PROCESSO FINALIZADO {'='*20}")

if __name__ == "__main__":
    main()