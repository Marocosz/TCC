"""
================================================================================
MÓDULO DE GERAÇÃO DE RESUMOS ESTATÍSTICOS TEXTUAIS — Input ou Output
================================================================================

Objetivo:
    Produzir relatórios em texto simples (.txt) com estatísticas descritivas
    para cada persona. Funciona tanto sobre os inputs (playlists-semente)
    quanto sobre os outputs (Daily Mix mirrors), via flag --source.

Fonte de dados (após Spotify Fev/2026):
    - Listeners e plays do artista: Last.fm artist.getInfo (proxy de followers/popularidade)
    - Listeners e plays da track:    Last.fm track.getInfo  (proxy de track_popularity)
    - Gêneros:                       MusicBrainz tags (com fallback Last.fm tags)

Métricas geradas:
    - Volume (faixas, artistas únicos, ratio)
    - Alcance: mediana e média de Last.fm listeners (artista)
    - Popularidade Histórica: mediana e média de Last.fm playcount (artista)
    - Listeners por track: agregação de lastfm_track_listeners
    - Janela temporal: ano médio, ranges, top décadas
    - Estrutura: duração média e variação
    - Top gêneros (mb_tags || lastfm_tags)
    - Top artistas (concentração)

Uso:
    python src/analysis/build_summaries.py beatriz --source=input
    python src/analysis/build_summaries.py todas --source=output
    python src/analysis/build_summaries.py todas
"""

import pandas as pd
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _source_config import (
    parse_source, csv_path_for, summaries_dir_for, PERSONAS, safe_int
)


