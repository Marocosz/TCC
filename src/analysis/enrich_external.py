"""
================================================================================
ENRIQUECIMENTO VIA FONTES EXTERNAS — Last.fm + MusicBrainz
================================================================================

Objetivo:
    Preencher os dados de popularidade, alcance e gênero que a Spotify Web API
    deixou de fornecer em fevereiro/2026 para apps em Development Mode, usando
    fontes externas consagradas: Last.fm (ouvintes, plays históricos, tags) e
    MusicBrainz (tags crowdsourced, país, área geográfica).

Fontes consultadas e campos extraídos:

  Para cada ARTISTA único:
    - Last.fm artist.getInfo:
        * lastfm_listeners  — número de ouvintes únicos no Last.fm
        * lastfm_playcount  — total de plays históricos
        * lastfm_tags       — top 5 tags (proxy de gêneros)
    - MusicBrainz /artist:
        * mb_country        — código ISO do país de origem
        * mb_area           — nome da região
        * mb_tags           — top 5 tags crowdsourced
        * mb_score          — confiança do match (0-100)

  Para cada TRACK única (artist+track):
    - Last.fm track.getInfo:
        * lastfm_track_listeners  — proxy de track_popularity
        * lastfm_track_playcount  — total de plays da faixa

Cache:
    `data/external_cache.json` com duas seções: "artists" e "tracks".
    Persistência incremental — script pode ser interrompido e retomado.

Schema final (colunas adicionadas ao CSV de entrada):
    lastfm_listeners, lastfm_playcount, lastfm_tags,
    mb_country, mb_area, mb_tags, mb_score,
    lastfm_track_listeners, lastfm_track_playcount,
    external_source

Uso:
    python src/analysis/enrich_external.py daniel --source=output
    python src/analysis/enrich_external.py todas --source=input
    python src/analysis/enrich_external.py todas --source=output

Pré-requisitos:
    - LASTFM_API_KEY no .env (https://www.last.fm/api/account/create)
    - User-Agent obrigatório no MusicBrainz (já configurado)
"""

import os
import sys
import csv
import json
import time
import requests
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

# UTF-8 no stdout (PowerShell default = cp1252 → quebra com nomes em alfabetos
# diversos). Assim print() funciona com qualquer artista do mundo.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY", "").strip()
USER_AGENT = "TCC-Auditoria-Spotify/1.0 (marcos.oliveira@finza.com.br)"

PERSONAS = ["beatriz", "daniel", "ricardo", "sofia"]

# Helper compartilhado de paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from _source_config import csv_path_for, get_paths

PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
CACHE_PATH = os.path.join(PROJECT_ROOT, "data", "external_cache.json")


# ============================================================================
# CACHE — duas seções (artists + tracks), persistência incremental
# ============================================================================

def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Compatibilidade com cache antigo (flat)
            if "artists" not in data:
                data = {"artists": data, "tracks": {}}
            data.setdefault("artists", {})
            data.setdefault("tracks", {})
            return data
        except Exception:
            pass
    return {"artists": {}, "tracks": {}}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# ============================================================================
# LAST.FM — artist.getInfo
# ============================================================================

def fetch_lastfm_artist(artist_name):
    """artist.getInfo → {lastfm_listeners, lastfm_playcount, lastfm_tags}."""
    if not LASTFM_API_KEY or not artist_name:
        return None
    url = (
        f"http://ws.audioscrobbler.com/2.0/"
        f"?method=artist.getInfo"
        f"&artist={quote_plus(artist_name)}"
        f"&api_key={LASTFM_API_KEY}"
        f"&format=json"
        f"&autocorrect=1"
    )
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if "error" in data:
            return None
        artist = data.get("artist") or {}
        stats = artist.get("stats") or {}
        tags_obj = (artist.get("tags") or {}).get("tag") or []
        tags_list = [t.get("name", "") for t in tags_obj if t.get("name")]
        return {
            "lastfm_listeners": int(stats.get("listeners", 0) or 0),
            "lastfm_playcount": int(stats.get("playcount", 0) or 0),
            "lastfm_tags": "; ".join(tags_list[:5]),
        }
    except Exception:
        return None


