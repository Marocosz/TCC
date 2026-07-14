"""
================================================================================
GERACAO DE INSIGHTS GRAFICOS POR PERSONA — Input ou Output
================================================================================

Objetivo:
    Gerar 6 insights gráficos individuais para cada persona, em modo input
    ou output. Os insights cobrem alcance, gênero, época, concentração,
    perfil de fama e duração.

Insights gerados:
    1. Distribuição de Listeners por Track (Last.fm) — substitui track_popularity
    2. Top 10 Gêneros (mb_tags + fallback lastfm_tags + fallback artist_genres)
    3. Era Musical (Histograma de release_year)
    4. Concentração de Artistas (Top 15 por volume)
    5. Quadrante de Fama: Listeners x Playcount do artista (escala log)
    6. Duração das Faixas (Histograma)
    + Grid Final 3x2 com os 6 insights consolidados

Fonte de dados (após Spotify Fev/2026):
    - Listeners/playcount/tags ← Last.fm + MusicBrainz
    - release_date / duration ← Spotify (não foram afetados)

Uso:
    python src/analysis/build_personal_graphs.py beatriz --source=input
    python src/analysis/build_personal_graphs.py todas --source=output
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import seaborn as sns
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _source_config import parse_source, csv_path_for, figures_dir_for, PERSONAS

sns.set_theme(style="ticks", rc={"axes.labelsize": 14, "xtick.labelsize": 11,
                                 "ytick.labelsize": 11, "axes.grid": True})


def get_genre_string(row):
    """Prioridade: mb_tags > lastfm_tags > artist_genres."""
    for col in ("mb_tags", "lastfm_tags", "artist_genres"):
        v = row.get(col)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def calcular_top_tags(df, top_n=10):
    """Top N gêneros agregados de mb_tags+lastfm_tags+artist_genres."""
    tags = []
    for _, row in df.iterrows():
        s = get_genre_string(row)
        if s:
            tags.extend([t.strip().lower() for t in s.split(";") if t.strip()])
    return Counter(tags).most_common(top_n)


def gerar_graficos(persona, csv_path, output_folder, source_label):
    print(f"\n{'='*20} {persona.upper()} ({source_label}) {'='*20}")
    print(f"   Lendo: {csv_path}")

    if not os.path.exists(csv_path):
        print(f"   [ERRO] Arquivo não encontrado.")
        return

    os.makedirs(output_folder, exist_ok=True)
    df = pd.read_csv(csv_path)

    df["album_release_year"] = pd.to_datetime(df["album_release_date"], errors="coerce").dt.year
    for col in ["lastfm_listeners", "lastfm_playcount",
                "lastfm_track_listeners", "lastfm_track_playcount"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0)

    persona_title = persona.capitalize()

    # GRAFICO 1: Listeners por Track (escala log)
    # A mediana ANOTADA usa a serie completa (idem build_summaries.py e as
    # tabelas do texto): faixas sem correspondencia no Last.fm entram como 0 e
    # NAO sao descartadas do calculo. Apenas o histograma em escala log precisa
    # do subconjunto > 0, ja que log(0) e indefinido. Manter as duas coisas
    # separadas evita que a legenda da figura divirja da Tabela por Persona.
    print("   1. Listeners por Track (Last.fm)")
    plt.figure(figsize=(10, 6))
    track_median = df["lastfm_track_listeners"].median()
    track_positive = df["lastfm_track_listeners"].replace(0, pd.NA).dropna()
    if not track_positive.empty:
        sns.histplot(track_positive, kde=True, bins=25, color="teal", log_scale=True)
        plt.axvline(track_median, color="red", linestyle="--",
                    label=f"Mediana: {track_median:,.0f}")
        plt.legend()
    plt.title(f"Insight 1: Listeners por Track no Last.fm ({persona_title})", fontsize=15)
    plt.xlabel("Listeners (escala log)")
    plt.ylabel("Faixas")
    plt.savefig(os.path.join(output_folder, "insight_1_track_listeners.png"), bbox_inches="tight")
    plt.close()

    # GRAFICO 2: Top Tags
    print("   2. Top 10 Tags / Gêneros")
    top_tags = calcular_top_tags(df, top_n=10)
    if top_tags:
        df_t = pd.DataFrame(top_tags, columns=["tag", "count"])
        plt.figure(figsize=(12, 8))
        sns.barplot(data=df_t, x="count", y="tag", orient="h", palette="mako")
        plt.title(f"Insight 2: Top 10 Tags/Gêneros ({persona_title})", fontsize=15)
        plt.xlabel("Frequência")
        plt.ylabel("Tag")
        plt.tight_layout()
        plt.savefig(os.path.join(output_folder, "insight_2_generos.png"), bbox_inches="tight")
        plt.close()

    # GRAFICO 3: Era Musical
    print("   3. Era Musical")
    plt.figure(figsize=(10, 6))
    df_clean = df.dropna(subset=["album_release_year"])
    if not df_clean.empty:
        sns.histplot(df_clean["album_release_year"], kde=True, bins=25, color="indigo")
    plt.title(f"Insight 3: Era Musical ({persona_title})", fontsize=15)
    plt.xlabel("Ano de Lançamento")
    plt.ylabel("Faixas")
    plt.savefig(os.path.join(output_folder, "insight_3_era_musical.png"), bbox_inches="tight")
    plt.close()

    # GRAFICO 4: Concentração de Artistas
    print("   4. Top 15 Artistas")
    top_a = df["primary_artist_name"].value_counts().nlargest(15)
    plt.figure(figsize=(12, 8))
    sns.barplot(x=top_a.values, y=top_a.index, orient="h", palette="magma")
    plt.title(f"Insight 4: Top 15 Artistas ({persona_title})", fontsize=15)
    plt.xlabel("Faixas na Playlist")
    plt.ylabel("Artista")
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, "insight_4_concentracao_artistas.png"), bbox_inches="tight")
    plt.close()

    # GRAFICO 5: Quadrante de Fama (Listeners × Playcount)
    # As medianas ANOTADAS nos eixos usam TODOS os artistas unicos (idem
    # build_summaries.py e as tabelas), inclusive os sem dado no Last.fm (0).
    # O scatter em escala log, por outro lado, so consegue plotar os pontos > 0.
    print("   5. Quadrante de Fama (Listeners × Playcount)")
    df_unique = df.drop_duplicates(subset=["primary_artist_name"]).copy()
    median_l = df_unique["lastfm_listeners"].median()
    median_p = df_unique["lastfm_playcount"].median()
    df_artists = df_unique[(df_unique["lastfm_listeners"] > 0) &
                           (df_unique["lastfm_playcount"] > 0)]
    plt.figure(figsize=(12, 8))
    if not df_artists.empty:
        g = sns.scatterplot(data=df_artists, x="lastfm_listeners", y="lastfm_playcount",
                             s=80, alpha=0.7, color="crimson")
        g.set_xscale("log")
        g.set_yscale("log")
        plt.axvline(median_l, color="gray", linestyle="--", alpha=0.5)
        plt.axhline(median_p, color="gray", linestyle="--", alpha=0.5)
        plt.title(f"Insight 5: Quadrante de Fama — Listeners x Plays ({persona_title})", fontsize=14)
        plt.xlabel(f"Last.fm Listeners (mediana: {median_l:,.0f})")
        plt.ylabel(f"Last.fm Playcount (mediana: {median_p:,.0f})")
        plt.grid(True, which="both", ls="--", alpha=0.3)
    plt.savefig(os.path.join(output_folder, "insight_5_pop_vs_followers.png"), bbox_inches="tight")
    plt.close()

    # GRAFICO 6: Duração
    print("   6. Duração das Faixas")
    if "duration_readable" in df.columns:
        df["duration_seconds"] = df["duration_readable"].astype(str).apply(
            lambda x: int(x.split(":")[0])*60 + int(x.split(":")[1]) if ":" in x else None
        )
        plt.figure(figsize=(10, 6))
        clean = df.dropna(subset=["duration_seconds"])
        if not clean.empty:
            sns.histplot(clean["duration_seconds"], kde=True, bins=20, color="purple")
            mean_v = clean["duration_seconds"].mean()
            plt.axvline(mean_v, color="red", linestyle="--",
                        label=f"Média: {int(mean_v//60)}:{int(mean_v%60):02d}")
            plt.legend()
        plt.title(f"Insight 6: Duração das Faixas ({persona_title})", fontsize=15)
        plt.xlabel("Segundos")
        plt.ylabel("Faixas")
        plt.tight_layout()
        plt.savefig(os.path.join(output_folder, "insight_6_music_duration.png"), bbox_inches="tight")
        plt.close()

    # GRID FINAL 3x2
    print("   Grid consolidado")
    graficos = [
        ("insight_1_track_listeners.png",       "Insight 1: Track Listeners"),
        ("insight_2_generos.png",               "Insight 2: Top Tags"),
        ("insight_3_era_musical.png",           "Insight 3: Era Musical"),
        ("insight_4_concentracao_artistas.png", "Insight 4: Top Artistas"),
        ("insight_5_pop_vs_followers.png",      "Insight 5: Quadrante Fama"),
        ("insight_6_music_duration.png",        "Insight 6: Duração"),
    ]

    fig_grid = plt.figure(figsize=(20, 24), constrained_layout=True)
    fig_grid.suptitle(f"Perfil Analítico — {persona_title} ({source_label})",
                      fontsize=32, weight="bold", y=1.02)
    gs = fig_grid.add_gridspec(3, 2)
    for idx, (filename, _) in enumerate(graficos):
        filepath = os.path.join(output_folder, filename)
        ax = fig_grid.add_subplot(gs[idx // 2, idx % 2])
        if os.path.exists(filepath):
            ax.imshow(mpimg.imread(filepath))
        else:
            ax.text(0.5, 0.5, f"Faltando:\n{filename}", ha="center", va="center",
                    fontsize=14, color="red")
        ax.axis("off")

    grid_path = os.path.join(output_folder, "final_summary_grid.png")
    plt.savefig(grid_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"   [OK] Salvos em {output_folder}")


def main():
    source = parse_source()
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    label = "INPUT" if source == "input" else "OUTPUT"

    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        alvo = "todas"
    else:
        alvo = sys.argv[1].lower()

    if alvo in ("todas", "all"):
        for persona in PERSONAS:
            csv_path = csv_path_for(persona, project_root, source, enriched=True)
            output_folder = figures_dir_for(project_root, source, persona=persona)
            gerar_graficos(persona, csv_path, output_folder, label)
    elif alvo in PERSONAS:
        csv_path = csv_path_for(alvo, project_root, source, enriched=True)
        output_folder = figures_dir_for(project_root, source, persona=alvo)
        gerar_graficos(alvo, csv_path, output_folder, label)
    else:
        print(f"[!] Persona inválida: {alvo}")


if __name__ == "__main__":
    main()
