"""
================================================================================
GRAFICOS CRUZADOS ENTRE PERSONAS — Input ou Output
================================================================================

Objetivo:
    Gerar 5 visualizações comparativas das 4 personas lado a lado, a partir
    do CSV consolidado (data/consolidated/consolidado_<source>.csv).

Visualizações:
    1. Listeners por Track (Boxplot, escala log)
    2. Top Tags / Gêneros (Multiplot por persona)
    3. Era Musical (KDE Plot)
    4. Concentração de Artistas (Curva de Lorenz)
    5. Listeners x Playcount (Scatter, log-log)

Fonte (após Spotify Fev/2026):
    Last.fm + MusicBrainz (mesma fonte para input e output → comparação válida).

Uso:
    python src/analysis/build_cross_graphs.py --source=input
    python src/analysis/build_cross_graphs.py --source=output
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _source_config import (
    parse_source, consolidated_path_for, figures_dir_for, PERSONAS
)

PALETA = {"beatriz": "#FF66C4", "daniel": "#00BF63",
          "ricardo": "#FF914D", "sofia":   "#5271FF"}

PERSONA_ORDER = ["beatriz", "daniel", "ricardo", "sofia"]

sns.set_theme(style="ticks", rc={"axes.labelsize": 13, "xtick.labelsize": 11,
                                 "ytick.labelsize": 11, "axes.grid": True})


def get_genre_string(row):
    for col in ("mb_tags", "lastfm_tags", "artist_genres"):
        v = row.get(col)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def main():
    source = parse_source()
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    label = "INPUT" if source == "input" else "OUTPUT"
    print(f"\n=== CROSS GRAPHS ({label}) ===\n")

    consolidated = consolidated_path_for(project_root, source)
    if not os.path.exists(consolidated):
        print(f"[ERRO] Arquivo consolidado não encontrado: {consolidated}")
        print(f"       Rode antes: python src/analysis/merge_datasets.py --source={source}")
        return

    df = pd.read_csv(consolidated)
    df["album_release_year"] = pd.to_datetime(df["album_release_date"], errors="coerce").dt.year
    for col in ["lastfm_listeners", "lastfm_playcount",
                "lastfm_track_listeners", "lastfm_track_playcount"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0)

    output_dir = figures_dir_for(project_root, source)
    os.makedirs(output_dir, exist_ok=True)

    # GRAFICO 1: Boxplot Listeners por Track (escala log)
    print("   1. Boxplot Listeners por Track")
    plt.figure(figsize=(12, 7))
    df_g1 = df[df["lastfm_track_listeners"] > 0].copy()
    sns.boxplot(data=df_g1, x="persona", y="lastfm_track_listeners",
                order=PERSONA_ORDER, palette=PALETA)
    plt.yscale("log")
    plt.title(f"Distribuição de Listeners por Track ({label})", fontsize=15)
    plt.xlabel("Persona")
    plt.ylabel("Last.fm Listeners (log)")
    plt.savefig(os.path.join(output_dir, "grafico_track_listeners.png"), bbox_inches="tight")
    plt.close()

    # GRAFICO 2: Top Tags por Persona (multiplot 2x2)
    print("   2. Top Tags por Persona")
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    for ax, persona in zip(axes.flat, PERSONA_ORDER):
        sub = df[df["persona"] == persona]
        tags = []
        for _, row in sub.iterrows():
            s = get_genre_string(row)
            if s:
                tags.extend([t.strip().lower() for t in s.split(";") if t.strip()])
        top = Counter(tags).most_common(8)
        if top:
            d = pd.DataFrame(top, columns=["tag", "count"])
            sns.barplot(data=d, x="count", y="tag", orient="h",
                        color=PALETA[persona], ax=ax)
        ax.set_title(persona.capitalize(), fontsize=14)
        ax.set_xlabel("Frequência")
        ax.set_ylabel("")
    fig.suptitle(f"Top 8 Tags por Persona ({label})", fontsize=17)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "grafico_generos.png"), bbox_inches="tight")
    plt.close()

    # GRAFICO 3: KDE Era Musical
    print("   3. KDE Era Musical")
    plt.figure(figsize=(13, 7))
    sns.kdeplot(data=df.dropna(subset=["album_release_year"]),
                x="album_release_year", hue="persona",
                hue_order=PERSONA_ORDER, palette=PALETA, fill=True, alpha=0.35,
                common_norm=False, linewidth=2)
    plt.title(f"Distribuição Temporal das Faixas ({label})", fontsize=15)
    plt.xlabel("Ano")
    plt.ylabel("Densidade")
    plt.savefig(os.path.join(output_dir, "grafico_era_musical.png"), bbox_inches="tight")
    plt.close()

    # GRAFICO 4: Curva de Lorenz (Concentração de Artistas)
    print("   4. Curva de Lorenz")
    plt.figure(figsize=(10, 8))
    plt.plot([0, 1], [0, 1], color="black", linestyle=":", label="Igualdade Perfeita")
    for persona in PERSONA_ORDER:
        sub = df[df["persona"] == persona]
        counts = sub["primary_artist_name"].value_counts().sort_values().values
        if len(counts) == 0:
            continue
        cumulative = np.cumsum(counts) / counts.sum()
        x = np.linspace(0, 1, len(cumulative))
        plt.plot(x, cumulative, label=persona.capitalize(),
                 color=PALETA[persona], linewidth=2.5)
    plt.title(f"Curva de Lorenz — Concentração de Artistas ({label})", fontsize=14)
    plt.xlabel("Fração dos Artistas")
    plt.ylabel("Fração Acumulada das Faixas")
    plt.legend()
    plt.savefig(os.path.join(output_dir, "grafico_concentracao_artistas.png"), bbox_inches="tight")
    plt.close()

    # GRAFICO 5: Scatter Listeners x Playcount (log-log)
    print("   5. Scatter Listeners x Playcount")
    df_g5 = df.drop_duplicates(subset=["primary_artist_name", "persona"]).copy()
    df_g5 = df_g5[(df_g5["lastfm_listeners"] > 0) & (df_g5["lastfm_playcount"] > 0)]
    plt.figure(figsize=(12, 8))
    sns.scatterplot(data=df_g5, x="lastfm_listeners", y="lastfm_playcount",
                    hue="persona", hue_order=PERSONA_ORDER, palette=PALETA,
                    s=60, alpha=0.65)
    plt.xscale("log")
    plt.yscale("log")
    plt.title(f"Listeners x Playcount por Artista ({label})", fontsize=15)
    plt.xlabel("Last.fm Listeners (log)")
    plt.ylabel("Last.fm Playcount (log)")
    plt.savefig(os.path.join(output_dir, "grafico_pop_vs_followers.png"), bbox_inches="tight")
    plt.close()

    print(f"\n[OK] 5 gráficos salvos em {output_dir}")


if __name__ == "__main__":
    main()
