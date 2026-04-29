"""
================================================================================
METRICAS DE MERCADO E CAUDA LONGA (HHI + Long Tail Tiers)
================================================================================

Objetivo:
    Auditar o valor comercial e a distribuição de poder nas playlists.

Métricas:
    1. HHI (Herfindahl-Hirschman) sobre tags/gêneros (mb_tags || lastfm_tags).
    2. Long Tail Tiers via PERCENTIL DENTRO DO CONJUNTO UNIFICADO (4 personas
       da mesma source). Decisão 5.2 do PLANO_REFATORACAO.md:
       - Top 25% Listeners (Last.fm) → Superstars
       - Meio (25%-75%)              → Médios
       - Bottom 25%                  → Cauda Longa

Por que percentis e não thresholds absolutos:
    Os antigos thresholds (1M followers Spotify) não são transferíveis pro
    Last.fm (escala diferente). Percentis dão classificação relativa robusta,
    independente da fonte, e mais defensável academicamente.

Uso:
    python src/analysis/build_market_metrics.py --source=input
    python src/analysis/build_market_metrics.py --source=output
"""

import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _source_config import parse_source, csv_path_for, summaries_dir_for, PERSONAS


def calculate_hhi(series):
    """HHI = soma dos quadrados das participações de mercado."""
    if len(series) == 0:
        return 0
    counts = series.value_counts()
    total = counts.sum()
    if total == 0:
        return 0
    shares = counts / total
    return float((shares ** 2).sum())


def explode_tags(s):
    """'rock; pop; jazz' → ['rock', 'pop', 'jazz']."""
    if not isinstance(s, str):
        return []
    return [t.strip().lower() for t in s.split(";") if t.strip()]


def get_genre_string(row):
    """Prioridade: mb_tags > lastfm_tags > artist_genres."""
    for col in ("mb_tags", "lastfm_tags", "artist_genres"):
        v = row.get(col)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def main():
    source = parse_source()
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    label = "INPUT" if source == "input" else "OUTPUT"

    print(f"\n=== MERCADO + LONG TAIL ({label}) ===\n")

    # ETAPA 1: carregar todos os CSVs e juntar artistas únicos pra calibrar percentis
    all_artists_listeners = []
    persona_data = {}

    for persona in PERSONAS:
        path = csv_path_for(persona, project_root, source, enriched=True)
        if not os.path.exists(path):
            print(f"[!] {persona}: CSV não encontrado, pulando.")
            continue
        df = pd.read_csv(path)
        df["lastfm_listeners"] = pd.to_numeric(df["lastfm_listeners"], errors="coerce").fillna(0)
        unique_artists = df.drop_duplicates(subset=["primary_artist_name"])
        persona_data[persona] = (df, unique_artists)
        all_artists_listeners.extend(unique_artists["lastfm_listeners"].tolist())

    if not all_artists_listeners:
        print("[!] Nenhum dado encontrado.")
        return

    # ETAPA 2: calibrar thresholds por percentil 25 e 75 sobre o pool unificado
    pool = pd.Series(all_artists_listeners)
    p25 = pool.quantile(0.25)
    p75 = pool.quantile(0.75)
    print(f"[i] Thresholds calibrados (percentis sobre {len(pool)} artistas únicos):")
    print(f"    Cauda Longa  : <= {p25:>15,.0f} listeners (P25)")
    print(f"    Médios       :    {p25:>15,.0f} < x <= {p75:,.0f} (P25-P75)")
    print(f"    Superstars   :  > {p75:>15,.0f} listeners (P75)\n")

    def categorize(v):
        if pd.isna(v):
            return "Unknown"
        if v <= p25:
            return "Tail (Long Tail)"
        if v <= p75:
            return "Mid (Medio)"
        return "Head (Superstars)"

    # ETAPA 3: calcular metricas por persona
    results = []
    for persona, (df, unique_artists) in persona_data.items():
        # HHI sobre tags
        all_tags = []
        for _, row in df.iterrows():
            all_tags.extend(explode_tags(get_genre_string(row)))
        hhi = calculate_hhi(pd.Series(all_tags))

        # Long Tail via percentis
        tiers = unique_artists["lastfm_listeners"].apply(categorize)
        tier_pct = tiers.value_counts(normalize=True) * 100

        results.append({
            "Persona": persona.capitalize(),
            "Source": label,
            "HHI Generos": round(hhi, 4),
            "% Superstars (>P75)": round(tier_pct.get("Head (Superstars)", 0), 1),
            "% Medios (P25-P75)": round(tier_pct.get("Mid (Medio)", 0), 1),
            "% Cauda Longa (<=P25)": round(tier_pct.get("Tail (Long Tail)", 0), 1),
        })

    df_results = pd.DataFrame(results)
    print("--- Resultados ---")
    print(df_results.to_string(index=False))

    # Salva
    output_dir = summaries_dir_for(project_root, source)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "tabela_mercado_longtail.csv")

    # Inclui linha com os thresholds calibrados como metadata
    metadata = pd.DataFrame([{
        "Persona": "_THRESHOLDS_",
        "Source": label,
        "HHI Generos": "",
        "% Superstars (>P75)": f"P75={p75:,.0f}",
        "% Medios (P25-P75)": "",
        "% Cauda Longa (<=P25)": f"P25={p25:,.0f}",
    }])
    pd.concat([df_results, metadata], ignore_index=True).to_csv(output_path, index=False)
    print(f"\n[OK] Tabela salva em: {output_path}")


if __name__ == "__main__":
    main()
