# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based academic research project auditing Spotify's music recommendation algorithm for bias. It uses a black-box auditing methodology (Sandvig et al., 2014) with 4 synthetic personas to test filter bubbles, recency bias, and popularity-driven filtering.

## Setup

```bash
# Activate the virtual environment
source venvtcc/Scripts/activate   # Windows Git Bash
# or
venvtcc\Scripts\activate          # Windows cmd

# Install dependencies
pip install spotipy pandas seaborn matplotlib python-dotenv scipy
```

Credentials are loaded from `.env` at the project root. OAuth tokens require logging into the correct persona's Spotify account in the browser before running collector scripts.

## Pipeline Execution

Scripts run manually in sequence — there is no build system. Follow the 4-phase order documented in `PIPELINE.md`:

**Phase 1 – Reset (Cold Start Control):**
```bash
python src/utils/clear_library.py     # Remove all liked songs
python src/utils/clear_follows.py     # Unfollow all artists
```

**Phase 2 – Data Ingestion (Training Input):**
```bash
python src/analysis/build_persona_raw_data.py   # Mine artist metadata from seed playlists
python src/collectors/create_beatriz_playlist.py
python src/collectors/create_daniel_playlist.py
python src/collectors/create_ricardo_playlist.py
python src/collectors/create_sofia_playlist.py
python src/collectors/sync_persona_follows.py   # Generate explicit follows (run after likes)
```

**Phase 3 – Audit Data Collection** (run after 7+ days of algorithm processing):
```bash
python src/analysis/extrair_dados_playlist.py
python src/analysis/extrair_dados_artistas_seguidos.py
```

**Phase 4 – Analysis & Reporting:**
```bash
python src/analysis/merge_datasets.py
python src/analysis/build_summaries.py
python src/analysis/build_personal_graphs.py
python src/analysis/build_cross_graphs.py
python src/analysis/build_diversity_metrics.py    # Shannon entropy, Pielou evenness, Gini coefficient
python src/analysis/build_similarity_matrix.py    # Jaccard index between personas (+ mean pairwise)
python src/analysis/build_market_metrics.py       # HHI genre concentration; single P25/P75 ruler (input+output)
python src/analysis/build_significance.py         # bootstrap CIs, Mann-Whitney, rarefaction, Jaccard permutation (needs scipy)
```

The inferential outputs (`reports/comparison/significancia*.csv`, `rarefacao.csv`, `jaccard_significancia.csv`, `composicao_*.csv`) are reproducible via a fixed RNG seed in `build_significance.py`.

## Architecture

**Core layer — `src/functions.py`:** Central service module wrapping the Spotify API. Handles OAuth 2.0 (write operations) and Client Credentials (read-only), pagination, batch chunking (100 items/request), and CSV I/O. All other modules import from here.

**Collectors — `src/collectors/`:** Build persona identities on live Spotify accounts. Read CSVs from `data/raw/`, apply persona-specific track selection logic, create playlists, and like tracks.

**Analysis — `src/analysis/`:** Two groups:
- *Data collection scripts* (`extrair_dados_*.py`): Fetch Spotify-generated recommendations into `data/processed/`.
- *Reporting scripts* (`build_*.py`): Compute statistics and generate charts in `reports/`.

**Data flow:**
```
data/raw/ (artist metadata) → Spotify accounts (playlists + likes + follows)
→ [7+ day wait] → data/processed/ (recommendations) → reports/ (summaries + figures)
```

## The Four Personas

| Persona | Archetype | Selection Logic |
|---------|-----------|----------------|
| **Beatriz** | Mainstream/Viral | Pure popularity sort (control group) |
| **Daniel** | Lo-Fi/Functional | Organic distribution with functional tier weighting |
| **Sofia** | Underground/Niche | Deep discography, low-popularity artists |
| **Ricardo** | Nostalgic/Legacy | Legacy catalog, prioritizes pre-2000s releases |

Each persona has a dedicated Spotify account (credentials in `.env`), its own playlist creation script, and its own processed CSV output.

## Key Metrics Computed

- **Shannon Entropy** — genre/artist diversity
- **Gini Coefficient** — inequality of attention across artists
- **HHI (Herfindahl-Hirschman Index)** — genre market concentration
- **Jaccard Index** — set overlap between personas' recommendations

## Code Conventions

Block-level comments are preferred over line-by-line comments. Comments should explain business rules and non-obvious logic, not restate the code.
