# 📘 Guia de Execução do Pipeline de Dados - TCC (Corrigido)

Este documento descreve a ordem lógica e cronológica de execução dos scripts do projeto. Siga este fluxo para garantir que os arquivos base sejam criados, as playlists geradas e os dados analisados corretamente.

---

## 🛠️ 0. Pré-requisitos e Configuração

Antes de iniciar, certifique-se de que:
1.  **Ambiente Virtual:** O ambiente `venvtcc` esteja ativo.
    ```bash
    # Windows
    .\venvtcc\Scripts\activate
    ```
2.  **Dependências:** As bibliotecas estejam instaladas.
    ```bash
    pip install -r requirements.txt
    ```
3.  **Credenciais:** O arquivo `.env` (na raiz) contenha suas credenciais do Spotify (`SPOTIPY_CLIENT_ID`, etc).

---

## 🔄 Fluxo de Execução

### ⚪ FASE 0: Geração dos Dados Brutos (Seed Data)
**Objetivo:** Criar os arquivos CSV iniciais que contêm as listas de artistas base para cada persona. Sem isso, os scripts da Fase 1 não encontram os dados para trabalhar.

**Script:** `src/analysis/build_persona_raw_data.py`
**Comando:**
```bash
python src/analysis/build_persona_raw_data.py
```
**O que ele faz:** Consulta APIs ou listas estáticas e gera os arquivos na pasta `data/raw/`:
* `artistas_topbrasil_dados.csv` (Base para Beatriz)
* `artistas_lofi_dados.csv` (Base para Daniel)
* `artistas_classicos_dados.csv` (Base para Ricardo)
* *(Nota: A Sofia usa uma URL de playlist direto no código, mas este passo é vital para os outros três).*

---

### 🟢 FASE 1: Coleta e Criação de Playlists (Collectors)
**Objetivo:** Ler os CSVs brutos gerados na Fase 0 e interagir com a API do Spotify para criar as playlists reais na sua conta.

**Arquivos de Entrada:** `data/raw/*.csv` (Gerados no passo anterior).
**Arquivos de Saída:** Criação de playlists reais na conta do Spotify.

**Ordem de Execução (Execute todos):**

1.  `python src/collectors/create_beatriz_playlist.py`
2.  `python src/collectors/create_daniel_playlist.py`
3.  `python src/collectors/create_ricardo_playlist.py`
4.  `python src/collectors/create_sofia_playlist.py`

---

### 🟡 FASE 2: Extração e Processamento (Analysis - ETL)
**Objetivo:** Baixar os dados técnicos (áudio features, popularidade) das playlists recém-criadas no Spotify e salvar em CSVs processados para análise.

**Arquivos de Entrada:** As Playlists que estão online no Spotify.
**Arquivos de Saída:** `data/processed/analise_{Persona}_playlist.csv`.

**Ordem de Execução:**

1.  **Extração Individual:**
    ```bash
    python src/analysis/extrair_dados_playlist.py
    ```
    * *Varre as playlists da conta e salva os metadados em `data/processed`.*

2.  **Consolidação (Merge):**
    ```bash
    python src/analysis/merge_datasets.py
    ```
    * *Junta todos os CSVs individuais em um único arquivo mestre para gráficos comparativos.*

---

### 🔴 FASE 3: Visualização e Relatórios (Viz & Reports)
**Objetivo:** Gerar gráficos e textos explicativos baseados nos dados processados.

**Arquivos de Entrada:** `data/processed/*.csv`.
**Arquivos de Saída:** `reports/figures/` (Imagens) e `reports/summaries/` (Textos).

**Ordem de Execução:**

1.  **Gráficos Individuais:**
    ```bash
    python src/analysis/build_personal_graphs.py
    ```
    * *Gera os 5 insights visuais para cada persona.*

2.  **Gráficos Comparativos:**
    ```bash
    python src/analysis/build_cross_graphs.py
    ```
    * *Gera comparações entre as personas.*

3.  **Resumos em Texto:**
    ```bash
    python src/analysis/build_summaries.py
    ```
    * *Escreve a análise estatística em linguagem natural.*

---

## 📂 Checklist Final

Se tudo correu bem, você terá:
1.  **`data/raw/`**: 4 arquivos CSV (Fase 0).
2.  **Spotify App**: 4 Novas Playlists criadas (Fase 1).
3.  **`data/processed/`**: 4 CSVs de análise + 1 Consolidado (Fase 2).
4.  **`reports/figures/`**: Gráficos PNG organizados por persona (Fase 3).