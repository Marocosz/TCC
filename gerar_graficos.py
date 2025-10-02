# gerar_graficos.py

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter

def calcular_top_generos(series_generos, top_n=10):
    """
    Função auxiliar que recebe uma série de strings de gêneros,
    limpa os dados, conta as ocorrências e retorna os top N.
    """
    # Filtra apenas os valores que são strings e não estão vazios
    generos_validos = series_generos.dropna().astype(str)
    
    # Cria uma lista única com todos os gêneros, separados por ';'
    lista_de_todos_os_generos = []
    for item in generos_validos:
        lista_de_todos_os_generos.extend([genre.strip() for genre in item.split(';') if genre.strip()])
    
    # Conta as ocorrências e retorna os mais comuns
    return Counter(lista_de_todos_os_generos).most_common(top_n)

def main():
    """
    Função principal para carregar os dados consolidados, analisá-los
    e gerar gráficos comparativos entre as personas.
    """
    # --- 1. CARREGAMENTO E PREPARAÇÃO DOS DADOS ---
    print("--- PASSO 1: Carregando e preparando os dados do CSV consolidado ---")
    
    CSV_FILE = 'analise_consolidada_input.csv'
    
    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{CSV_FILE}' não encontrado. Verifique o nome e o local do arquivo.")
        return

    # --- Limpeza e Processamento de Dados ---
    df['album_release_year'] = pd.to_datetime(df['album_release_date'], errors='coerce').dt.year
    df['track_popularity'] = pd.to_numeric(df['track_popularity'], errors='coerce')
    df['artist_popularity'] = pd.to_numeric(df['artist_popularity'], errors='coerce')
    df['artist_followers'] = pd.to_numeric(df['artist_followers'], errors='coerce')
    df['duration_sec'] = pd.to_numeric(df.get('duration_ms'), errors='coerce') / 1000 # Usa .get() para segurança

    print("Dados carregados e preparados com sucesso.")
    print("-" * 40)

    # --- 2. GERAÇÃO DOS GRÁFICOS ---
    
    # Define uma paleta de cores e ordem para manter a consistência
    palette = sns.color_palette("husl", len(df['persona'].unique()))
    order = ['beatriz', 'ricardo', 'sofia', 'daniel']
    
    # --- GRÁFICO 1: Análise de Popularidade (Mainstream) ---
    print("\n--- Gerando Gráfico 1: Popularidade (Box Plot) ---")
    plt.figure(figsize=(12, 8))
    sns.boxplot(data=df, x='persona', y='track_popularity', hue='persona', palette=palette, legend=False, order=order)
    plt.title('Distribuição da Popularidade das Músicas por Persona', fontsize=16)
    plt.xlabel('Persona', fontsize=12)
    plt.ylabel('Índice de Popularidade da Música (0-100)', fontsize=12)
    plt.savefig('grafico_popularidade.png')
    print("Gráfico 'grafico_popularidade.png' salvo com sucesso.")
    
    # --- GRÁFICO 2: Análise de Gêneros (Diversidade) ---
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
            sns.barplot(data=df_generos, x='contagem', y='genero', ax=ax, color=palette[i], orient='h')
            ax.set_title(f'Top 10 Gêneros - {persona_name.capitalize()}', fontsize=14)
            ax.set_xlabel('Contagem de Músicas', fontsize=12)
        except (KeyError, IndexError):
            ax.set_title(f'Top 10 Gêneros - {persona_name.capitalize()} (Sem Dados)', fontsize=14)

    plt.tight_layout(pad=3.0)
    plt.savefig('grafico_generos.png')
    print("Gráfico 'grafico_generos.png' salvo com sucesso.")

    # --- GRÁFICO 3: Análise Temporal (Nostalgia) ---
    print("\n--- Gerando Gráfico 3: Época Musical (Violin Plot) ---")
    plt.figure(figsize=(12, 8))
    sns.violinplot(data=df, x='persona', y='album_release_year', hue='persona', palette=palette, legend=False, order=order)
    plt.title('Distribuição do Ano de Lançamento das Músicas por Persona', fontsize=16)
    plt.xlabel('Persona', fontsize=12)
    plt.ylabel('Ano de Lançamento', fontsize=12)
    plt.savefig('grafico_era_musical.png')
    print("Gráfico 'grafico_era_musical.png' salvo com sucesso.")

    # --- GRÁFICO 4: Concentração de Artistas ---
    print("\n--- Gerando Gráfico 4: Concentração de Artistas ---")
    fig, axes = plt.subplots(2, 2, figsize=(20, 15))
    axes = axes.flatten()
    
    for i, persona_name in enumerate(order):
        ax = axes[i]
        try:
            grupo_persona = df[df['persona'] == persona_name]
            top_artistas = grupo_persona['primary_artist_name'].value_counts().nlargest(10)
            sns.barplot(x=top_artistas.values, y=top_artistas.index, ax=ax, color=palette[i], orient='h')
            ax.set_title(f'Top 10 Artistas Mais Frequentes - {persona_name.capitalize()}', fontsize=14)
            ax.set_xlabel('Número de Músicas na Playlist', fontsize=12)
        except (KeyError, IndexError):
            ax.set_title(f'Top 10 Artistas - {persona_name.capitalize()} (Sem Dados)', fontsize=14)

    plt.tight_layout(pad=3.0)
    plt.savefig('grafico_concentracao_artistas.png')
    print("Gráfico 'grafico_concentracao_artistas.png' salvo com sucesso.")

    # --- GRÁFICO 5: Popularidade vs. Seguidores ---
    print("\n--- Gerando Gráfico 5: Popularidade vs. Seguidores ---")
    plt.figure(figsize=(14, 10))
    g = sns.scatterplot(data=df, x='artist_popularity', y='artist_followers', hue='persona', palette=palette, hue_order=order, s=100, alpha=0.7)
    g.set_yscale('log') # Usamos escala logarítmica para ver melhor a distribuição
    plt.title('Análise de Nicho vs. Mainstream (Popularidade vs. Seguidores)', fontsize=16)
    plt.xlabel('Popularidade do Artista (Relevância Atual)', fontsize=12)
    plt.ylabel('Seguidores do Artista (Base de Fãs) - Escala Log', fontsize=12)
    plt.legend(title='Persona')
    plt.savefig('grafico_pop_vs_followers.png')
    print("Gráfico 'grafico_pop_vs_followers.png' salvo com sucesso.")

    # --- GRÁFICO 6: Duração das Músicas ---
# INSIGHT 6: DURAÇÃO DAS MÚSICAS
    print("\n--- Gerando Gráfico 6: Duração das Músicas ---")
    plt.figure(figsize=(12, 8))

    # --- ADICIONE ESTA LINHA ---
    # Cria um novo DataFrame temporário apenas com as linhas que têm um valor válido de duração
    df_duration = df.dropna(subset=['duration_sec'])

    # --- MUDE A LINHA DO GRÁFICO PARA USAR O NOVO DATAFRAME ---
    sns.boxplot(data=df_duration, x='persona', y='duration_sec', hue='persona', palette=palette, legend=False, order=order)
    
    plt.title('Distribuição da Duração das Músicas por Persona', fontsize=16)
    plt.xlabel('Persona', fontsize=12)
    plt.ylabel('Duração da Música (em segundos)', fontsize=12)
    plt.savefig('grafico_duracao_musicas.png')
    print("Gráfico 'grafico_duracao_musicas.png' salvo com sucesso.")

    print("\n--- Processo finalizado! Todos os 6 gráficos foram gerados. ---")
    
if __name__ == "__main__":
    main()