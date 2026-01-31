"""
================================================================================
MÓDULO DE MÉTRICAS DE MERCADO E CAUDA LONGA (MARKET ANALYSIS)
================================================================================

Objetivo:
    Aplicar conceitos de Economia da Cultura (Concentração e Long Tail) para
    auditar o valor comercial e a distribuição de poder nas playlists.

Métricas Calculadas:
    1. HHI (Herfindahl-Hirschman Index): Mede a concentração de gêneros.
       - HHI > 0.25 indica alta concentração (Monopólio de estilo).
       - HHI < 0.15 indica mercado competitivo (Diversidade real).
    
    2. Long Tail Tiers (Camadas de Fama):
       - Head (Superstars): > 1 Milhão de seguidores.
       - Mid (Classe Média): Entre 50k e 1M seguidores.
       - Tail (Nicho/Indie): < 50k seguidores.

Resultado:
    Gera um relatório CSV (tabela_mercado.csv) com as porcentagens exatas
    de cada camada para cada persona.

Uso:
    python src/analysis/build_market_metrics.py
"""

import pandas as pd
import numpy as np
import os

def calculate_hhi(series):
    """
    Calcula o Índice Herfindahl-Hirschman (HHI).
    Fórmula: Soma dos quadrados das participações de mercado (%).
    Retorna valor entre 0 e 1.
    """
    if len(series) == 0: return 0
    
    # Conta frequência de cada item (ex: Gênero)
    counts = series.value_counts()
    total = counts.sum()
    
    # Calcula participação (share) de cada um (ex: 0.5, 0.3...)
    shares = counts / total
    
    # Soma dos quadrados
    hhi = (shares ** 2).sum()
    return hhi

def categorize_tier(followers):
    """Classifica o artista com base no número de seguidores."""
    if pd.isna(followers): return 'Unknown'
    if followers >= 1_000_000:
        return 'Head (Superstars)'
    elif followers >= 50_000:
        return 'Mid (Médio Porte)'
    else:
        return 'Tail (Nicho/Indie)'

def main():
    print("--- Calculando Métricas de Economia da Cultura (HHI & Long Tail) ---")
    
    # Configuração de Caminhos
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    data_dir = os.path.join(project_root, 'data', 'processed')
    
    personas = ['beatriz', 'daniel', 'ricardo', 'sofia']
    results = []

    for persona in personas:
        csv_path = os.path.join(data_dir, f'dataset_{persona.capitalize()}_playlist.csv')
        
        try:
            df = pd.read_csv(csv_path)
            
            # --- 1. CÁLCULO DO HHI DE GÊNEROS ---
            # Precisamos explodir os gêneros (que estão como 'pop;rock') para contar corretamente
            all_genres = []
            for item in df['artist_genres'].dropna().astype(str):
                # Separa e limpa espaços
                genres = [g.strip() for g in item.split(';') if g.strip()]
                all_genres.extend(genres)
            
            # Cria uma Series pandas com todos os gêneros individuais
            series_genres = pd.Series(all_genres)
            hhi_genre = calculate_hhi(series_genres)
            
            # --- 2. CÁLCULO DA CAUDA LONGA (TIERS) ---
            # Aplica a função de categoria em cada linha
            # Removemos duplicatas de artistas para não contar o mesmo artista 10 vezes
            df_unique_artists = df.drop_duplicates(subset=['primary_artist_name'])
            
            tiers = df_unique_artists['artist_followers'].apply(categorize_tier)
            tier_counts = tiers.value_counts(normalize=True) # Retorna porcentagem (0.0 a 1.0)
            
            # Pega as porcentagens (se não existir, põe 0)
            pct_head = tier_counts.get('Head (Superstars)', 0) * 100
            pct_mid = tier_counts.get('Mid (Médio Porte)', 0) * 100
            pct_tail = tier_counts.get('Tail (Nicho/Indie)', 0) * 100
            
            results.append({
                'Persona': persona.capitalize(),
                'Concentração de Gênero (HHI)': round(hhi_genre, 4),
                '% Superstars (>1M seg)': round(pct_head, 1),
                '% Médios (50k-1M seg)': round(pct_mid, 1),
                '% Nicho/Cauda (<50k seg)': round(pct_tail, 1)
            })
            
        except FileNotFoundError:
            print(f"Arquivo não encontrado para {persona}")

    # --- EXIBIÇÃO E SALVAMENTO ---
    df_results = pd.DataFrame(results)
    
    print("\n=== RESULTADOS DE ANÁLISE DE MERCADO ===")
    print(df_results.to_string(index=False))
    
    # Salva
    output_path = os.path.join(project_root, 'reports', 'summaries', 'tabela_mercado_longtail.csv')
    df_results.to_csv(output_path, index=False)
    print(f"\n[Sucesso] Tabela salva em: {output_path}")
    print("Dica: Use estes dados para discutir 'Monopólio Cultural' e 'Invisibilidade Algorítmica'.")

if __name__ == "__main__":
    main()