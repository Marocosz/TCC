"""
================================================================================
MATRIZ DE SIMILARIDADE — Indice de Jaccard entre Personas (Input ou Output)
================================================================================

Objetivo:
    Calcular o overlap (Jaccard) entre os conjuntos de artistas de cada persona.
    Em modo input, prova a ortogonalidade dos perfis iniciais (cold start).
    Em modo output, mede o "Colapso de Contexto" — convergência forçada pelo
    algoritmo entre personas distintas.

Fonte:
    Usa apenas primary_artist_name (sobreviveu à mudança de Fev/2026).

Uso:
    python src/analysis/build_similarity_matrix.py --source=input
    python src/analysis/build_similarity_matrix.py --source=output
"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _source_config import parse_source, csv_path_for, figures_dir_for, PERSONAS


def calcular_jaccard(set_a, set_b):
    if not (set_a or set_b):
        return 0
    return len(set_a & set_b) / len(set_a | set_b)


def main():
    source = parse_source()
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    label = "INPUT" if source == "input" else "OUTPUT"

    print(f"\n=== JACCARD ({label}) ===\n")

    sets_artistas = {}
    for persona in PERSONAS:
        path = csv_path_for(persona, project_root, source, enriched=True)
        if not os.path.exists(path):
            print(f"[!] {persona}: CSV não encontrado.")
            return
        df = pd.read_csv(path)
        sets_artistas[persona.capitalize()] = set(df["primary_artist_name"].dropna().unique())
        print(f"   {persona}: {len(sets_artistas[persona.capitalize()])} artistas únicos")

    personas_cap = [p.capitalize() for p in PERSONAS]
    matrix_data = [[calcular_jaccard(sets_artistas[a], sets_artistas[b])
                    for b in personas_cap] for a in personas_cap]
    df_matrix = pd.DataFrame(matrix_data, index=personas_cap, columns=personas_cap)

    print(f"\n--- Matriz Jaccard ({label}) ---")
    print(df_matrix.round(3).to_string())

    output_dir = figures_dir_for(project_root, source)
    os.makedirs(output_dir, exist_ok=True)

    plt.figure(figsize=(10, 8))
    title = f"Sobreposição entre Personas — {label} (Indice de Jaccard)"
    sns.heatmap(df_matrix, annot=True, cmap="YlGnBu", vmin=0, vmax=1, fmt=".3f")
    plt.title(title, fontsize=14)

    save_path = os.path.join(output_dir, "matriz_similaridade_jaccard.png")
    plt.savefig(save_path, bbox_inches="tight", dpi=150)
    plt.close()
    print(f"\n[OK] Heatmap salvo em: {save_path}")


if __name__ == "__main__":
    main()
