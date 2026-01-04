# gerar_insights_individuais.py

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import os

# Configurações visuais para os gráficos
sns.set_theme(style="whitegrid", rc={"axes.labelsize": 14, "xtick.labelsize": 12, "ytick.labelsize": 12})

def calcular_top_generos(series_generos, top_n=10):
    """Função auxiliar para contar e retornar os top N gêneros."""
    generos_validos = series_generos.dropna().astype(str)
    lista_de_todos_os_generos = [genre.strip() for item in generos_validos for genre in item.split(';') if genre.strip()]
    return Counter(lista_de_todos_os_generos).most_common(top_n)

def main():
    """
    Função principal que carrega os dados de cada persona individualmente,
    analisa e salva os gráficos de insights em suas respectivas pastas.
    """
    # --- 1. PAINEL DE CONTROLE (CONFIGURAÇÕES) ---
    print("--- Iniciando a geração de insights individuais por persona ---")
    
    # Mapeia o nome da persona para o caminho do seu CSV e a pasta de saída
    ARQUIVOS_DAS_PERSONAS = {
        'beatriz': {
            'csv_path': 'beatriz/analise_Beatriz_playlist.csv',
            'output_folder': 'beatriz/'
        },
        'daniel': {
            'csv_path': 'daniel/analise_Daniel_playlist.csv',
            'output_folder': 'daniel/'
        },
        'ricardo': {
            'csv_path': 'ricardo/analise_Ricardo_playlist.csv',
            'output_folder': 'ricardo/'
        },
        'sofia': {
            'csv_path': 'sofia/analise_Sofia_playlist.csv',
            'output_folder': 'sofia/'
        }
    }

    # --- 2. LOOP DE GERAÇÃO DE GRÁFICOS PARA CADA PERSONA ---
    for persona, info in ARQUIVOS_DAS_PERSONAS.items():
        print(f"\n{'='*20} GERANDO GRÁFICOS PARA: {persona.upper()} {'='*20}")
        
        csv_path = info['csv_path']
        output_folder = info['output_folder']

        # Garante que a pasta de saída existe
        os.makedirs(output_folder, exist_ok=True)

        try:
            df = pd.read_csv(csv_path)
            # Limpeza e preparação dos dados
            df['album_release_year'] = pd.to_datetime(df['album_release_date'], errors='coerce').dt.year
            for col in ['track_popularity', 'artist_popularity', 'artist_followers']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            print(f"Arquivo '{csv_path}' carregado com sucesso.")
        except FileNotFoundError:
            print(f"ERRO: Arquivo '{csv_path}' não encontrado. Pulando esta persona.")
            continue

        # --- GRÁFICO 1: ANÁLISE DE POPULARIDADE ---
        print("  - Gerando Gráfico 1: Popularidade...")
        plt.figure(figsize=(10, 6))
        sns.histplot(data=df, x='track_popularity', kde=True, bins=20)
        plt.title(f'Insight 1: Distribuição da Popularidade das Músicas ({persona.capitalize()})', fontsize=16)
        plt.xlabel('Índice de Popularidade da Música')
        plt.ylabel('Contagem')
        plt.savefig(os.path.join(output_folder, 'insight_1_popularidade.png'))
        plt.close()

        # --- GRÁFICO 2: DIVERSIDADE DE GÊNEROS ---
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

        # --- GRÁFICO 3: ANÁLISE TEMPORAL ---
        print("  - Gerando Gráfico 3: Época Musical...")
        plt.figure(figsize=(10, 6))
        sns.histplot(data=df.dropna(subset=['album_release_year']), x='album_release_year', kde=True, bins=25)
        plt.title(f'Insight 3: A "Era Musical" da Playlist ({persona.capitalize()})', fontsize=16)
        plt.xlabel('Ano de Lançamento do Álbum')
        plt.ylabel('Contagem')
        plt.savefig(os.path.join(output_folder, 'insight_3_era_musical.png'))
        plt.close()

        # --- GRÁFICO 4: CONCENTRAÇÃO DE ARTISTAS ---
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

        # --- GRÁFICO 5: POPULARIDADE VS. SEGUIDORES ---
        print("  - Gerando Gráfico 5: Natureza da Fama...")
        plt.figure(figsize=(12, 8))
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