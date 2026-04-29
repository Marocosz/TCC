"""
================================================================================
CONVERSOR DE CSVs DO EXPORTIFY → SCHEMA DO TCC
================================================================================

Objetivo:
    Pegar os CSVs baixados do Exportify (https://exportify.net) das 4 playlists
    espelho dos Daily Mixes e convertê-los para o mesmo schema dos baselines
    (dataset_<Persona>_playlist.csv), permitindo que o resto do pipeline da
    Fase 4 rode sem alterações.

Por que existe:
    Em 2025-2026 o Spotify bloqueou o endpoint /playlists/{id}/tracks para
    apps em Development Mode. Exportify (registrado como app de produção)
    ainda funciona e é o método mais rápido de extrair tracks de uma playlist.
    Este script faz a ponte: Exportify CSV → schema do TCC.

Fluxo:
    1. Lê data/recommendations/raw_exportify/<persona>.csv
    2. Para cada track, mapeia colunas Exportify → schema TCC
    3. Coleta artist URIs únicos
    4. Faz batch de /artists/{id} (até 50 por request) para enriquecer
       com artist_popularity e artist_followers (não vem no Exportify)
    5. Salva data/recommendations/dataset_<Persona>_recommendations.csv

Uso:
    python src/analysis/convert_exportify_csv.py [persona|todas]

Dependências:
    - .env configurado com SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET
    - CSVs do Exportify em data/recommendations/raw_exportify/
    - O endpoint /artists/{id} do Spotify (não foi bloqueado, só /playlists/.../tracks)
"""

import os
import sys
import csv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv()

PERSONAS = ["beatriz", "daniel", "ricardo", "sofia"]

# Mapeamento das colunas do Exportify (esquerda) para o schema do TCC (direita).
# O schema do Exportify pode variar por versão; este mapping cobre as colunas
# atuais (versão 2024-2026 do exportify.net).
EXPORTIFY_COL_VARIANTS = {
    "track_name": ["Track Name"],
    "track_popularity": ["Popularity", "Track Popularity"],
    "primary_artist_name": ["Artist Name(s)", "Artist Name", "Artists"],
    "all_artists": ["Artist Name(s)", "Artist Name", "Artists"],
    "artist_genres": ["Artist Genres", "Genres"],
    "album_name": ["Album Name"],
    "album_release_date": ["Album Release Date", "Release Date"],
    "is_explicit": ["Explicit"],
    "track_url": ["Track URL", "Track Preview URL"],
    "track_uri": ["Track URI", "Spotify URI"],
    "artist_uri": ["Artist URI(s)", "Artist URIs", "Artists URIs"],
    "duration_ms": ["Track Duration (ms)", "Duration (ms)", "Duration"],
}


def first_existing(row, candidates):
    """Retorna o valor da primeira coluna candidata que existir no row dict."""
    for col in candidates:
        if col in row:
            return row[col]
    return ""


def ms_para_min_seg(ms_str):
    """Converte ms (string) para 'M:SS'."""
    try:
        ms = float(ms_str)
    except (TypeError, ValueError):
        return "0:00"
    total_segundos = int(ms / 1000)
    return f"{total_segundos // 60}:{total_segundos % 60:02}"


def extract_id_from_uri(uri):
    """Extrai o ID de um URI do Spotify (ex: spotify:artist:abc123 → abc123)."""
    if not uri:
        return None
    if ":" in uri:
        return uri.split(":")[-1]
    return uri


def enriquecer_artistas(artist_ids, sp):
    """
    Busca popularity, followers e genres de artistas em lote (até 50 por request).
    Retorna dict {artist_id: {popularity, followers, genres}}.
    """
    artist_map = {}
    artist_ids = [aid for aid in artist_ids if aid]
    print(f"  Enriquecendo {len(artist_ids)} artistas únicos...")

    for i in range(0, len(artist_ids), 50):
        batch = artist_ids[i : i + 50]
        try:
            response = sp.artists(batch)
            for artist in response.get("artists", []):
                if artist:
                    artist_map[artist["id"]] = {
                        "popularity": artist.get("popularity", 0),
                        "followers": artist.get("followers", {}).get("total", 0),
                        "genres": "; ".join(artist.get("genres", [])),
                    }
        except Exception as e:
            print(f"  [!] Erro ao buscar batch de artistas: {e}")

    print(f"  Detalhes obtidos para {len(artist_map)} artistas.")
    return artist_map


