"""
================================================================================
MÓDULO DE METRICAS DE DIVERSIDADE — Shannon Entropy + Gini Coefficient
================================================================================

Objetivo:
    Calcular indicadores matemáticos de diversidade (Shannon, Gini) e riqueza
    (artistas únicos) sobre as 4 personas, em modo input ou output.

Fonte:
    Estas métricas dependem APENAS do nome do artista (primary_artist_name),
    portanto NÃO foram afetadas pela remoção dos campos do Spotify em Fev/2026.

Uso:
    python src/analysis/build_diversity_metrics.py --source=input
    python src/analysis/build_diversity_metrics.py --source=output
"""

import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _source_config import parse_source, csv_path_for, summaries_dir_for, PERSONAS


def shannon_entropy(series):
    counts = series.value_counts()
    total = len(series)
    if total == 0:
        return 0
    probs = counts / total
    return float(-np.sum(probs * np.log2(probs)))


def gini_coefficient(series):
    counts = series.value_counts().values
    if len(counts) == 0:
        return 0
    sorted_counts = np.sort(counts)
    n = len(counts)
    index = np.arange(1, n + 1)
    return float(((2 * index - n - 1) * sorted_counts).sum() / (n * sorted_counts.sum()))


def main():
    source = parse_source()
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    label = "INPUT" if source == "input" else "OUTPUT"

    print(f"\n=== DIVERSIDADE ({label}) ===\n")

    results = []
    for persona in PERSONAS:
        csv_path = csv_path_for(persona, project_root, source, enriched=True)
        if not os.path.exists(csv_path):
            print(f"[!] {persona}: CSV não encontrado.")
            continue

        df = pd.read_csv(csv_path)
        col = df["primary_artist_name"]

        results.append({
            "Persona": persona.capitalize(),
            "Source": label,
            "Entropia (Shannon)": round(shannon_entropy(col), 4),
            "Desigualdade (Gini)": round(gini_coefficient(col), 4),
            "Riqueza (Artistas Unicos)": col.nunique(),
            "Total Faixas": len(df),
        })

    df_out = pd.DataFrame(results)
    print(df_out.to_string(index=False))

    output_dir = summaries_dir_for(project_root, source)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "tabela_diversidade_matematica.csv")
    df_out.to_csv(output_path, index=False)
    print(f"\n[OK] Tabela salva em: {output_path}")


if __name__ == "__main__":
    main()
