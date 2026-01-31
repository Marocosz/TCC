"""
================================================================================
MÓDULO DE MATRIZ DE SIMILARIDADE (JACCARD INDEX)
================================================================================

Objetivo:
    Verificar matematicamente a sobreposição (overlap) entre as personas.
    Prova que os perfis iniciais são distintos e isolados (Bolhas separadas).

Métrica:
    Índice de Jaccard: J(A,B) = |A ∩ B| / |A ∪ B|
    Mede a porcentagem de artistas compartilhados entre dois perfis.

Saída Visual:
    Gera um Heatmap (Mapa de Calor) mostrando quem se parece com quem.

Uso:
    python src/analysis/build_similarity_matrix.py
"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os
import itertools

def calcular_jaccard(set_a, set_b):
    """Calcula a similaridade de Jaccard entre dois conjuntos."""
    interseccao = len(set_a.intersection(set_b))
    uniao = len(set_a.union(set_b))
    if uniao == 0: return 0
    return interseccao / uniao

def main():
    print("--- Gerando Matriz de Similaridade (Jaccard) ---")
    
    # Configuração de Caminhos
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    data_dir = os.path.join(project_root, 'data', 'processed')
    output_img_dir = os.path.join(project_root, 'reports', 'figures', 'cross')
    
    personas = ['Beatriz', 'Daniel', 'Ricardo', 'Sofia']
    
    # Dicionário para guardar os conjuntos de artistas de cada um
    sets_artistas = {}
    
    # 1. Carregar Conjuntos
    for persona in personas:
        try:
            path = os.path.join(data_dir, f'dataset_{persona}_playlist.csv')
            df = pd.read_csv(path)
            # Cria um SET (conjunto único) de artistas
            sets_artistas[persona] = set(df['primary_artist_name'].dropna().unique())
            print(f"{persona}: {len(sets_artistas[persona])} artistas únicos carregados.")
        except FileNotFoundError:
            print(f"[Erro] CSV da {persona} não encontrado.")
            return

    # 2. Calcular Matriz Cruzada
    matrix_data = []
    
    for p1 in personas:
        row = []
        for p2 in personas:
            score = calcular_jaccard(sets_artistas[p1], sets_artistas[p2])
            row.append(score)
        matrix_data.append(row)
    
    # 3. Criar DataFrame da Matriz
    df_matrix = pd.DataFrame(matrix_data, index=personas, columns=personas)
    
    # Mostra no terminal
    print("\n--- MATRIZ DE SIMILARIDADE (INPUT) ---")
    print(df_matrix.round(3))
    
    # 4. Gerar Heatmap Visual
    plt.figure(figsize=(10, 8))
    sns.heatmap(df_matrix, annot=True, cmap="YlGnBu", vmin=0, vmax=1, fmt=".3f")
    plt.title("Grau de Sobreposição entre Personas (Índice de Jaccard)", fontsize=14)
    
    save_path = os.path.join(output_img_dir, 'matriz_similaridade_jaccard.png')
    plt.savefig(save_path)
    print(f"\n[Visual] Heatmap salvo em: {save_path}")

if __name__ == "__main__":
    main()