"""
================================================================================
MÓDULO DE CÁLCULO DE DIVERSIDADE E ENTROPIA (MATH METRICS)
================================================================================

Objetivo:
    Calcular índices matemáticos robustos para medir a diversidade de informação
    dentro de cada playlist. Transforma "sensações" (ex: "é variado") em 
    números exatos (ex: "Entropia 4.5").

Métricas:
    1. Entropia de Shannon: Mede a incerteza/variedade da playlist.
    2. Coeficiente de Gini: Mede a desigualdade/concentração de artistas.
    3. Riqueza (Richness): Contagem simples de itens únicos.

Uso:
    python src/analysis/build_diversity_metrics.py
"""

import pandas as pd
import numpy as np
import os
import sys

def shannon_entropy(series):
    """Calcula a Entropia de Shannon (H = -sum(p * log(p)))."""
    # Frequência relativa de cada item (probabilidade p)
    counts = series.value_counts()
    total = len(series)
    probs = counts / total
    
    # Cálculo da entropia
    entropy = -np.sum(probs * np.log2(probs))
    return entropy

def gini_coefficient(series):
    """Calcula o Coeficiente de Gini (0 = igualdade total, 1 = desigualdade max)."""
    counts = series.value_counts().values
    if len(counts) == 0: return 0
    
    # O Gini requer dados ordenados
    sorted_counts = np.sort(counts)
    n = len(counts)
    index = np.arange(1, n + 1)
    
    return ((2 * index - n - 1) * sorted_counts).sum() / (n * sorted_counts.sum())

def main():
    print("--- Calculando Métricas Matemáticas de Diversidade ---")
    
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
            
            # --- CÁLCULOS SOBRE ARTISTAS ---
            # Quão concentrada é a playlist em termos de artistas?
            col_artista = df['primary_artist_name']
            
            entropia = shannon_entropy(col_artista)
            gini = gini_coefficient(col_artista)
            riqueza = col_artista.nunique()
            
            results.append({
                'Persona': persona.capitalize(),
                'Entropia (Shannon)': round(entropia, 4),
                'Desigualdade (Gini)': round(gini, 4),
                'Riqueza (Artistas Únicos)': riqueza,
                'Total Músicas': len(df)
            })
            
        except FileNotFoundError:
            print(f"Arquivo não encontrado para {persona}")

    # --- EXIBIÇÃO E SALVAMENTO ---
    df_results = pd.DataFrame(results)
    
    print("\n=== RESULTADOS FINAIS (MATRIZ DE DIVERSIDADE) ===")
    print(df_results.to_string(index=False))
    
    # Salva em CSV para usar no TCC
    output_path = os.path.join(project_root, 'reports', 'summaries', 'tabela_diversidade_matematica.csv')
    df_results.to_csv(output_path, index=False)
    print(f"\n[Sucesso] Tabela salva em: {output_path}")

if __name__ == "__main__":
    main()