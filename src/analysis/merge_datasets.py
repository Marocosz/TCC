"""
================================================================================
MÓDULO DE CONSOLIDAÇÃO DE DATASETS (MERGE) — Input ou Output
================================================================================

Objetivo:
    Concatenar os CSVs enriched das 4 personas em um único arquivo consolidado,
    com coluna 'persona' identificando a origem de cada linha. Esse consolidado
    alimenta os scripts cross-persona (build_cross_graphs, build_diversity_metrics,
    build_market_metrics, build_similarity_matrix).

Schema:
    Lê CSVs em data/inputs/ ou data/outputs/ (modo --source) e escreve em
    data/consolidated/ (consolidado_input.csv ou consolidado_output.csv).

Uso:
    python src/analysis/merge_datasets.py --source=input
    python src/analysis/merge_datasets.py --source=output
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _source_config import (
    parse_source, get_paths, csv_path_for, consolidated_path_for, PERSONAS
)


def consolidar(source, project_root):
    paths = get_paths(project_root, source)
    print(f"\n=== MERGE DATASETS — Modo: {paths['label']} ===\n")

    dados_consolidados = []
    headers = []

    for persona in PERSONAS:
        nome_arquivo = csv_path_for(persona, project_root, source, enriched=True)
        print(f"   Lendo {persona:<10} <- {os.path.basename(nome_arquivo)}", end=" ")

        if not os.path.exists(nome_arquivo):
            print("[NAO ENCONTRADO]")
            continue

        try:
            with open(nome_arquivo, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                if not headers:
                    headers = list(reader.fieldnames or [])
                count = 0
                for linha in reader:
                    linha["persona"] = persona
                    dados_consolidados.append(linha)
                    count += 1
            print(f"[OK, {count} linhas]")
        except Exception as e:
            print(f"[ERRO: {e}]")

    if not dados_consolidados:
        print("\n[!] Nenhum dado coletado. Consolidado não será gerado.")
        return

    cabecalhos = ["persona"] + [h for h in headers if h != "persona"]

    arquivo_saida = consolidated_path_for(project_root, source)
    os.makedirs(os.path.dirname(arquivo_saida), exist_ok=True)
    with open(arquivo_saida, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cabecalhos, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(dados_consolidados)

    print(f"\n[OK] {len(dados_consolidados)} linhas -> {arquivo_saida}")


if __name__ == "__main__":
    source = parse_source()
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    consolidar(source, project_root)
