"""
================================================================================
ORQUESTRADOR DA FASE 4 + COMPARACOES — pipeline completo num comando
================================================================================

Roda TODOS os scripts de análise em ordem correta, modo input + output, e os
2 scripts comparativos (Overlap + Delta).

Pré-condições:
    - data/inputs/dataset_<Persona>_input_enriched.csv existem (4 personas)
    - data/outputs/dataset_<Persona>_output_enriched.csv existem (4 personas)

Saídas:
    - data/consolidated/consolidado_input.csv + consolidado_output.csv
    - reports/inputs/ e reports/outputs/ com summaries + figures
    - reports/comparison/overlap_interno.csv + delta_metrics.csv

Uso:
    python src/analysis/run_full_pipeline.py
"""

import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run(cmd_args, label):
    print(f"\n{'#' * 72}")
    print(f"# {label}")
    print(f"# CMD: {' '.join(cmd_args)}")
    print('#' * 72)
    result = subprocess.run(
        [sys.executable] + cmd_args,
        cwd=SCRIPT_DIR,
        capture_output=False,
    )
    if result.returncode != 0:
        print(f"[!] Comando falhou (rc={result.returncode}). Continuando mesmo assim.")


def main():
    steps = [
        # 1. Consolidação
        (["merge_datasets.py", "--source=input"],   "1.1 Merge datasets INPUT"),
        (["merge_datasets.py", "--source=output"],  "1.2 Merge datasets OUTPUT"),

        # 2. Resumos textuais
        (["build_summaries.py", "todas", "--source=input"],   "2.1 Summaries INPUT"),
        (["build_summaries.py", "todas", "--source=output"],  "2.2 Summaries OUTPUT"),

        # 3. Gráficos por persona
        (["build_personal_graphs.py", "todas", "--source=input"],   "3.1 Personal graphs INPUT"),
        (["build_personal_graphs.py", "todas", "--source=output"],  "3.2 Personal graphs OUTPUT"),

        # 4. Gráficos cross-persona
        (["build_cross_graphs.py", "--source=input"],   "4.1 Cross graphs INPUT"),
        (["build_cross_graphs.py", "--source=output"],  "4.2 Cross graphs OUTPUT"),

        # 5. Métricas matemáticas
        (["build_diversity_metrics.py", "--source=input"],   "5.1 Diversity INPUT"),
        (["build_diversity_metrics.py", "--source=output"],  "5.2 Diversity OUTPUT"),
        (["build_market_metrics.py", "--source=input"],      "5.3 Market INPUT"),
        (["build_market_metrics.py", "--source=output"],     "5.4 Market OUTPUT"),
        (["build_similarity_matrix.py", "--source=input"],   "5.5 Jaccard INPUT (ortogonalidade)"),
        (["build_similarity_matrix.py", "--source=output"],  "5.6 Jaccard OUTPUT (Colapso de Contexto)"),

        # 6. Análises comparativas
        (["build_overlap_metrics.py"],  "6.1 Overlap interno dos Daily Mixes"),
        (["build_delta_metrics.py"],    "6.2 Delta Algoritmico (Input -> Output)"),
    ]

    print(f"\n{'=' * 72}")
    print(" FASE 4 + COMPARACOES — pipeline completo")
    print(f" {len(steps)} etapas")
    print('=' * 72)

    for cmd, label in steps:
        run(cmd, label)

    print(f"\n{'=' * 72}")
    print(" PIPELINE COMPLETO! Resultados em:")
    print('=' * 72)
    print("   - reports/inputs/summaries/ + figures/")
    print("   - reports/outputs/summaries/ + figures/")
    print("   - reports/comparison/")


if __name__ == "__main__":
    main()
