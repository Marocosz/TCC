"""
================================================================================
INFERÊNCIA ESTATÍSTICA — Bootstrap CI, Mann-Whitney, Rarefação, Permutação
================================================================================

Objetivo:
    Dotar a auditoria de tratamento inferencial (não apenas estimativas
    pontuais), como exige o paradigma de sock-puppet audit (Sandvig et al.,
    2014; Datta, Tschantz & Datta, 2015 — AdFisher usa testes de permutação).

    Resolve os problemas #1 (inferência), #5 (rarefação/confound de N),
    #6 (Jaccard cross-persona + permutação), #11 (IC/p nos deltas),
    #14 (composição de tipo com base absoluta) e #9 (composição de país).

Saídas (reports/comparison/):
    significancia.csv            — IC 95% bootstrap de Shannon/Pielou/Gini/HHI/medianas
    significancia_mannwhitney.csv — U e p (input vs output) das distribuições de listeners
    rarefacao.csv                — S, H, J do output subamostrado a N=200 (controle de N)
    jaccard_significancia.csv    — Jaccard cross-persona (artista e tag) vs nulo de permutação
    composicao_tipo.csv          — % solo/grupo com n absoluto e IC de Wilson (#14)
    composicao_pais.csv          — % BR vs não-BR por persona (#9, viés geocultural)

Reprodutibilidade:
    RNG com semente fixa (SEED=42). Reexecutar produz os mesmos números.

Uso:
    python src/analysis/build_significance.py
"""

import os
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _source_config import csv_path_for, PERSONAS
from build_delta_metrics import shannon, gini, hhi, explode_tags, get_genre_string

SEED = 42
N_BOOT = 1000
N_PERM = 2000
RAREF_N = 200          # tamanho-alvo da rarefação (= N dos inputs)
Z = 1.959963984540054  # quantil normal para IC 95%


def pielou(series):
    s = series.nunique()
    if s < 2:
        return float("nan")
    return float(shannon(series) / np.log2(s))


def numeric(df, col):
    return pd.to_numeric(df.get(col), errors="coerce").fillna(0)


def load(persona, source):
    df = pd.read_csv(csv_path_for(persona, project_root(), source, enriched=True))
    return df


def project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# BOOTSTRAP — IC 95% por percentis (Efron & Tibshirani, 1993)
# ============================================================================

def bootstrap_ci(rng, base, fn, n_boot=N_BOOT):
    """Reamostra `base` (DataFrame ou Series) com reposição n_boot vezes,
    aplica `fn` ao resample e retorna (estimativa_pontual, ic_inf, ic_sup)."""
    point = fn(base)
    n = len(base)
    if n == 0:
        return point, float("nan"), float("nan")
    boots = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        boots[b] = fn(base.iloc[idx])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(point), float(lo), float(hi)


def run_bootstrap(rng):
    """IC bootstrap APENAS para medianas de audiência.

    O bootstrap com reposição é válido para medianas, mas é enviesado para
    baixo em métricas de entropia/riqueza (Shannon, Pielou, Gini, riqueza S):
    reamostrar com reposição introduz duplicatas, reduz o nº de artistas únicos
    e, com ele, a entropia — fazendo a estimativa pontual cair FORA do IC. Por
    isso a incerteza dessas métricas de forma é tratada por rarefação
    (run_rarefaction, Gotelli & Colwell 2001), não aqui. Ver #1/#5."""
    rows = []
    for source in ("input", "output"):
        for persona in PERSONAS:
            df = load(persona, source).copy()
            df["_lst"] = numeric(df, "lastfm_listeners")
            df["_pc"] = numeric(df, "lastfm_playcount")
            df["_tlst"] = numeric(df, "lastfm_track_listeners")
            artists_df = df.drop_duplicates(subset=["primary_artist_name"])

            specs = [
                ("listeners_med_artista", artists_df, lambda d: float(d["_lst"].median())),
                ("playcount_med_artista", artists_df, lambda d: float(d["_pc"].median())),
                ("listeners_med_track", df, lambda d: float(d["_tlst"].median())),
            ]
            for name, base, fn in specs:
                est, lo, hi = bootstrap_ci(rng, base, fn)
                rows.append({
                    "Persona": persona.capitalize(), "Source": source.upper(),
                    "Metrica": name, "Estimativa": round(est, 4),
                    "IC_inf_95": round(lo, 4), "IC_sup_95": round(hi, 4),
                })
    return pd.DataFrame(rows)


# ============================================================================
# MANN-WHITNEY U — input vs output, distribuições track-level (Mann & Whitney 1947)
# ============================================================================