# ============================================================================
# LAST.FM — track.getInfo
# ============================================================================

def fetch_lastfm_track(artist_name, track_name):
    """track.getInfo → {lastfm_track_listeners, lastfm_track_playcount, lastfm_track_tags}."""
    if not LASTFM_API_KEY or not (artist_name and track_name):
        return None
    url = (
        f"http://ws.audioscrobbler.com/2.0/"
        f"?method=track.getInfo"
        f"&artist={quote_plus(artist_name)}"
        f"&track={quote_plus(track_name)}"
        f"&api_key={LASTFM_API_KEY}"
        f"&format=json"
        f"&autocorrect=1"
    )
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if "error" in data:
            return None
        track = data.get("track") or {}
        # Extrai toptags da track (lista de tag objects com name)
        tags_obj = (track.get("toptags") or {}).get("tag") or []
        tags_list = [t.get("name", "") for t in tags_obj if t.get("name")]
        return {
            "lastfm_track_listeners": int(track.get("listeners", 0) or 0),
            "lastfm_track_playcount": int(track.get("playcount", 0) or 0),
            "lastfm_track_tags": "; ".join(tags_list[:5]),
        }
    except Exception:
        return None


# ============================================================================
# MUSICBRAINZ — /artist (1 req/seg obrigatório)
# ============================================================================

def fetch_musicbrainz_artist(artist_name):
    """
    /artist → metadata completa do artista.

    Campos extraídos (todos numa única chamada):
        - mb_country, mb_area, mb_tags, mb_score (rodada 1)
        - mb_career_start, mb_career_end — anos início/fim de carreira (life-span)
        - mb_artist_type — Person | Group | Choir | Orchestra | Other
        - mb_gender — Male | Female | Other (apenas para Person)
    """
    if not artist_name:
        return None
    url = (
        f"https://musicbrainz.org/ws/2/artist"
        f"?query=artist:{quote_plus(artist_name)}"
        f"&fmt=json&limit=1"
    )
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        time.sleep(1.0)  # rate limit obrigatório
        if r.status_code != 200:
            return None
        data = r.json()
        artists = data.get("artists") or []
        if not artists:
            return None
        a = artists[0]
        tags_list = [t.get("name", "") for t in (a.get("tags") or []) if t.get("name")]

        # Extrai life-span (apenas o ano)
        life_span = a.get("life-span") or {}
        begin = (life_span.get("begin") or "")[:4]  # "1981-..." → "1981"
        end = (life_span.get("end") or "")[:4]

        return {
            "mb_country": a.get("country", ""),
            "mb_area": (a.get("area") or {}).get("name", ""),
            "mb_tags": "; ".join(tags_list[:5]),
            "mb_score": int(a.get("score", 0) or 0),
            "mb_career_start": begin,
            "mb_career_end": end,
            "mb_artist_type": a.get("type", ""),
            "mb_gender": a.get("gender", ""),
        }
    except Exception:
        return None


# ============================================================================
# PIPELINE de enrichment
# ============================================================================

ARTIST_FIELDS = [
    # Rodada 1 (Last.fm artist + MB básico)
    "lastfm_listeners", "lastfm_playcount", "lastfm_tags",
    "mb_country", "mb_area", "mb_tags", "mb_score",
    # Rodada 2 (MB life-span + tipo + gênero, zero custo extra)
    "mb_career_start", "mb_career_end", "mb_artist_type", "mb_gender",
]
TRACK_FIELDS = [
    "lastfm_track_listeners", "lastfm_track_playcount",
    "lastfm_track_tags",  # rodada 2
]

# Campos que indicam se a entrada do cache é da rodada 2 (campos novos).
# Usados pra detectar entries antigas e re-fetch incremental.
ARTIST_V2_MARKER = "mb_career_start"
TRACK_V2_MARKER = "lastfm_track_tags"


