"""
================================================================================
HELPER COMPARTILHADO — Comutação Input/Output + Harmonização de Schema
================================================================================

Permite que TODOS os scripts da pipeline operem indistintamente sobre os dados
de Input (playlists-semente das personas) e Output (playlists espelho dos
Daily Mixes), via flag `--source=input|output` na linha de comando.

ESTRUTURA NOVA DE DADOS (pós-refatoração de 2026-04-28):

  data/
    raw/                                    sementes (artistas_*.csv)
    inputs/
      dataset_<Persona>_input.csv           (raw extraído via Spotify)
      dataset_<Persona>_input_enriched.csv  (com Last.fm + MusicBrainz)
    outputs/
      dataset_<Persona>_output.csv          (raw extraído via Spotify)
      dataset_<Persona>_output_enriched.csv (com Last.fm + MusicBrainz)
    consolidated/
      consolidado_input.csv                 (4 personas concatenadas)
      consolidado_output.csv

  reports/
    inputs/
      figures/<persona>/, figures/cross/    PNGs gerados a partir dos inputs
      summaries/                            tabelas e .txt de summarie
    outputs/
      figures/<persona>/, figures/cross/    PNGs gerados a partir dos outputs
      summaries/
    comparison/                             análises Delta Input vs Output

CONVENÇÕES DE METRICA (após Spotify Fev/2026):
  Os scripts NÃO devem mais ler artist_popularity / artist_followers / artist_genres
  / track_popularity diretamente — esses campos foram removidos da Web API.
  Em vez disso, usar as colunas externas via harmonize_row():
    - _followers       ← lastfm_listeners
    - _genres          ← mb_tags || lastfm_tags
    - _popularity      ← lastfm_playcount (artista, histórico)
    - _track_listeners ← lastfm_track_listeners (substitui track_popularity)
    - _track_playcount ← lastfm_track_playcount

Ver PROGRESSO.md §7 e PLANO_REFATORACAO.md para detalhes.
"""

import os
import sys

PERSONAS = ["beatriz", "daniel", "ricardo", "sofia"]


# ============================================================================
# CLI — parsing de argumentos comuns
# ============================================================================

def parse_source(argv=None):
    """Lê `--source=input|output` da linha de comando. Default: 'input'."""
    if argv is None:
        argv = sys.argv[1:]
    for arg in argv:
        if arg.startswith("--source="):
            value = arg.split("=", 1)[1].lower()
            if value in ("input", "output"):
                return value
    return "input"


def is_source_arg(arg):
    """True se o argumento for `--source=...`."""
    return arg.startswith("--source=")


# ============================================================================
# PATHS — resolução de caminhos por modo
# ============================================================================

def get_paths(project_root, source="input"):
    """
    Retorna paths e padrões resolvidos para o modo escolhido.

    Convenções:
        - data/inputs/dataset_<Persona>_input{_enriched}.csv
        - data/outputs/dataset_<Persona>_output{_enriched}.csv
        - reports/<source>/figures/<persona>/...
        - reports/<source>/summaries/...
    """
    if source == "output":
        return {
            "source": "output",
            "label": "OUTPUT (Daily Mix mirrors)",
            "data_dir": os.path.join(project_root, "data", "outputs"),
            "csv_pattern_raw": "dataset_{persona_cap}_output.csv",
            "csv_pattern_enriched": "dataset_{persona_cap}_output_enriched.csv",
            "consolidated_csv_name": "consolidado_output.csv",
            "consolidated_dir": os.path.join(project_root, "data", "consolidated"),
            "reports_figures_dir": os.path.join(project_root, "reports", "outputs", "figures"),
            "reports_summaries_dir": os.path.join(project_root, "reports", "outputs", "summaries"),
        }
    return {
        "source": "input",
        "label": "INPUT (training seed playlists)",
        "data_dir": os.path.join(project_root, "data", "inputs"),
        "csv_pattern_raw": "dataset_{persona_cap}_input.csv",
        "csv_pattern_enriched": "dataset_{persona_cap}_input_enriched.csv",
        "consolidated_csv_name": "consolidado_input.csv",
        "consolidated_dir": os.path.join(project_root, "data", "consolidated"),
        "reports_figures_dir": os.path.join(project_root, "reports", "inputs", "figures"),
        "reports_summaries_dir": os.path.join(project_root, "reports", "inputs", "summaries"),
    }


def csv_path_for(persona, project_root, source="input", enriched=True):
    """Caminho do CSV de uma persona, no modo escolhido. Default: enriched."""
    paths = get_paths(project_root, source)
    pattern = paths["csv_pattern_enriched"] if enriched else paths["csv_pattern_raw"]
    filename = pattern.format(persona_cap=persona.capitalize())
    return os.path.join(paths["data_dir"], filename)


def consolidated_path_for(project_root, source="input"):
    """Caminho do CSV consolidado (4 personas) para o modo escolhido."""
    paths = get_paths(project_root, source)
    return os.path.join(paths["consolidated_dir"], paths["consolidated_csv_name"])


def figures_dir_for(project_root, source="input", persona=None):
    """Pasta de figures (cross ou per-persona) para o modo escolhido."""
    paths = get_paths(project_root, source)
    base = paths["reports_figures_dir"]
    return os.path.join(base, persona) if persona else os.path.join(base, "cross")


def summaries_dir_for(project_root, source="input"):
    """Pasta de summaries (.txt + tabelas .csv) para o modo escolhido."""
    return get_paths(project_root, source)["reports_summaries_dir"]


# ============================================================================
# HARMONIZAÇÃO de schema — esconde a transição Spotify→Externo
# ============================================================================
# Os scripts da Fase 4 leem '_followers', '_genres', '_popularity', '_track_listeners',
# '_track_playcount' independente da origem. Quando uma fonte externa não cobriu
# o artista, valores ficam em 0/vazio (entram naturalmente como Cauda Longa).
# ============================================================================

def safe_int(v, default=0):
    """Converte para int tolerando valores vazios/string."""
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def harmonize_row(row):
    """
    Adiciona colunas harmonizadas a uma linha de CSV.

    Mapeamento:
        - _followers       ← lastfm_listeners (proxy de seguidores)
        - _popularity      ← lastfm_playcount (artista, histórico cumulativo)
        - _genres          ← mb_tags || lastfm_tags || artist_genres
        - _track_listeners ← lastfm_track_listeners (substitui track_popularity)
        - _track_playcount ← lastfm_track_playcount

    Por que existe:
        Após a remoção dos campos Spotify (Fev/2026), todas as análises
        passaram a depender de Last.fm + MusicBrainz. Esta função desacopla
        os scripts de análise da fonte de dados subjacente.
    """
    row["_followers"] = safe_int(row.get("lastfm_listeners"), 0)
    row["_popularity"] = safe_int(row.get("lastfm_playcount"), 0)
    row["_track_listeners"] = safe_int(row.get("lastfm_track_listeners"), 0)
    row["_track_playcount"] = safe_int(row.get("lastfm_track_playcount"), 0)

    genres = (row.get("mb_tags") or "").strip()
    if not genres:
        genres = (row.get("lastfm_tags") or "").strip()
    if not genres:
        genres = (row.get("artist_genres") or "").strip()
    row["_genres"] = genres

    return row


def load_enriched_csv(csv_path):
    """Carrega um CSV enriched e harmoniza cada linha. Retorna lista de dicts."""
    import csv as _csv
    if not os.path.exists(csv_path):
        return []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        rows = list(_csv.DictReader(f))
    return [harmonize_row(r) for r in rows]
