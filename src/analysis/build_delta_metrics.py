"""
================================================================================
DELTA ALGORITMICO — Comparação Input vs Output (4 personas)
================================================================================

Objetivo:
    Calcular a diferença (delta) entre métricas dos inputs (playlists-semente)
    e dos outputs (Daily Mixes recomendados pelo Spotify), por persona.

    Isso é o coração quantitativo do Capítulo 4 do TCC: mostra a "interferência
    do algoritmo" sobre o gosto declarado de cada persona.

Métricas comparadas (apples-to-apples — mesma fonte Last.fm/MusicBrainz):
    - Shannon Entropy (artistas)
    - Gini Coefficient (artistas)
    - HHI sobre tags
    - Listeners medianos por artista (Last.fm)
    - Playcount mediano por artista (Last.fm)
    - Listeners medianos por track (Last.fm)
    - Ano médio de lançamento
    - Duração média (segundos)
    - % Superstars / % Médios / % Cauda Longa (calibrado por percentil unificado)

Saída:
    reports/comparison/delta_metrics.csv com colunas:
        Persona | Métrica | Input | Output | Delta_Absoluto | Delta_Percentual

Uso:
    python src/analysis/build_delta_metrics.py
"""

import os
import sys
import numpy as np
import pandas as pd
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _source_config import csv_path_for, PERSONAS


def shannon(series):
    counts = series.value_counts()
    if len(counts) == 0:
        return 0
    probs = counts / len(series)
    return float(-np.sum(probs * np.log2(probs)))


def gini(series):
    counts = series.value_counts().values
    if len(counts) == 0:
        return 0
    sorted_counts = np.sort(counts)
    n = len(counts)
    idx = np.arange(1, n + 1)
    return float(((2 * idx - n - 1) * sorted_counts).sum() / (n * sorted_counts.sum()))


def hhi(series):
    if len(series) == 0:
        return 0
    counts = series.value_counts()
    total = counts.sum()
    if total == 0:
        return 0
    shares = counts / total
    return float((shares ** 2).sum())


def explode_tags(s):
    if not isinstance(s, str):
        return []
    return [t.strip().lower() for t in s.split(";") if t.strip()]


def get_genre_string(row):
    for col in ("mb_tags", "lastfm_tags", "artist_genres"):
        v = row.get(col)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def duration_seconds(s):
    if not isinstance(s, str) or ":" not in s:
        return None
    try:
        m, sec = s.split(":")
        return int(m) * 60 + int(sec)
    except ValueError:
        return None


def compute_metrics(df):
    """Computa o vetor de métricas para um DataFrame de uma persona."""
    df = df.copy()
    df["lastfm_listeners"] = pd.to_numeric(df.get("lastfm_listeners"), errors="coerce").fillna(0)
    df["lastfm_playcount"] = pd.to_numeric(df.get("lastfm_playcount"), errors="coerce").fillna(0)
    df["lastfm_track_listeners"] = pd.to_numeric(df.get("lastfm_track_listeners"), errors="coerce").fillna(0)
    df["release_year"] = pd.to_datetime(df.get("album_release_date"), errors="coerce").dt.year
    df["duration_sec"] = df["duration_readable"].apply(duration_seconds)

    artists_df = df.drop_duplicates(subset=["primary_artist_name"])

    # tags
    all_tags = []
    for _, row in df.iterrows():
        all_tags.extend(explode_tags(get_genre_string(row)))

    # Era de carreira (mediana, robusta a outliers de match falso do MB)
    career_starts = []
    for v in artists_df.get("mb_career_start", pd.Series()):
        try:
            y = int(v)
            if 1900 <= y <= 2030:
                career_starts.append(y)
        except (TypeError, ValueError):
            continue
    career_med = float(np.median(career_starts)) if career_starts else float("nan")

    # Tipo de artista — % Group
    types = artists_df.get("mb_artist_type", pd.Series()).fillna("").astype(str)
    n_typed = (types != "").sum()
    pct_group = (types == "Group").sum() / n_typed * 100 if n_typed else float("nan")
    pct_person = (types == "Person").sum() / n_typed * 100 if n_typed else float("nan")

    return {
        "shannon_artistas":         shannon(df["primary_artist_name"]),
        "gini_artistas":            gini(df["primary_artist_name"]),
        "hhi_tags":                 hhi(pd.Series(all_tags)),
        "listeners_med_artista":    artists_df["lastfm_listeners"].median(),
        "playcount_med_artista":    artists_df["lastfm_playcount"].median(),
        "listeners_med_track":      df["lastfm_track_listeners"].median(),
        "ano_medio_release":        df["release_year"].mean(),
        "ano_medio_carreira":       career_med,
        "pct_artistas_grupo":       pct_group,
        "pct_artistas_solo":        pct_person,
        "duracao_media_seg":        df["duration_sec"].mean(),
        "n_faixas":                 len(df),
        "n_artistas_unicos":        artists_df["primary_artist_name"].nunique(),
    }


def percent_change(input_v, output_v):
    """Variação percentual com tratamento para divisão por zero."""
    if input_v is None or pd.isna(input_v) or input_v == 0:
        return None
    return (output_v - input_v) / abs(input_v) * 100


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print("\n=== DELTA ALGORITMICO (Input → Output) ===\n")

    rows = []
    summary_lines = []
    for persona in PERSONAS:
        in_path = csv_path_for(persona, project_root, "input", enriched=True)
        out_path = csv_path_for(persona, project_root, "output", enriched=True)
        if not (os.path.exists(in_path) and os.path.exists(out_path)):
            print(f"   [!] {persona}: faltam CSVs ({in_path} ou {out_path})")
            continue

        in_df = pd.read_csv(in_path)
        out_df = pd.read_csv(out_path)

        in_m = compute_metrics(in_df)
        out_m = compute_metrics(out_df)

        print(f"--- {persona.upper()} ---")
        for k in in_m:
            iv = in_m[k]
            ov = out_m[k]
            delta_abs = (ov - iv) if (not pd.isna(iv) and not pd.isna(ov)) else None
            delta_pct = percent_change(iv, ov)
            rows.append({
                "Persona": persona.capitalize(),
                "Metrica": k,
                "Input": round(iv, 4) if not pd.isna(iv) else None,
                "Output": round(ov, 4) if not pd.isna(ov) else None,
                "Delta_Absoluto": round(delta_abs, 4) if delta_abs is not None else None,
                "Delta_Percentual": round(delta_pct, 2) if delta_pct is not None else None,
            })
            iv_s = f"{iv:.3f}" if not pd.isna(iv) else "NA"
            ov_s = f"{ov:.3f}" if not pd.isna(ov) else "NA"
            dpct = f"{delta_pct:+.1f}%" if delta_pct is not None else "  --  "
            print(f"   {k:<24}: {iv_s:>14} -> {ov_s:>14}  ({dpct})")
        print()

    if not rows:
        print("[!] Nenhum delta computado.")
        return

    df_out = pd.DataFrame(rows)
    output_dir = os.path.join(project_root, "reports", "comparison")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "delta_metrics.csv")
    df_out.to_csv(output_path, index=False)

    print(f"\n[OK] Tabela completa salva em: {output_path}")

    # Pivot para visualização rápida (1 métrica por linha, 4 personas em colunas)
    pivot_path = os.path.join(output_dir, "delta_metrics_pivot.csv")
    pivot = df_out.pivot_table(index="Metrica", columns="Persona",
                                values="Delta_Percentual", aggfunc="first")
    pivot.to_csv(pivot_path)
    print(f"[OK] Pivot Delta% salvo em: {pivot_path}")


if __name__ == "__main__":
    main()