def run_mannwhitney():
    from scipy.stats import mannwhitneyu
    rows = []
    for persona in PERSONAS:
        din = load(persona, "input")
        dout = load(persona, "output")
        for var, col in (("listeners_por_artista", "lastfm_listeners"),
                         ("listeners_por_track", "lastfm_track_listeners")):
            x = pd.to_numeric(din.get(col), errors="coerce").dropna().values
            y = pd.to_numeric(dout.get(col), errors="coerce").dropna().values
            if len(x) == 0 or len(y) == 0:
                continue
            U, p = mannwhitneyu(x, y, alternative="two-sided")
            cles = U / (len(x) * len(y))  # common-language effect size P(X>Y)
            rows.append({
                "Persona": persona.capitalize(), "Variavel": var,
                "Mediana_input": round(float(np.median(x)), 1),
                "Mediana_output": round(float(np.median(y)), 1),
                "U": round(float(U), 1), "p_valor": float(f"{p:.2e}"),
                "Efeito_CLES": round(float(cles), 3),
                "n_input": len(x), "n_output": len(y),
            })
    return pd.DataFrame(rows)


# ============================================================================
# RAREFAÇÃO — controla o confound de N (Gotelli & Colwell, 2001)
# ============================================================================

def run_rarefaction(rng):
    rows = []
    for persona in PERSONAS:
        din = load(persona, "input")
        dout = load(persona, "output")
        in_art = din["primary_artist_name"]
        out_art = dout["primary_artist_name"]

        def shape(series):
            return {"S": series.nunique(), "H": shannon(series),
                    "J": pielou(series), "Gini": gini(series)}

        # ponto de partida (sem rarefação)
        base = {
            "input_obs": dict(shape(in_art), N=len(din)),
            "output_full": dict(shape(out_art), N=len(dout)),
        }

        # rarefação do output para N=RAREF_N, sem reposição, N_BOOT vezes
        n = len(dout)
        if n >= RAREF_N:
            acc = {k: np.empty(N_BOOT) for k in ("S", "H", "J", "Gini")}
            for b in range(N_BOOT):
                idx = rng.choice(n, size=RAREF_N, replace=False)
                vals = shape(out_art.iloc[idx])
                for k in acc:
                    acc[k][b] = vals[k]
            raref = {k: (v.mean(), np.percentile(v, [2.5, 97.5])) for k, v in acc.items()}
        else:
            raref = None

        for metric in ("S", "H", "J", "Gini"):
            r = {
                "Persona": persona.capitalize(), "Metrica": metric,
                "Input_N200": round(base["input_obs"][metric], 4),
                "Output_full": round(base["output_full"][metric], 4),
                "Output_N_full": base["output_full"]["N"],
            }
            if raref:
                mean, (lo, hi) = raref[metric]
                r.update({
                    "Output_rarefeito_media": round(float(mean), 4),
                    "Output_raref_IC_inf": round(float(lo), 4),
                    "Output_raref_IC_sup": round(float(hi), 4),
                })
            rows.append(r)
    return pd.DataFrame(rows)


# ============================================================================
# JACCARD CROSS-PERSONA + PERMUTAÇÃO (#6) — artista e tag
# ============================================================================

def _mean_pairwise_jaccard(sets):
    keys = list(sets)
    pairs = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = sets[keys[i]], sets[keys[j]]
            u = len(a | b)
            pairs.append(len(a & b) / u if u else 0.0)
    return float(np.mean(pairs))


def _artist_sets(source):
    return {p.capitalize(): set(load(p, source)["primary_artist_name"].dropna().str.strip())
            for p in PERSONAS}


def _tag_sets(source):
    out = {}
    for p in PERSONAS:
        df = load(p, source)
        tags = set()
        for s in df.apply(get_genre_string, axis=1):
            tags.update(explode_tags(s))
        out[p.capitalize()] = tags
    return out


def _permute_jaccard(rng, sets):
    """Nulo: para cada persona, sorteia (sem reposição) um subconjunto do
    universo combinado, do mesmo tamanho do conjunto observado. Quebra a
    associação persona↔repertório preservando os tamanhos."""
    universe = sorted(set().union(*sets.values()))
    U = len(universe)
    sizes = {k: len(v) for k, v in sets.items()}
    null = np.empty(N_PERM)
    for b in range(N_PERM):
        perm = {k: set(rng.choice(U, size=sizes[k], replace=False)) for k in sets}
        null[b] = _mean_pairwise_jaccard(perm)
    return null


