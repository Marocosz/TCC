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
  Os campos artist_popularity / artist_followers / artist_genres / track_popularity
  foram removidos da Web API. Os scripts da Fase 4 leem DIRETAMENTE as colunas
  externas dos CSVs enriched:
    - lastfm_listeners        (alcance do artista; substitui artist_followers)
    - lastfm_playcount        (popularidade histórica; substitui artist_popularity)
    - lastfm_track_listeners  (alcance da faixa; substitui track_popularity)
    - mb_tags || lastfm_tags  (gêneros; substitui artist_genres)
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
# UTILITÁRIOS
# ============================================================================

def safe_int(v, default=0):
    """Converte para int tolerando valores vazios/string. Usado por build_summaries."""
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default
