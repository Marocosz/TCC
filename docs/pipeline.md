# 📘 Guia de Execução do Pipeline de Dados - TCC

Este documento descreve a ordem lógica e cronológica de execução dos scripts do projeto. Siga este fluxo para garantir que os dados sejam gerados, processados e analisados corretamente, evitando erros de dependência.

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
3.  **Credenciais:** O arquivo `.env` (na raiz) contenha suas credenciais do Spotify (`SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, `SPOTIPY_REDIRECT_URI`).

---

## 🔄 Fluxo de Execução

O pipeline é dividido em **3 Fases**: Coleta, Processamento e Análise.

### 🟢 FASE 1: Coleta e Criação de Playlists (Collectors)
**Objetivo:** Ler os arquivos CSV brutos (`data/raw/`) e interagir com a API do Spotify para criar as playlists reais na sua conta.

**Arquivos de Entrada:** `data/raw/*.csv`
**Arquivos de Saída:** Criação de playlists na conta do Spotify.

**Ordem de Execução:**
Execute os scripts abaixo (a ordem entre eles não importa, mas todos devem ser rodados):

1.  `python src/collectors/create_beatriz_playlist.py`
    * *Gera a playlist "Top Hits Brasil" baseada em popularidade.*
2.  `python src/collectors/create_daniel_playlist.py`
    * *Gera a playlist "Lofi Flow" com aleatoriedade.*
3.  `python src/collectors/create_ricardo_playlist.py`
    * *Gera a playlist "Rock & MPB 90s" com estratificação.*
4.  `python src/collectors/create_sofia_playlist.py`
    * *Gera a playlist "Alternativa Pura" com lógica ponderada.*

---

### 🟡 FASE 2: Extração e Processamento de Dados (Analysis - ETL)
**Objetivo:** Baixar os dados técnicos (áudio features, popularidade, gêneros) das playlists recém-criadas e salvar em CSVs locais para análise.

**Arquivos de Entrada:** Playlists na nuvem (Spotify).
**Arquivos de Saída:** `data/processed/analise_{Persona}_playlist.csv`.

**Ordem de Execução:**

1.  **Extração Individual:**
    `python src/analysis/extrair_dados_playlist.py`
    * *Este script varre as playlists criadas na Fase 1 e salva os dados detalhados na pasta `data/processed`.*

2.  **Consolidação (Merge):**
    `python src/analysis/merge_datasets.py`
    * *Lê todos os CSVs individuais gerados acima e cria um arquivo unificado (ex: `analise_consolidada_input.csv`) necessário para os gráficos comparativos.*

---

### 🔴 FASE 3: Visualização e Relatórios (Visualization & Reports)
**Objetivo:** Ler os dados processados e gerar os gráficos (png) e resumos de texto (txt).

**Arquivos de Entrada:** `data/processed/*.csv`.
**Arquivos de Saída:** Imagens em `reports/figures/` e textos em `reports/summaries/`.

**Ordem de Execução:**

1.  **Gráficos Individuais (Por Persona):**
    `python src/analysis/build_personal_graphs.py`
    * *Gera os 5 insights visuais (Popularidade, Gêneros, Era, etc.) dentro da pasta de cada persona em `reports/figures/`.*

2.  **Gráficos Comparativos (Cruzamento):**
    `python src/analysis/build_cross_graphs.py`
    * *Gera gráficos que comparam as personas entre si (ex: Boxplot de popularidade Beatriz vs Sofia).*

3.  **Geração de Resumos (Texto):**
    `python src/analysis/build_summaries.py`
    * *Analisa estatisticamente os CSVs e gera os arquivos `resumo_playlist.txt` em `reports/summaries/`, explicando os dados em linguagem natural.*

---

## 📂 Resumo da Estrutura de Saída

Após rodar todo o pipeline, verifique se os resultados estão nos locais corretos:

* **Dados para tabelas:** `data/processed/` (CSVs finais).
* **Imagens para o TCC:** `reports/figures/{persona}/` (PNGs).
* **Dados para o texto do TCC:** `reports/summaries/{persona}/` (TXTs).

## ⚠️ Notas Importantes
* **`src/functions.py`**: Este é um arquivo de utilitários. **Não deve ser executado diretamente**. Ele é importado pelos outros scripts.
* **`build_persona_raw_data.py`**: Parece ser um script auxiliar para preparar dados brutos. Se ele for necessário, execute-o **antes** da Fase 1, mas pela estrutura atual, parece que os dados raw já estão presentes em `data/raw`.