def converter_persona(persona, project_root, sp):
    """
    Lê o CSV do Exportify de uma persona e gera o CSV no schema do TCC.
    """
    print(f"\n{'=' * 60}")
    print(f"  CONVERSÃO: {persona.upper()}")
    print('=' * 60)

    input_path = os.path.join(
        project_root, "data", "recommendations", "raw_exportify", f"{persona}.csv"
    )
    output_path = os.path.join(
        project_root, "data", "recommendations", f"dataset_{persona.capitalize()}_recommendations.csv"
    )

    if not os.path.exists(input_path):
        print(f"  [!] CSV do Exportify não encontrado: {input_path}")
        print(f"      Baixe a playlist espelho da {persona} via https://exportify.net")
        print(f"      e salve nesse caminho.")
        return False

    # Lê CSV do Exportify
    rows_exportify = []
    with open(input_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows_exportify = list(reader)

    print(f"  Lidas {len(rows_exportify)} faixas do Exportify CSV.")
    if rows_exportify:
        print(f"  Colunas detectadas: {list(rows_exportify[0].keys())[:8]}...")

    # Coleta IDs de artistas (primeiro de cada lista)
    artist_ids_unique = set()
    for row in rows_exportify:
        artist_uris_raw = first_existing(row, EXPORTIFY_COL_VARIANTS["artist_uri"])
        # Pode vir como "spotify:artist:abc, spotify:artist:def" — pega o primeiro
        primary_uri = artist_uris_raw.split(",")[0].strip() if artist_uris_raw else ""
        primary_id = extract_id_from_uri(primary_uri)
        if primary_id:
            artist_ids_unique.add(primary_id)

    # Enriquece via API
    artist_details = enriquecer_artistas(list(artist_ids_unique), sp)

    # Monta linhas no schema do TCC
    linhas_finais = []
    for row in rows_exportify:
        # Multi-artist string
        all_artists_str = first_existing(row, EXPORTIFY_COL_VARIANTS["all_artists"])
        # Primeiro artista (separado por vírgula no Exportify)
        primary_artist_name = all_artists_str.split(",")[0].strip() if all_artists_str else "N/A"

        # Primeiro artist URI
        artist_uris_raw = first_existing(row, EXPORTIFY_COL_VARIANTS["artist_uri"])
        primary_uri = artist_uris_raw.split(",")[0].strip() if artist_uris_raw else ""
        primary_id = extract_id_from_uri(primary_uri)
        details = artist_details.get(primary_id, {})

        # Gêneros: prefere o que veio do Exportify, fallback no enriquecido
        genres_str = first_existing(row, EXPORTIFY_COL_VARIANTS["artist_genres"])
        if not genres_str:
            genres_str = details.get("genres", "")

        # Track URL: se Exportify deu URI, monta a URL; senão usa o que tiver
        track_uri = first_existing(row, EXPORTIFY_COL_VARIANTS["track_uri"])
        track_id = extract_id_from_uri(track_uri)
        track_url = f"https://open.spotify.com/track/{track_id}" if track_id else ""

        # Duração
        duration_ms = first_existing(row, EXPORTIFY_COL_VARIANTS["duration_ms"])

        linhas_finais.append({
            "track_name": first_existing(row, EXPORTIFY_COL_VARIANTS["track_name"]),
            "primary_artist_name": primary_artist_name,
            "all_artists": all_artists_str.replace(", ", "; "),
            "album_name": first_existing(row, EXPORTIFY_COL_VARIANTS["album_name"]),
            "track_popularity": first_existing(row, EXPORTIFY_COL_VARIANTS["track_popularity"]),
            "artist_popularity": details.get("popularity", 0),
            "artist_followers": details.get("followers", 0),
            "artist_genres": genres_str.replace(", ", "; "),
            "album_release_date": first_existing(row, EXPORTIFY_COL_VARIANTS["album_release_date"]),
            "duration_readable": ms_para_min_seg(duration_ms),
            "is_explicit": first_existing(row, EXPORTIFY_COL_VARIANTS["is_explicit"]),
            "track_url": track_url,
            "track_uri": track_uri,
        })

    # Salva no schema TCC
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    colunas = [
        "track_name", "primary_artist_name", "all_artists", "album_name",
        "track_popularity", "artist_popularity", "artist_followers", "artist_genres",
        "album_release_date", "duration_readable", "is_explicit", "track_url", "track_uri",
    ]
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=colunas)
        writer.writeheader()
        writer.writerows(linhas_finais)

    print(f"  ✅ {len(linhas_finais)} linhas salvas em {output_path}")
    return True


def main():
    if len(sys.argv) < 2:
        print("\nUso: python convert_exportify_csv.py [persona|todas]")
        print(f"Personas: {', '.join(PERSONAS)}")
        return

    arg = sys.argv[1].lower()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))

    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

    alvos = PERSONAS if arg in ("todas", "all") else [arg]
    for persona in alvos:
        if persona not in PERSONAS:
            print(f"[!] Persona inválida: {persona}")
            continue
        converter_persona(persona, project_root, sp)


if __name__ == "__main__":
    main()
