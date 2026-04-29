"""
================================================================================
TAXA DE OVERLAP INTERNO DOS DAILY MIXES (Output)
================================================================================

Objetivo:
    Quantificar quanto o algoritmo do Spotify "insiste nas mesmas faixas" entre
    os 6 Daily Mixes de cada persona.

Lógica:
    Cada persona tem 6 Daily Mixes gerados pelo Spotify, cada um com ~50 faixas.
    Pool bruto: 300 faixas/persona.
    A playlist espelho (cópia manual + dedup) tem N faixas únicas.

    Overlap Interno = (300 - N) / 300

    Interpretação:
        - Alto overlap: clusters do algoritmo são redundantes, persona vive numa
          bolha estreita com poucas faixas em rotação cruzada.
        - Baixo overlap: clusters mais ortogonais, exposição maior a faixas
          distintas dentro do mesmo perfil.

Por que existe:
    Esta métrica captura um aspecto que o Jaccard cruzado entre personas
    NÃO captura — a redundância INTERNA do algoritmo dentro de uma única
    persona, sinal de quão estreita é a bolha temática construída pelo sistema.

Customização:
    Use --raw=N para mudar o pool bruto assumido (default: 300 = 6 mixes × 50).

Uso:
    python src/analysis/build_overlap_metrics.py
    python src/analysis/build_overlap_metrics.py --raw=300
"""

import os
import sys
import csv
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _source_config import csv_path_for, PERSONAS

DEFAULT_RAW_POOL = 300  # 6 Daily Mixes × ~50 faixas


def main():
    raw_pool = DEFAULT_RAW_POOL
    for arg in sys.argv[1:]:
        if arg.startswith("--raw="):
            try:
                raw_pool = int(arg.split("=", 1)[1])
            except ValueError:
                pass

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    print(f"\n=== TAXA DE OVERLAP INTERNO ===")
    print(f"   Pool bruto assumido: {raw_pool} faixas (6 Daily Mixes × ~50)\n")

    results = []
    for persona in PERSONAS:
        path = csv_path_for(persona, project_root, source="output", enriched=True)
        if not os.path.exists(path):
            # tenta sem enriched
            path = csv_path_for(persona, project_root, source="output", enriched=False)
        if not os.path.exists(path):
            print(f"   [!] {persona}: CSV não encontrado.")
            continue

        df = pd.read_csv(path)
        n_unique = len(df)
        duplicatas = max(0, raw_pool - n_unique)
        overlap_rate = duplicatas / raw_pool

        results.append({
            "Persona": persona.capitalize(),
            "Faixas Unicas (N)": n_unique,
            "Pool Bruto Estimado": raw_pool,
            "Duplicatas Removidas": duplicatas,
            "Taxa Overlap Interno (%)": round(overlap_rate * 100, 2),
        })

        print(f"   {persona:<10}: {n_unique:>4} únicas | "
              f"~{duplicatas:>3} duplicatas | "
              f"Overlap = {overlap_rate*100:>5.2f}%")

    if not results:
        print("\n[!] Nenhum dado processado.")
        return

    df_out = pd.DataFrame(results)

    output_dir = os.path.join(project_root, "reports", "comparison")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "overlap_interno.csv")
    df_out.to_csv(output_path, index=False)

    print(f"\n[OK] Tabela salva em: {output_path}")

    # Interpretação automática
    print("\n--- Interpretação ---")
    for r in results:
        rate = r["Taxa Overlap Interno (%)"]
        if rate > 30:
            interp = "ALTA redundância — algoritmo insiste nas mesmas faixas (bolha estreita)"
        elif rate > 15:
            interp = "Moderada — algumas faixas se repetem entre clusters"
        else:
            interp = "BAIXA — clusters mais ortogonais (variedade dentro do perfil)"
        print(f"   {r['Persona']:<10} ({rate:5.1f}%): {interp}")


if __name__ == "__main__":
    main()
