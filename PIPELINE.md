# Pipeline de Execução: Auditoria Algorítmica Spotify

> **Versão 2.0** — atualizado em 2026-04-28 após refatoração completa para fontes externas (Last.fm + MusicBrainz).

Este pipeline descreve a ordem lógica e técnica de execução dos scripts para a realização da auditoria de "caixa-preta". O fluxo garante a neutralidade inicial das contas, a ingestão controlada de dados e a extração + enriquecimento dos resultados a partir de fontes externas (após restrições da Spotify Web API em 2024-2026).

---

## 📋 Pré-requisitos Fundamentais

1. **Ambiente virtual ativo**: `source venvtcc/Scripts/activate`
2. **`.env`** na raiz com:
   - `SPOTIPY_CLIENT_ID` (do app de dev — owner deve ter Premium ativo)
   - `SPOTIPY_CLIENT_SECRET`
   - `SPOTIPY_REDIRECT_URI` (ex: `http://127.0.0.1:8000/callback`)
   - `LASTFM_API_KEY` (gratuita em https://www.last.fm/api/account/create)
3. **Dependências**: `spotipy`, `pandas`, `seaborn`, `matplotlib`, `numpy`, `python-dotenv`, `requests`.
4. **User Management** do dev app no Spotify Developer Dashboard inclui as 4 personas como users autorizados.

---

## Fase 1: Higienização (Tabula Rasa) — **uma vez por persona**

> Garante cold start. Faça login na conta da persona alvo no navegador antes de rodar.

### 1.1 Limpar biblioteca
```bash
python src/utils/clear_library.py
```

### 1.2 Limpar artistas seguidos
```bash
python src/utils/clear_follows.py
```

---

## Fase 2: Ingestão / Construção da Persona — **uma vez por persona**

### 2.1 Minerar metadata de artistas das playlists-semente
```bash
python src/analysis/build_persona_raw_data.py
```
Saída: 4 CSVs em `data/raw/`.

### 2.2 Criar playlist da persona + likes
Estar logado como a persona alvo:
```bash
python src/collectors/create_beatriz_playlist.py
python src/collectors/create_daniel_playlist.py
python src/collectors/create_ricardo_playlist.py
python src/collectors/create_sofia_playlist.py
```

### 2.3 Sincronizar follows
```bash
python src/collectors/sync_persona_follows.py
```

---

## Fase 3 (manual): Incubação Algorítmica

**~40 horas de Smart Shuffle por conta-persona**, escutando ativamente o conteúdo. Sem isso o Spotify NÃO gera os Daily Mixes (verificado empiricamente).

Pré-requisito não-trivial documentado na seção 3.4 do README.

---

## Fase 4 (manual): Cópia das Daily Mixes para playlist espelho

Para cada persona:
1. Crie uma playlist nova chamada **"Geradas Spotify (daily mix) - <Persona>"** na conta da persona.
2. Para cada um dos 6 Daily Mixes gerados pelo Spotify:
   - Ctrl+A em todas as faixas → "Adicionar à playlist" → playlist espelho.
   - Aceitar duplicatas se o Spotify avisar (vamos contar duplicatas em metadata).
3. Anote a URL da playlist espelho.
4. Atualize `CONFIG_RECOMMENDATIONS` em [src/analysis/extrair_dados_playlist.py](src/analysis/extrair_dados_playlist.py) com a URL.

> **Por que cópia manual?** A Spotify Web API restringiu o acesso a Daily Mixes em 27/11/2024 para apps Dev Mode. As playlists espelho contornam isso (são playlists do usuário, leitura permitida via OAuth do dono).

---

## Fase 5: Extração via API (resiliente)

Tem dois subfluxos: **--source=input** (playlists-semente) e **--source=output** (playlists espelho).

### 5.1 Extrair INPUTS
```bash
# Para cada persona, faça login dela no browser ANTES (a playlist-semente é privada)
python src/analysis/extrair_dados_playlist.py beatriz --source=input
python src/analysis/extrair_dados_playlist.py daniel  --source=input
python src/analysis/extrair_dados_playlist.py ricardo --source=input
python src/analysis/extrair_dados_playlist.py sofia   --source=input
```
Saída: `data/inputs/dataset_<Persona>_input.csv`

### 5.2 Extrair OUTPUTS
```bash
# Mesmo procedimento, mas para as playlists espelho. Cache OAuth por persona.
python src/analysis/extrair_dados_playlist.py beatriz --source=output
python src/analysis/extrair_dados_playlist.py daniel  --source=output
python src/analysis/extrair_dados_playlist.py ricardo --source=output
python src/analysis/extrair_dados_playlist.py sofia   --source=output
```
Saída: `data/outputs/dataset_<Persona>_output.csv`

### Notas técnicas
- **Endpoint usado**: `/playlists/{id}/items` (novo Feb/2026; spotipy ainda chama o `/tracks` deprecated → usamos requests direto).
- **OAuth por persona**: cache OAuth separado em `.cache_<persona>`. Cada persona precisa logar uma vez.
- **Resiliência**: se algum endpoint do Spotify retornar 403 (caso típico de Fev/2026 para `/artists`), o script salva o CSV com os campos vazios — serão preenchidos na Fase 6.

---

## Fase 6: Enriquecimento via Fontes Externas (Last.fm + MusicBrainz)

Preenche os campos que a Spotify Web API removeu (popularity / followers / genres / track_popularity).

```bash
# Enriquecer todos os inputs
python src/analysis/enrich_external.py todas --source=input

# Enriquecer todos os outputs
python src/analysis/enrich_external.py todas --source=output
```

### O que é adicionado a cada CSV

| Coluna | Origem | Substitui |
|--------|--------|-----------|
| `lastfm_listeners` | Last.fm artist.getInfo | artist_followers |
| `lastfm_playcount` | Last.fm artist.getInfo | artist_popularity (proxy histórico) |
| `lastfm_tags` | Last.fm artist.getInfo | artist_genres (fallback) |
| `mb_country`, `mb_area` | MusicBrainz | (novo, metadata geográfica) |
| `mb_tags` | MusicBrainz | artist_genres (primário) |
| `mb_score` | MusicBrainz | (confiança 0-100 do match) |
| `lastfm_track_listeners` | Last.fm track.getInfo | track_popularity |
| `lastfm_track_playcount` | Last.fm track.getInfo | (novo) |
| `external_source` | derivada | (auditável: lastfm+mb / lastfm / mb / none) |

### Cache
`data/external_cache.json` é incremental e persistente. Se o script for interrompido, retomar continua de onde parou. Cobertura típica: >95% via Last.fm, >85% via MusicBrainz.

### Performance
- Last.fm: sem rate limit duro. ~0.1s por artista, ~0.1s por track.
- MusicBrainz: 1 req/seg obrigatório. Gargalo principal (≈115 artistas → ~2 min/persona).

---

## Fase 7: Análise

> Todos os scripts aceitam `--source=input|output`. Rode primeiro com `input`, depois com `output`, para gerar os dois conjuntos de relatórios.

### 7.1 Consolidação
```bash
python src/analysis/merge_datasets.py --source=input
python src/analysis/merge_datasets.py --source=output
```
Saída: `data/consolidated/consolidado_<source>.csv`

### 7.2 Resumos textuais (.txt)
```bash
python src/analysis/build_summaries.py todas --source=input
python src/analysis/build_summaries.py todas --source=output
```
Saída: `reports/<source>/summaries/summarie_<Persona>.txt`

### 7.3 Insights por persona (6 PNGs + grid 3x2)
```bash
python src/analysis/build_personal_graphs.py todas --source=input
python src/analysis/build_personal_graphs.py todas --source=output
```
Saída: `reports/<source>/figures/<persona>/`

### 7.4 Gráficos cruzados (5 PNGs)
```bash
python src/analysis/build_cross_graphs.py --source=input
python src/analysis/build_cross_graphs.py --source=output
```
Saída: `reports/<source>/figures/cross/`

### 7.5 Métricas matemáticas
```bash
python src/analysis/build_diversity_metrics.py --source=input
python src/analysis/build_diversity_metrics.py --source=output
python src/analysis/build_market_metrics.py    --source=input
python src/analysis/build_market_metrics.py    --source=output
python src/analysis/build_similarity_matrix.py --source=input
python src/analysis/build_similarity_matrix.py --source=output
```
Saída: `reports/<source>/summaries/tabela_*.csv` + `reports/<source>/figures/cross/matriz_similaridade_jaccard.png`

### 7.6 Análises comparativas (Input vs Output)

#### 7.6.1 Taxa de Overlap Interno dos Daily Mixes
```bash
python src/analysis/build_overlap_metrics.py
```
Mede quanto o algoritmo "insiste nas mesmas faixas" entre os 6 Daily Mixes da mesma persona.

Saída: `reports/comparison/overlap_interno.csv`

#### 7.6.2 Delta Algorítmico (Input → Output)
```bash
python src/analysis/build_delta_metrics.py
```
Compara TODAS as métricas entre input e output, persona por persona.

Saída: `reports/comparison/delta_metrics.csv` + `delta_metrics_pivot.csv`

---

## 🛠️ Resumo de Fluxo I/O

| Script | Fase | Entrada | Saída |
|--------|------|---------|-------|
| build_persona_raw_data | 2 | URLs sementes | data/raw/*.csv |
| create_X_playlist | 2 | data/raw/*.csv | Spotify (playlists + likes) |
| sync_persona_follows | 2 | Likes Spotify | Follows Spotify |
| extrair_dados_playlist (input) | 5 | URLs playlists-semente | data/inputs/*.csv |
| extrair_dados_playlist (output) | 5 | URLs playlists espelho | data/outputs/*.csv |
| enrich_external | 6 | data/{inputs,outputs}/*.csv | data/{inputs,outputs}/*_enriched.csv |
| merge_datasets | 7.1 | *_enriched.csv | data/consolidated/*.csv |
| build_summaries | 7.2 | *_enriched.csv | reports/<src>/summaries/*.txt |
| build_personal_graphs | 7.3 | *_enriched.csv | reports/<src>/figures/<persona>/*.png |
| build_cross_graphs | 7.4 | consolidado_*.csv | reports/<src>/figures/cross/*.png |
| build_diversity_metrics | 7.5 | *_enriched.csv | reports/<src>/summaries/tabela_diversidade*.csv |
| build_market_metrics | 7.5 | *_enriched.csv | reports/<src>/summaries/tabela_mercado*.csv |
| build_similarity_matrix | 7.5 | *_enriched.csv | reports/<src>/figures/cross/matriz_*.png |
| build_overlap_metrics | 7.6 | data/outputs/*.csv | reports/comparison/overlap_interno.csv |
| build_delta_metrics | 7.6 | input + output enriched | reports/comparison/delta_metrics*.csv |

---

## Limitações Documentadas

- A coleta dos outputs depende da disposição do Spotify em gerar Daily Mixes (~40h de escuta — Fase 3).
- Os campos quantitativos centrais (`popularity`, `followers`, `genres`) vêm de Last.fm + MusicBrainz, não da Spotify Web API. Apps em Extended Quota Mode poderiam usar Spotify, mas a aprovação para apps acadêmicos é improvável.
- A "Taxa de Overlap Interno" assume pool bruto de 300 (6 mixes × ~50 faixas). Use `--raw=N` para ajustar se a contagem real for diferente.