def formatar_duracao(segundos):
    if pd.isna(segundos):
        return "N/A"
    minutos = int(segundos // 60)
    return f"{minutos}:{int(segundos % 60):02}"


def formatar_int(v):
    try:
        return f"{int(float(v)):,}"
    except (TypeError, ValueError):
        return "N/A"


def gerar_resumo(persona, csv_path, output_folder, source_label):
    print(f"\n{'='*20} {persona.upper()} ({source_label}) {'='*20}")
    print(f"   Lendo:  {csv_path}")

    if not os.path.exists(csv_path):
        print(f"   [ERRO] Arquivo não encontrado.")
        return

    output_path = os.path.join(output_folder, f"summarie_{persona.capitalize()}.txt")
    os.makedirs(output_folder, exist_ok=True)

    df = pd.read_csv(csv_path)

    # Casting de tipos
    df["album_release_year"] = pd.to_datetime(df["album_release_date"], errors="coerce").dt.year
    df["lastfm_listeners"] = pd.to_numeric(df.get("lastfm_listeners"), errors="coerce")
    df["lastfm_playcount"] = pd.to_numeric(df.get("lastfm_playcount"), errors="coerce")
    df["lastfm_track_listeners"] = pd.to_numeric(df.get("lastfm_track_listeners"), errors="coerce")
    df["lastfm_track_playcount"] = pd.to_numeric(df.get("lastfm_track_playcount"), errors="coerce")

    # Volume
    total_musicas = len(df)
    artistas_unicos = df["primary_artist_name"].nunique()
    contagem_artistas = df["primary_artist_name"].value_counts()

    # Alcance (Last.fm artist listeners — proxy de followers)
    listeners_per_artist = df.drop_duplicates(subset=["primary_artist_name"])["lastfm_listeners"]
    listeners_median = listeners_per_artist.median()
    listeners_mean = listeners_per_artist.mean()
    listeners_total = listeners_per_artist.sum()

    # Popularidade Histórica (Last.fm artist playcount)
    playcount_per_artist = df.drop_duplicates(subset=["primary_artist_name"])["lastfm_playcount"]
    playcount_median = playcount_per_artist.median()
    playcount_mean = playcount_per_artist.mean()

    # Track-level
    track_listeners_median = df["lastfm_track_listeners"].median()
    track_listeners_mean = df["lastfm_track_listeners"].mean()
    track_playcount_total = df["lastfm_track_playcount"].sum()

    # Tags / Gêneros (prioriza mb_tags, fallback lastfm_tags, fallback artist_genres)
    def get_tags_str(row):
        for col in ("mb_tags", "lastfm_tags", "artist_genres"):
            v = row.get(col, "")
            if isinstance(v, str) and v.strip():
                return v
        return ""

    df["_genres_resolved"] = df.apply(get_tags_str, axis=1)
    lista_de_tags = []
    for s in df["_genres_resolved"].dropna().astype(str):
        lista_de_tags.extend([t.strip().lower() for t in s.split(";") if t.strip()])
    todos_os_tags = Counter(lista_de_tags).most_common()

    # Tempo
    ano_medio = df["album_release_year"].mean()
    ano_min = df["album_release_year"].min()
    ano_max = df["album_release_year"].max()
    df["decade"] = (df["album_release_year"] // 10) * 10
    top_decadas = df["decade"].value_counts(normalize=True).head(3)

    # Duração
    series_sec = df["duration_readable"].astype(str).apply(
        lambda x: int(x.split(":")[0]) * 60 + int(x.split(":")[1]) if ":" in x else None
    ).dropna()

    # Cobertura de fontes externas
    src_counts = df.get("external_source", pd.Series([])).value_counts()

    # ESCRITA
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"=============== RESUMO ({source_label}): {persona.upper()} ===============\n\n")

        f.write("--- METRICAS GERAIS ---\n")
        f.write(f"Total de Faixas: {total_musicas}\n")
        f.write(f"Artistas Únicos: {artistas_unicos}\n")
        f.write(f"Faixas/Artista (média): {(total_musicas/artistas_unicos):.2f}\n\n")

        f.write("--- ALCANCE (Last.fm artist listeners) ---\n")
        f.write(f"Mediana de Listeners por Artista: {formatar_int(listeners_median)}\n")
        f.write(f"Média de Listeners por Artista:   {formatar_int(listeners_mean)}\n")
        f.write(f"Listeners Acumulados (soma):      {formatar_int(listeners_total)}\n\n")

        f.write("--- POPULARIDADE HISTORICA (Last.fm artist playcount) ---\n")
        f.write(f"Mediana de Playcount por Artista: {formatar_int(playcount_median)}\n")
        f.write(f"Média de Playcount por Artista:   {formatar_int(playcount_mean)}\n\n")

        f.write("--- TRACK-LEVEL (Last.fm track) ---\n")
        f.write(f"Mediana de Listeners por Track:   {formatar_int(track_listeners_median)}\n")
        f.write(f"Média de Listeners por Track:     {formatar_int(track_listeners_mean)}\n")
        f.write(f"Plays Acumulados de Tracks:       {formatar_int(track_playcount_total)}\n\n")

        f.write("--- METRICAS TEMPORAIS ---\n")
        f.write(f"Ano Médio: {ano_medio:.0f}\n" if not pd.isna(ano_medio) else "Ano Médio: N/A\n")
        f.write(f"Faixa Etária: {int(ano_min) if not pd.isna(ano_min) else 'N/A'} a "
                f"{int(ano_max) if not pd.isna(ano_max) else 'N/A'}\n")
        f.write("Décadas Dominantes:\n")
        for decada, pct in top_decadas.items():
            f.write(f"  - Anos {int(decada)}s: {pct*100:.1f}%\n")
        f.write("\n")

        f.write("--- ESTRUTURA (Duração) ---\n")
        if not series_sec.empty:
            f.write(f"Duração Média: {formatar_duracao(series_sec.mean())}\n")
            f.write(f"Variação: {formatar_duracao(series_sec.min())} a {formatar_duracao(series_sec.max())}\n\n")
        else:
            f.write("Duração: N/A\n\n")

        f.write("--- COBERTURA DE FONTES EXTERNAS ---\n")
        for src, count in src_counts.items():
            f.write(f"  {src}: {count} faixas ({count/total_musicas*100:.1f}%)\n")
        f.write("\n")

        # --- ERA DE CARREIRA DO ARTISTA (mb_career_start) ---
        # Filtra anos absurdos (matches falsos do MusicBrainz). Música popular
        # gravada a partir do final do séc XIX → corte conservador em 1900.
        career_starts = []
        for v in df.drop_duplicates(subset=["primary_artist_name"]).get("mb_career_start", pd.Series()):
            try:
                y = int(v)
                if 1900 <= y <= 2030:
                    career_starts.append(y)
            except (TypeError, ValueError):
                continue

        if career_starts:
            ser = pd.Series(career_starts)
            f.write("--- ERA DE CARREIRA DO ARTISTA (MusicBrainz life-span) ---\n")
            f.write(f"Cobertura: {len(career_starts)} de {df['primary_artist_name'].nunique()} artistas únicos\n")
            f.write(f"Mediana de inicio de carreira: {int(ser.median())}\n")
            f.write(f"Range: {ser.min()} a {ser.max()}\n")
            decades_career = Counter((s // 10) * 10 for s in career_starts)
            f.write("Décadas dominantes (de início):\n")
            for dec, count in decades_career.most_common(3):
                f.write(f"  - Anos {dec}s: {count} artistas\n")
            f.write("\n")

        # --- TIPO DE ARTISTA (mb_artist_type) ---
        types_series = df.drop_duplicates(subset=["primary_artist_name"]).get("mb_artist_type", pd.Series())
        types = Counter(t for t in types_series if isinstance(t, str) and t.strip())
        if types:
            total_typed = sum(types.values())
            f.write("--- TIPO DE ARTISTA (MusicBrainz) ---\n")
            for tipo, c in types.most_common():
                f.write(f"  {tipo}: {c} ({c/total_typed*100:.1f}%)\n")
            f.write("\n")

        f.write("--- TOP 20 TAGS/GENEROS (mb_tags + lastfm_tags) ---\n")
        for i, (tag, count) in enumerate(todos_os_tags[:20], 1):
            f.write(f"  {i}. {tag} ({count})\n")
        f.write("\n")

        f.write("--- TOP 20 ARTISTAS (volume) ---\n")
        for artista, count in contagem_artistas.head(20).items():
            f.write(f"  - {artista}: {count} faixa(s)\n")

    print(f"   [OK] Resumo salvo em {output_path}")


def main():
    source = parse_source()
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        # Default: todas
        alvo = "todas"
    else:
        alvo = sys.argv[1].lower()

    output_folder = summaries_dir_for(project_root, source)
    label = "INPUT" if source == "input" else "OUTPUT"

    if alvo in ("todas", "all"):
        for persona in PERSONAS:
            csv_path = csv_path_for(persona, project_root, source, enriched=True)
            gerar_resumo(persona, csv_path, output_folder, label)
    elif alvo in PERSONAS:
        csv_path = csv_path_for(alvo, project_root, source, enriched=True)
        gerar_resumo(alvo, csv_path, output_folder, label)
    else:
        print(f"[!] Persona inválida: {alvo}")


if __name__ == "__main__":
    main()