def enrich_artist(artist_name, cache):
    """
    Preenche dados do artista (Last.fm + MusicBrainz). Atualiza cache.

    Lógica de "completar" cache antigo (rodada 1) com campos novos (rodada 2):
        - Se entry no cache JÁ TEM os campos v2 (mb_career_start), reusa.
        - Se entry existe mas NÃO TEM campos v2, refaz APENAS o fetch do MB
          pra completar (Last.fm não muda — preserva).
        - Se entry não existe, fetch completo das duas APIs.
    """
    if not artist_name or artist_name == "N/A":
        return {}

    key = artist_name.strip().lower()
    cached = cache["artists"].get(key)

    if cached is not None and ARTIST_V2_MARKER in cached:
        return cached  # cache completo, nada a fazer

    # Caso 1: entry parcial (rodada 1) — completa só o MB
    if cached is not None:
        print(f"   art {artist_name[:44]:<44} [completar v2]", end=" ", flush=True)
        mb = fetch_musicbrainz_artist(artist_name)
        if mb and mb.get("mb_score", 0) >= 70:
            cached.update(mb)
            print(f"MB[{mb.get('mb_country', '??'):>2}] start={mb.get('mb_career_start','--'):>4}", flush=True)
        else:
            cached.setdefault("mb_career_start", "")
            cached.setdefault("mb_career_end", "")
            cached.setdefault("mb_artist_type", "")
            cached.setdefault("mb_gender", "")
            print("MB[--]", flush=True)
        cache["artists"][key] = cached
        return cached

    # Caso 2: entry novo — fetch completo
    print(f"   art {artist_name[:48]:<48}", end=" ", flush=True)
    enriched = {}
    sources = []

    lf = fetch_lastfm_artist(artist_name)
    if lf and lf.get("lastfm_listeners", 0) > 0:
        enriched.update(lf)
        sources.append("lastfm")
        print(f"LF[{lf['lastfm_listeners']:>10,}L]", end=" ", flush=True)
    else:
        enriched.update({"lastfm_listeners": 0, "lastfm_playcount": 0, "lastfm_tags": ""})
        print("LF[--]              ", end=" ", flush=True)

    mb = fetch_musicbrainz_artist(artist_name)
    if mb and mb.get("mb_score", 0) >= 70:
        enriched.update(mb)
        sources.append("mb")
        print(f"MB[{mb.get('mb_country', '??'):>2}]", flush=True)
    else:
        enriched.update({
            "mb_country": "", "mb_area": "", "mb_tags": "", "mb_score": 0,
            "mb_career_start": "", "mb_career_end": "",
            "mb_artist_type": "", "mb_gender": "",
        })
        print("MB[--]", flush=True)

    enriched["external_source"] = "+".join(sources) if sources else "none"
    cache["artists"][key] = enriched
    return enriched


def enrich_track(artist_name, track_name, cache):
    """
    Preenche dados da track via Last.fm track.getInfo. Atualiza cache.

    Lógica de "completar":
        - Se entry no cache tem campos v2 (lastfm_track_tags), reusa.
        - Senão, refetch completo (track.getInfo é uma chamada só).
    """
    if not (artist_name and track_name):
        return {"lastfm_track_listeners": 0, "lastfm_track_playcount": 0,
                "lastfm_track_tags": ""}

    key = f"{artist_name.strip().lower()}|{track_name.strip().lower()}"
    cached = cache["tracks"].get(key)

    if cached is not None and TRACK_V2_MARKER in cached:
        return cached

    lf = fetch_lastfm_track(artist_name, track_name)
    enriched = lf or {"lastfm_track_listeners": 0, "lastfm_track_playcount": 0,
                      "lastfm_track_tags": ""}
    cache["tracks"][key] = enriched
    return enriched