def run_jaccard(rng):
    rows = []
    for nivel, getter in (("artista", _artist_sets), ("tag", _tag_sets)):
        for source in ("input", "output"):
            sets = getter(source)
            obs = _mean_pairwise_jaccard(sets)
            null = _permute_jaccard(rng, sets)
            # Phipson & Smyth (2010): (b+1)/(m+1), nunca zero
            p_greater = (np.sum(null >= obs) + 1) / (N_PERM + 1)
            p_less = (np.sum(null <= obs) + 1) / (N_PERM + 1)
            rows.append({
                "Nivel": nivel, "Source": source.upper(),
                "Jaccard_obs": round(obs, 4),
                "Jaccard_nulo_media": round(float(null.mean()), 4),
                "Nulo_IC_inf": round(float(np.percentile(null, 2.5)), 4),
                "Nulo_IC_sup": round(float(np.percentile(null, 97.5)), 4),
                "p_obs_maior_que_acaso": round(float(p_greater), 4),
                "p_obs_menor_que_acaso": round(float(p_less), 4),
            })
    return pd.DataFrame(rows)


# ============================================================================
# COMPOSIÇÃO DE TIPO (#14) e PAÍS (#9) — com n absoluto e cobertura
# ============================================================================

def wilson_ci(k, n):
    """IC de Wilson 95% para uma proporção k/n (robusto a base pequena)."""
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    denom = 1 + Z * Z / n
    center = (p + Z * Z / (2 * n)) / denom
    half = Z * np.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def run_composition_type():
    rows = []
    for source in ("input", "output"):
        for persona in PERSONAS:
            art = load(persona, source).drop_duplicates(subset=["primary_artist_name"])
            n_art = len(art)
            types = art.get("mb_artist_type", pd.Series(dtype=str)).fillna("").astype(str).str.strip()
            n_typed = int((types != "").sum())
            n_group = int((types == "Group").sum())
            n_person = int((types == "Person").sum())
            lo, hi = wilson_ci(n_group, n_typed) if n_typed else (float("nan"), float("nan"))
            rows.append({
                "Persona": persona.capitalize(), "Source": source.upper(),
                "n_artistas": n_art, "n_tipados": n_typed,
                "pct_cobertura_tipo": round(100 * n_typed / n_art, 1) if n_art else 0,
                "n_grupo": n_group, "n_solo": n_person,
                "pct_grupo": round(100 * n_group / n_typed, 1) if n_typed else float("nan"),
                "pct_grupo_IC_inf": round(100 * lo, 1) if n_typed else float("nan"),
                "pct_grupo_IC_sup": round(100 * hi, 1) if n_typed else float("nan"),
                "pct_solo": round(100 * n_person / n_typed, 1) if n_typed else float("nan"),
            })
    return pd.DataFrame(rows)


def run_composition_country():
    rows = []
    for source in ("input", "output"):
        for persona in PERSONAS:
            art = load(persona, source).drop_duplicates(subset=["primary_artist_name"])
            n_art = len(art)
            country = art.get("mb_country", pd.Series(dtype=str)).fillna("").astype(str).str.strip()
            n_known = int((country != "").sum())
            n_br = int((country == "BR").sum())
            rows.append({
                "Persona": persona.capitalize(), "Source": source.upper(),
                "n_artistas": n_art, "n_com_pais": n_known,
                "pct_cobertura_pais": round(100 * n_known / n_art, 1) if n_art else 0,
                "n_BR": n_br,
                "pct_BR_entre_conhecidos": round(100 * n_br / n_known, 1) if n_known else float("nan"),
                "pct_nao_BR": round(100 * (n_known - n_br) / n_known, 1) if n_known else float("nan"),
            })
    return pd.DataFrame(rows)


# ============================================================================
# MAIN
# ============================================================================

def main():
    rng = np.random.default_rng(SEED)
    out_dir = os.path.join(project_root(), "reports", "comparison")
    os.makedirs(out_dir, exist_ok=True)

    print("\n=== INFERÊNCIA ESTATÍSTICA (semente fixa = %d) ===\n" % SEED)

    jobs = [
        ("significancia.csv", "Bootstrap IC 95%", lambda: run_bootstrap(rng)),
        ("significancia_mannwhitney.csv", "Mann-Whitney U (input vs output)", run_mannwhitney),
        ("rarefacao.csv", "Rarefação (output → N=200)", lambda: run_rarefaction(rng)),
        ("jaccard_significancia.csv", "Jaccard cross-persona + permutação", lambda: run_jaccard(rng)),
        ("composicao_tipo.csv", "Composição solo/grupo + Wilson (#14)", run_composition_type),
        ("composicao_pais.csv", "Composição de país / viés Last.fm (#9)", run_composition_country),
    ]
    for fname, title, fn in jobs:
        df = fn()
        path = os.path.join(out_dir, fname)
        df.to_csv(path, index=False)
        print(f"--- {title} ---")
        print(df.to_string(index=False))
        print(f"[OK] {path}\n")


if __name__ == "__main__":
    main()
