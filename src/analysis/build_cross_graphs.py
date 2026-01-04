# build_cross_graphs.py

"""
================================================================================
MÓDULO DE VISUALIZAÇÃO DE DADOS E GERAÇÃO DE INSIGHTS
================================================================================

OBJETIVO DO ARQUIVO:
    Transformar os dados tabulares brutos (CSV consolidado) em representações
    visuais (gráficos estáticos) que fundamentam a argumentação do TCC.
    
    Este script é o responsável por gerar as "provas visuais" da auditoria
    algorítmica, comparando o comportamento das diferentes Personas.

RESPONSABILIDADES:
    1. Carregamento e Tipagem: Ler o dataset consolidado e corrigir tipos de dados.
    2. Engenharia de Features: Criar colunas derivadas (ex: duração em segundos).
    3. Padronização Visual: Garantir que cada Persona tenha sempre a mesma cor
       em todos os gráficos para facilitar a leitura cruzada.
    4. Geração de Figuras: Criar e salvar 6 tipos de gráficos específicos para
       análise de popularidade, diversidade, temporalidade e estrutura musical.

COMUNICAÇÃO:
    - Entrada: Lê 'analise_consolidada_input.csv' (gerado por consolidar_dados.py).
    - Saída: Salva arquivos .png na pasta raiz ou diretório de relatórios.

================================================================================
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter

def calcular_top_generos(series_generos, top_n=10):
    """
    Processa a coluna de gêneros (que contém strings compostas) para ranking.

    Motivação:
        O Spotify retorna gêneros como uma string única (ex: "pop; dance pop").
        Para analisar diversidade, precisamos "explodir" essa string, contar
        cada gênero individualmente e retornar os mais frequentes.

    Args:
        series_generos (pd.Series): Coluna do DataFrame contendo strings de gêneros.
        top_n (int): Quantidade de itens a retornar.

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
    Fluxo principal de execução da pipeline de visualização.
    """
    # ==========================================================================
    # 1. CARREGAMENTO E PREPARAÇÃO DOS DADOS (ETL)
    # ==========================================================================
    print("--- PASSO 1: Carregando e preparando os dados do CSV consolidado ---")
    
    # Arquivo gerado pela etapa de consolidação anterior
    CSV_FILE = 'analise_consolidada_input.csv'
    
    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{CSV_FILE}' não encontrado. Verifique o nome e o local do arquivo.")
        return

    # Tratamento de Tipos (Casting):
    # CSVs perdem a tipagem original (tudo vira string ou int genérico).
    # Aqui forçamos os tipos corretos para permitir cálculos estatísticos e plotagem.
    df['album_release_year'] = pd.to_datetime(df['album_release_date'], errors='coerce').dt.year
    df['track_popularity'] = pd.to_numeric(df['track_popularity'], errors='coerce')
    df['artist_popularity'] = pd.to_numeric(df['artist_popularity'], errors='coerce')
    df['artist_followers'] = pd.to_numeric(df['artist_followers'], errors='coerce')
    
    # Normalização: Converte ms para segundos para facilitar leitura humana no eixo Y
    df['duration_sec'] = pd.to_numeric(df.get('duration_ms'), errors='coerce') / 1000 

    print("Dados carregados e preparados com sucesso.")
    print("-" * 40)

    # ==========================================================================
    # 2. CONFIGURAÇÃO VISUAL GLOBAL
    # ==========================================================================
    
    # Define uma paleta de cores consistente baseada no número de personas únicas.
    # A lista 'order' garante que a Beatriz seja sempre a cor X e o Daniel a cor Y,
    # independente da ordem dos dados no arquivo.
    palette = sns.color_palette("husl", len(df['persona'].unique()))
    order = ['beatriz', 'ricardo', 'sofia', 'daniel']
    
    # ==========================================================================
    # GRÁFICO 1: ANÁLISE DE POPULARIDADE (Mainstream vs Nicho)
    # --------------------------------------------------------------------------
    # Insight Buscado:
    # Comparar a mediana e a dispersão da popularidade.
    # - Beatriz deve estar no topo (Mainstream).
    # - Sofia deve estar em baixo (Nicho).
    # - Se o Spotify homogeneizar, as caixas tendem a subir e se estreitar.
    # ==========================================================================
    print("\n--- Gerando Gráfico 1: Popularidade (Box Plot) ---")
    plt.figure(figsize=(12, 8))
    sns.boxplot(data=df, x='persona', y='track_popularity', hue='persona', palette=palette, legend=False, order=order)
    plt.title('Distribuição da Popularidade das Músicas por Persona', fontsize=16)
    plt.xlabel('Persona', fontsize=12)
    plt.ylabel('Índice de Popularidade da Música (0-100)', fontsize=12)
    plt.savefig('grafico_popularidade.png')
    print("Gráfico 'grafico_popularidade.png' salvo com sucesso.")
    
    # ==========================================================================
    # GRÁFICO 2: ANÁLISE DE DIVERSIDADE DE GÊNEROS
    # --------------------------------------------------------------------------
    # Insight Buscado:
    # Verificar a "Entropia de Gênero".
    # - Personas como Daniel (Caos) devem ter barras menores e mais distribuídas.
    # - Personas de nicho (Sofia) podem ter gêneros muito específicos.
    # - O algoritmo tende a reduzir essa diversidade?
    # ==========================================================================
    print("\n--- Gerando Gráfico 2: Diversidade de Gêneros (Bar Chart) ---")
    fig, axes = plt.subplots(2, 2, figsize=(20, 15)) # Cria grid 2x2
    axes = axes.flatten()
    
    for i, persona_name in enumerate(order):
        ax = axes[i]
        try:
            # Filtra dados apenas da persona atual do loop
            grupo_persona = df[df['persona'] == persona_name]
            
            # Chama função auxiliar para processar a string de gêneros
            top_generos = calcular_top_generos(grupo_persona['artist_genres'], top_n=10)
            
            if not top_generos: raise KeyError
            
            # Prepara DataFrame temporário para plotagem
            df_generos = pd.DataFrame(top_generos, columns=['genero', 'contagem'])
            
            sns.barplot(data=df_generos, x='contagem', y='genero', ax=ax, color=palette[i], orient='h')
            ax.set_title(f'Top 10 Gêneros - {persona_name.capitalize()}', fontsize=14)
            ax.set_xlabel('Contagem de Músicas', fontsize=12)
        except (KeyError, IndexError):
            # Tratamento para casos onde a persona não tem dados suficientes ou gêneros vazios
            ax.set_title(f'Top 10 Gêneros - {persona_name.capitalize()} (Sem Dados)', fontsize=14)

    plt.tight_layout(pad=3.0)
    plt.savefig('grafico_generos.png')
    print("Gráfico 'grafico_generos.png' salvo com sucesso.")

    # ==========================================================================
    # GRÁFICO 3: ANÁLISE TEMPORAL (Viés de Recência vs Nostalgia)
    # --------------------------------------------------------------------------
    # Insight Buscado:
    # O Violin Plot mostra a densidade de distribuição dos anos.
    # - Ricardo deve ter um "bojo" nos anos 70/80/90.
    # - A IA tende a recomendar músicas novas (viés de recência) mesmo para perfis retrô?
    # ==========================================================================
    print("\n--- Gerando Gráfico 3: Época Musical (Violin Plot) ---")
    plt.figure(figsize=(12, 8))
    sns.violinplot(data=df, x='persona', y='album_release_year', hue='persona', palette=palette, legend=False, order=order)
    plt.title('Distribuição do Ano de Lançamento das Músicas por Persona', fontsize=16)
    plt.xlabel('Persona', fontsize=12)
    plt.ylabel('Ano de Lançamento', fontsize=12)
    plt.savefig('grafico_era_musical.png')
    print("Gráfico 'grafico_era_musical.png' salvo com sucesso.")

    # ==========================================================================
    # GRÁFICO 4: CONCENTRAÇÃO DE ARTISTAS (Bolha de Filtro)
    # --------------------------------------------------------------------------
    # Insight Buscado:
    # Medir a repetitividade.
    # - Se o topo é dominado por poucos artistas com muitas músicas, indica "Bolha".
    # - Uma distribuição plana indica alta descoberta/variação.
    # ==========================================================================
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

    # ==========================================================================
    # GRÁFICO 5: ANÁLISE DE CAUDA LONGA (Pop vs Followers)
    # --------------------------------------------------------------------------
    # Insight Buscado (Crucial para o TCC):
    # Relaciona "Hype Atual" (Popularidade) com "Base Consolidada" (Seguidores).
    # - Escala Logarítmica (set_yscale('log')) é usada porque o número de seguidores
    #   varia exponencialmente (de 1.000 a 100.000.000).
    # - Permite visualizar se a IA recomenda apenas "Blockbusters" ou "Indies".
    # ==========================================================================
    print("\n--- Gerando Gráfico 5: Popularidade vs. Seguidores ---")
    plt.figure(figsize=(14, 10))
    g = sns.scatterplot(data=df, x='artist_popularity', y='artist_followers', hue='persona', palette=palette, hue_order=order, s=100, alpha=0.7)
    g.set_yscale('log') # Ajuste técnico essencial para visualização de dados de rede social
    plt.title('Análise de Nicho vs. Mainstream (Popularidade vs. Seguidores)', fontsize=16)
    plt.xlabel('Popularidade do Artista (Relevância Atual)', fontsize=12)
    plt.ylabel('Seguidores do Artista (Base de Fãs) - Escala Log', fontsize=12)
    plt.legend(title='Persona')
    plt.savefig('grafico_pop_vs_followers.png')
    print("Gráfico 'grafico_pop_vs_followers.png' salvo com sucesso.")

    # ==========================================================================
    # GRÁFICO 6: DURAÇÃO DAS MÚSICAS (Economia da Atenção)
    # --------------------------------------------------------------------------
    # Insight Buscado:
    # Verificar se o algoritmo privilegia músicas curtas (otimizadas para streaming).
    # - Músicas mais curtas geram mais plays e royalties.
    # ==========================================================================
    print("\n--- Gerando Gráfico 6: Duração das Músicas ---")
    plt.figure(figsize=(12, 8))

    # Filtragem preventiva: Remove linhas sem duração válida para não quebrar o plot
    df_duration = df.dropna(subset=['duration_sec'])

    sns.boxplot(data=df_duration, x='persona', y='duration_sec', hue='persona', palette=palette, legend=False, order=order)
    
    plt.title('Distribuição da Duração das Músicas por Persona', fontsize=16)
    plt.xlabel('Persona', fontsize=12)
    plt.ylabel('Duração da Música (em segundos)', fontsize=12)
    plt.savefig('grafico_duracao_musicas.png')
    print("Gráfico 'grafico_duracao_musicas.png' salvo com sucesso.")

    print("\n--- Processo finalizado! Todos os 6 gráficos foram gerados. ---")
    
if __name__ == "__main__":
    main()