def enrich_csv(input_csv_path, output_csv_path, cache):
    """Lê CSV no schema raw, enriquece via APIs externas, escreve CSV completo."""
    print(f"\n{'=' * 72}")
    print(f" Enriquecendo: {os.path.basename(input_csv_path)}")
    print('=' * 72)

    if not os.path.exists(input_csv_path):
        print(f"   [ERRO] Arquivo não encontrado: {input_csv_path}")
        return False

    with open(input_csv_path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"   [AVISO] CSV vazio.")
        return False

    unique_artists = sorted({r.get("primary_artist_name", "").strip()
                             for r in rows if r.get("primary_artist_name")})

    print(f"   {len(rows)} faixas, {len(unique_artists)} artistas únicos.")
    print(f"   Cache atual: {len(cache['artists'])} artistas, {len(cache['tracks'])} tracks.\n")

    # ETAPA 1: enriquecimento de artistas
    print("   --- ARTISTAS (Last.fm + MusicBrainz) ---")
    for i, artist in enumerate(unique_artists, 1):
        enrich_artist(artist, cache)
        if i % 10 == 0:
            save_cache(cache)
    save_cache(cache)

    # ETAPA 2: enriquecimento de tracks (Last.fm track.getInfo)
    print(f"\n   --- TRACKS (Last.fm track.getInfo) ---")
    track_pairs_to_fetch = []
    for r in rows:
        artist = r.get("primary_artist_name", "").strip()
        track = r.get("track_name", "").strip()
        if artist and track:
            track_pairs_to_fetch.append((artist, track))

    print(f"   Buscando {len(track_pairs_to_fetch)} tracks...")
    for i, (artist, track) in enumerate(track_pairs_to_fetch, 1):
        enrich_track(artist, track, cache)
        if i % 25 == 0:
            print(f"     [{i}/{len(track_pairs_to_fetch)}] cache: {len(cache['tracks'])} tracks")
            save_cache(cache)
    save_cache(cache)

    # ETAPA 3: aplicar enriquecimento a cada linha
    for row in rows:
        artist_key = row.get("primary_artist_name", "").strip().lower()
        track_key = f"{artist_key}|{row.get('track_name', '').strip().lower()}"

        ext_artist = cache["artists"].get(artist_key, {})
        ext_track = cache["tracks"].get(track_key, {})

        for col in ARTIST_FIELDS + ["external_source"]:
            row[col] = ext_artist.get(col, "")
        for col in TRACK_FIELDS:
            row[col] = ext_track.get(col, 0)

    # Schema final = base do TCC + extensões externas
    base_columns = [
        "track_name", "primary_artist_name", "all_artists", "album_name",
        "track_popularity", "artist_popularity", "artist_followers", "artist_genres",
        "album_release_date", "duration_readable", "is_explicit", "track_url", "track_uri",
    ]
    fieldnames = base_columns + ARTIST_FIELDS + TRACK_FIELDS + ["external_source"]

    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    with open(output_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n   [OK] {len(rows)} linhas enriquecidas -> {output_csv_path}")
    return True


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print("\nUso:")
        print("  python enrich_external.py <persona|todas> [--source=input|output]")
        print("  python enrich_external.py <caminho_csv>")
        print(f"\nPersonas: {', '.join(PERSONAS)}")
        return

    if not LASTFM_API_KEY:
        print("[AVISO] LASTFM_API_KEY ausente no .env — Last.fm será pulado.")

    cache = load_cache()
    print(f"[i] Cache carregado: {len(cache['artists'])} artistas, {len(cache['tracks'])} tracks.")

    arg = sys.argv[1]

    # Modo arquivo único
    if arg.endswith(".csv") and os.path.exists(arg):
        out_path = arg.replace(".csv", "_enriched.csv")
        enrich_csv(arg, out_path, cache)
        return

    # Determina source
    source = "input"
    for a in sys.argv[2:]:
        if a.startswith("--source="):
            source = a.split("=", 1)[1].lower()

    if arg.lower() in ("todas", "all"):
        for persona in PERSONAS:
            in_path = csv_path_for(persona, PROJECT_ROOT, source, enriched=False)
            out_path = csv_path_for(persona, PROJECT_ROOT, source, enriched=True)
            enrich_csv(in_path, out_path, cache)
        return

    if arg.lower() in PERSONAS:
        in_path = csv_path_for(arg.lower(), PROJECT_ROOT, source, enriched=False)
        out_path = csv_path_for(arg.lower(), PROJECT_ROOT, source, enriched=True)
        enrich_csv(in_path, out_path, cache)
        return

    print(f"[!] Argumento não reconhecido: {arg}")


if __name__ == "__main__":
    main()
