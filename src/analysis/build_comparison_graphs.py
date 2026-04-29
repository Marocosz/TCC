"""
================================================================================
GRAFICOS COMPARATIVOS — Input vs Output (Delta Algoritmico Visual)
================================================================================

Objetivo:
    Visualizar a transformação que o algoritmo do Spotify aplica sobre o gosto
    declarado de cada persona, comparando lado a lado as métricas dos inputs
    (playlists-semente) e dos outputs (Daily Mixes recomendados).

Visualizações geradas (em reports/comparison/):
    1. heatmap_delta_percentual.png    — todas métricas × personas (matriz de calor)
    2. bar_shannon_in_vs_out.png       — Shannon entropy: Input vs Output
    3. bar_listeners_in_vs_out.png     — Listeners mediano artista: Input vs Output
    4. bar_playcount_in_vs_out.png     — Playcount mediano: Input vs Output
    5. bar_solo_vs_group.png           — % Solo / Group: Input vs Output
    6. kde_era_musical_in_vs_out.png   — Distribuição de release_year (4 subplots)
    7. kde_listeners_in_vs_out.png     — Distribuição de listeners do artista
    8. tags_side_by_side.png           — Top 10 tags comparativas

Pré-requisitos:
    - data/inputs/dataset_<Persona>_input_enriched.csv
    - data/outputs/dataset_<Persona>_output_enriched.csv
    - reports/comparison/delta_metrics_pivot.csv (gerado por build_delta_metrics.py)

Uso:
    python src/analysis/build_comparison_graphs.py
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _source_config import csv_path_for, PERSONAS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "reports", "comparison")

PALETA_PERSONA = {"beatriz": "#FF66C4", "daniel": "#00BF63",
                  "ricardo": "#FF914D", "sofia": "#5271FF"}
COR_INPUT = "#5DADE2"   # azul claro
COR_OUTPUT = "#E74C3C"  # vermelho/laranja

sns.set_theme(style="whitegrid", rc={"axes.labelsize": 13, "xtick.labelsize": 11,
                                     "ytick.labelsize": 11})


def load_data():
    data = {}
    for p in PERSONAS:
        in_path = csv_path_for(p, PROJECT_ROOT, "input", enriched=True)
        out_path = csv_path_for(p, PROJECT_ROOT, "output", enriched=True)
        data[p] = {
            "input": pd.read_csv(in_path),
            "output": pd.read_csv(out_path),
        }
    return data


def get_genre_string(row):
    for col in ("mb_tags", "lastfm_tags", "artist_genres"):
        v = row.get(col)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def graf_1_heatmap_delta(pivot_df):
    """Heatmap geral do delta percentual por métrica × persona."""
    print("  1. Heatmap Delta Percentual")
    df = pivot_df.set_index("Metrica")
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(df, annot=True, fmt=".1f", cmap="RdBu_r", center=0,
                cbar_kws={"label": "Delta % (Output - Input)"}, ax=ax,
                linewidths=0.5)
    ax.set_title("Delta Algoritmico — Variação Percentual de cada métrica\n(Input → Output, por persona)",
                 fontsize=14, pad=14)
    ax.set_xlabel("Persona")
    ax.set_ylabel("Métrica")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "heatmap_delta_percentual.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def graf_2_bar_shannon(data):
    """Bar chart Shannon entropy Input vs Output."""
    print("  2. Bar Shannon Input vs Output")
    rows = []
    for p in PERSONAS:
        for src in ("input", "output"):
            df = data[p][src]
            counts = df["primary_artist_name"].value_counts()
            probs = counts / len(df)
            entropy = float(-np.sum(probs * np.log2(probs)))
            rows.append({"Persona": p.capitalize(), "Source": src.upper(), "Shannon": entropy})
    df_plot = pd.DataFrame(rows)

    plt.figure(figsize=(11, 6))
    sns.barplot(data=df_plot, x="Persona", y="Shannon", hue="Source",
                palette=[COR_INPUT, COR_OUTPUT])
    plt.axhline(6.5, color="gray", linestyle="--", alpha=0.5,
                label="Convergência observada (~6.5)")
    plt.title("Shannon Entropy — Homogeneização Algorítmica", fontsize=14)
    plt.ylabel("Entropia (bits)")
    plt.ylim(0, 7.5)
    for i, p in enumerate(PERSONAS):
        in_v = df_plot[(df_plot.Persona == p.capitalize()) & (df_plot.Source == "INPUT")].Shannon.values[0]
        out_v = df_plot[(df_plot.Persona == p.capitalize()) & (df_plot.Source == "OUTPUT")].Shannon.values[0]
        delta = (out_v - in_v) / in_v * 100
        plt.text(i, max(in_v, out_v) + 0.1, f"{delta:+.1f}%",
                 ha="center", fontsize=10, weight="bold",
                 color="green" if delta >= 0 else "red")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "bar_shannon_in_vs_out.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def graf_3_bar_listeners(data):
    """Bar chart listeners mediano Input vs Output (escala log)."""
    print("  3. Bar Listeners mediano Input vs Output")
    rows = []
    for p in PERSONAS:
        for src in ("input", "output"):
            df = data[p][src]
            df["lastfm_listeners"] = pd.to_numeric(df["lastfm_listeners"], errors="coerce").fillna(0)
            unique = df.drop_duplicates(subset=["primary_artist_name"])
            med = unique["lastfm_listeners"].median()
            rows.append({"Persona": p.capitalize(), "Source": src.upper(), "Listeners": med})
    df_plot = pd.DataFrame(rows)

    plt.figure(figsize=(11, 6))
    sns.barplot(data=df_plot, x="Persona", y="Listeners", hue="Source",
                palette=[COR_INPUT, COR_OUTPUT])
    plt.yscale("log")
    plt.title("Mediana de Listeners por Artista (Last.fm) — Input vs Output", fontsize=14)
    plt.ylabel("Listeners (escala log)")
    for i, p in enumerate(PERSONAS):
        in_v = df_plot[(df_plot.Persona == p.capitalize()) & (df_plot.Source == "INPUT")].Listeners.values[0]
        out_v = df_plot[(df_plot.Persona == p.capitalize()) & (df_plot.Source == "OUTPUT")].Listeners.values[0]
        delta = (out_v - in_v) / in_v * 100 if in_v else 0
        plt.text(i, max(in_v, out_v) * 1.3, f"{delta:+.1f}%",
                 ha="center", fontsize=10, weight="bold",
                 color="green" if delta >= 0 else "red")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "bar_listeners_in_vs_out.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def graf_4_bar_playcount(data):
    """Bar chart playcount mediano Input vs Output."""
    print("  4. Bar Playcount mediano Input vs Output")
    rows = []
    for p in PERSONAS:
        for src in ("input", "output"):
            df = data[p][src]
            df["lastfm_playcount"] = pd.to_numeric(df["lastfm_playcount"], errors="coerce").fillna(0)
            unique = df.drop_duplicates(subset=["primary_artist_name"])
            med = unique["lastfm_playcount"].median()
            rows.append({"Persona": p.capitalize(), "Source": src.upper(), "Playcount": med})
    df_plot = pd.DataFrame(rows)

    plt.figure(figsize=(11, 6))
    sns.barplot(data=df_plot, x="Persona", y="Playcount", hue="Source",
                palette=[COR_INPUT, COR_OUTPUT])
    plt.yscale("log")
    plt.title("Mediana de Playcount por Artista (Last.fm) — Input vs Output", fontsize=14)
    plt.ylabel("Playcount (escala log)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "bar_playcount_in_vs_out.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def graf_5_bar_solo_vs_group(data):
    """Bar chart % solo vs group Input vs Output."""
    print("  5. Bar Solo vs Group Input vs Output")
    rows = []
    for p in PERSONAS:
        for src in ("input", "output"):
            df = data[p][src]
            unique = df.drop_duplicates(subset=["primary_artist_name"])
            types = unique["mb_artist_type"].fillna("").astype(str)
            n = (types != "").sum()
            if n == 0:
                continue
            pct_solo = (types == "Person").sum() / n * 100
            pct_grupo = (types == "Group").sum() / n * 100
            rows.append({"Persona": p.capitalize(), "Source": src.upper(),
                         "Tipo": "Solo (Person)", "Pct": pct_solo})
            rows.append({"Persona": p.capitalize(), "Source": src.upper(),
                         "Tipo": "Grupo (Group)", "Pct": pct_grupo})
    df_plot = pd.DataFrame(rows)

    fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
    for ax, tipo in zip(axes, ["Solo (Person)", "Grupo (Group)"]):
        sub = df_plot[df_plot.Tipo == tipo]
        sns.barplot(data=sub, x="Persona", y="Pct", hue="Source",
                    palette=[COR_INPUT, COR_OUTPUT], ax=ax)
        ax.set_title(f"% Artistas {tipo}", fontsize=13)
        ax.set_ylim(0, 100)
        ax.set_ylabel("% dos artistas únicos")
    plt.suptitle("Estrutura Social do Consumo — Solo vs Grupo (Input vs Output)",
                 fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "bar_solo_vs_group.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def graf_6_kde_era(data):
    """KDE de release_year Input vs Output, 4 subplots por persona."""
    print("  6. KDE Era Musical (release_date) Input vs Output")
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    for ax, p in zip(axes.flat, PERSONAS):
        for src, cor in (("input", COR_INPUT), ("output", COR_OUTPUT)):
            df = data[p][src].copy()
            df["year"] = pd.to_datetime(df["album_release_date"], errors="coerce").dt.year
            sns.kdeplot(df["year"].dropna(), ax=ax, label=src.upper(),
                        color=cor, fill=True, alpha=0.4, linewidth=2)
        ax.set_title(p.capitalize(), fontsize=13)
        ax.set_xlabel("Ano de Lançamento")
        ax.set_ylabel("Densidade")
        ax.legend()
    plt.suptitle("Era Musical (Release Date) — Input vs Output", fontsize=15)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "kde_era_musical_in_vs_out.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def graf_7_kde_listeners(data):
    """KDE de listeners do artista (escala log) Input vs Output."""
    print("  7. KDE Listeners do Artista Input vs Output")
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    for ax, p in zip(axes.flat, PERSONAS):
        for src, cor in (("input", COR_INPUT), ("output", COR_OUTPUT)):
            df = data[p][src].copy()
            df["lastfm_listeners"] = pd.to_numeric(df["lastfm_listeners"], errors="coerce").fillna(0)
            unique = df.drop_duplicates(subset=["primary_artist_name"])
            vals = unique["lastfm_listeners"]
            vals = vals[vals > 0]
            if vals.empty:
                continue
            sns.kdeplot(np.log10(vals), ax=ax, label=src.upper(),
                        color=cor, fill=True, alpha=0.4, linewidth=2)
        ax.set_title(p.capitalize(), fontsize=13)
        ax.set_xlabel("log₁₀(Listeners no Last.fm)")
        ax.set_ylabel("Densidade")
        ax.legend()
    plt.suptitle("Distribuição de Listeners por Artista — Input vs Output (escala log)", fontsize=15)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "kde_listeners_in_vs_out.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def graf_8_tags_side_by_side(data):
    """Top 10 tags Input vs Output, lado a lado, por persona."""
    print("  8. Top 10 Tags Input vs Output")
    fig, axes = plt.subplots(4, 2, figsize=(15, 18))
    for row_idx, p in enumerate(PERSONAS):
        for col_idx, src in enumerate(("input", "output")):
            ax = axes[row_idx, col_idx]
            df = data[p][src]
            tags = []
            for _, r in df.iterrows():
                s = get_genre_string(r)
                if s:
                    tags.extend([t.strip().lower() for t in s.split(";") if t.strip()])
            top = Counter(tags).most_common(10)
            if top:
                d = pd.DataFrame(top, columns=["tag", "count"])
                cor = COR_INPUT if src == "input" else COR_OUTPUT
                sns.barplot(data=d, x="count", y="tag", orient="h", color=cor, ax=ax)
            ax.set_title(f"{p.capitalize()} — {src.upper()}", fontsize=12)
            ax.set_xlabel("Frequência")
            ax.set_ylabel("")
    plt.suptitle("Top 10 Tags por Persona — Input vs Output", fontsize=15)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "tags_side_by_side.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def main():
    print(f"\n=== GRÁFICOS COMPARATIVOS Input vs Output ===\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Carregando 8 CSVs enriched...")
    data = load_data()

    pivot_path = os.path.join(OUTPUT_DIR, "delta_metrics_pivot.csv")
    pivot = pd.read_csv(pivot_path)

    graf_1_heatmap_delta(pivot)
    graf_2_bar_shannon(data)
    graf_3_bar_listeners(data)
    graf_4_bar_playcount(data)
    graf_5_bar_solo_vs_group(data)
    graf_6_kde_era(data)
    graf_7_kde_listeners(data)
    graf_8_tags_side_by_side(data)

    print(f"\n[OK] 8 gráficos comparativos salvos em: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
