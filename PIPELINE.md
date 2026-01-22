# Pipeline de Execução: Auditoria Algorítmica Spotify

Este pipeline descreve a ordem lógica e técnica de execução dos scripts para a realização da auditoria de "caixa-preta". O fluxo garante a neutralidade inicial da conta, a ingestão controlada de dados e a extração fidedigna dos resultados para análise acadêmica.

---

## 📋 Pré-requisitos Fundamentais (Geral)
Antes de executar qualquer script das Fases 1, 2 ou 3, atente-se aos seguintes pontos:
1. **Autenticação Ativa:** Você deve estar logado no navegador padrão na **Conta da Persona específica** (Beatriz, Daniel, Ricardo ou Sofia) que deseja manipular. O Spotipy abrirá uma janela de navegador para validar o Token OAuth na primeira execução de cada sessão.
2. **Dashboard de Desenvolvedor:** As chaves `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET` e `SPOTIPY_REDIRECT_URI` devem estar corretamente configuradas no arquivo `.env` na raiz do projeto.
3. **Dependências:** O ambiente virtual (`venvtcc`) deve estar ativado e com as bibliotecas `spotipy`, `pandas`, `seaborn` e `python-dotenv` instaladas.

---

## Fase 1: Setup e Higienização (Tabula Rasa)
**Objetivo:** Eliminar qualquer rastro de uso anterior da conta para evitar contaminação de dados (Cold Start Control).

### 1. `src/utils/clear_library.py`
- **Ação:** Remove todas as músicas da biblioteca "Músicas Curtidas".
- **Entrada:** Interação manual via terminal (Confirmação 'SIM') + Conexão com API.
- **Saída:** Limpeza total da seção "Músicas Curtidas" da conta logada.
- **Requisito:** Estar logado na conta da Persona que será resetada.

### 2. `src/utils/clear_follows.py`
- **Ação:** Deixa de seguir todos os artistas na conta.
- **Entrada:** Interação manual via terminal (Confirmação 'SIM') + Conexão com API via Cursor.
- **Saída:** Zera a contagem de "Seguindo" na conta logada.

---

## Fase 2: Alimentação e Ingestão (Training Input)
**Objetivo:** Construir a identidade musical da Persona Sintética e fornecer os dados de treino para a IA do Spotify.

### 3. `src/analysis/build_persona_raw_data.py`
- **Ação:** Minera metadados de artistas a partir de playlists semente para definir o perfil.
- **Entrada:** URLs de playlists curadas definidas no dicionário `PERSONAS`.
- **Saída:** Arquivos CSV em `data/raw/` (ex: `artistas_indie_dados.csv`).
- **Requisito:** Acesso à Internet (Usa *Client Credentials* - não requer login de usuário).

### 4. `src/collectors/create_[persona]_playlist.py`
- **Ação:** Injeta a carga de músicas de acordo com a lógica de cada persona para termos a melhor playlist curtida que represente suas personalidades.
- **Entrada:** Arquivos CSV de `data/raw/`.
- **Saída:** Criação de uma Playlist física no Spotify + "Likes" em massa (ex: 100 ou 200 músicas) na conta logada.
- **Requisito:** Estar logado na conta correta da Persona no navegador.

### 5. `src/collectors/sync_persona_follows.py`
- **Ação:** Segue os artistas principais de cada faixa curtida (Geração de feedback explícito).
- **Entrada:** Lista de "Músicas Curtidas" da própria conta (API `current_user_saved_tracks`).
- **Saída:** Atualização da lista de artistas seguidos no perfil do Spotify.
- **Requisito:** Executar somente **após** o script anterior ter populado as curtidas.



---

## Fase 3: Extração de Auditoria (Data Collection)
**Objetivo:** Coletar o "Output" gerado pelo sistema de recomendação após o período de treinamento.

### 6. `src/analysis/extrair_dados_playlist.py`
- **Ação:** Baixa o conteúdo das playlists geradas pela IA (Descobertas da Semana, Daily Mix, etc).
- **Entrada:** URL da playlist gerada pelo Spotify para a Persona (configurada no script).
- **Saída:** Datasets processados em `data/processed/` (ex: `dataset_Sofia_playlist.csv`).
- **Requisito:** A playlist alvo deve estar visível/disponível na conta da Persona.

### 7. `src/analysis/extrair_dados_artistas_seguidos.py`
- **Ação:** Extrai metadados detalhados de todos os artistas que a conta passou a seguir.
- **Entrada:** URLs das playlists semente (reutilizadas para identificar os IDs dos artistas originais).
- **Saída:** Datasets de baseline em `data/processed/` (ex: `dataset_Sofia_artistas_seguidos.csv`).

---

## Fase 4: Processamento e Insights (Reporting)
**Objetivo:** Transformar os dados brutos em relatórios estatísticos e visualizações gráficas para o TCC.

### 8. `src/analysis/merge_datasets.py`
- **Ação:** Consolida os dados de entrada (Input) e saída (Output) em um dataset unificado.
- **Entrada:** Todos os arquivos CSV individuais da pasta `data/processed/`.
- **Saída:** Arquivo mestre `data/processed/dataset_consolidada_input.csv`.

### 9. `src/analysis/build_summaries.py`
- **Ação:** Gera resumos estatísticos textuais (.txt) em `reports/summaries/`.
- **Entrada:** Arquivos CSV processados de cada persona em `data/processed/`.
- **Saída:** Relatórios `.txt` contendo médias de popularidade, gêneros e métricas temporais.

### 10. `src/analysis/build_personal_graphs.py`
- **Ação:** Gera os 5 insights gráficos individuais para cada persona.
- **Entrada:** CSV individual de cada persona em `data/processed/`.
- **Saída:** 5 arquivos PNG por persona em `reports/figures/[persona]/`.

### 11. `src/analysis/build_cross_graphs.py`
- **Ação:** Gera gráficos comparativos cruzando os dados das 4 personas.
- **Entrada:** O dataset consolidado `dataset_consolidada_input.csv`.
- **Saída:** Gráficos comparativos (Boxplots, Violin plots, Scatter plots) em `reports/figures/cross/`.



---

## 🛠️ Resumo de Fluxo de I/O (Input/Output)

| Script | Entrada (Input) | Saída (Output) |
| :--- | :--- | :--- |
| **build_persona_raw_data** | URL Playlist Semente (Spotify) | CSV (data/raw) |
| **create_[persona]_playlist** | CSV (data/raw) | Playlist + Likes (Spotify Account) |
| **sync_persona_follows** | Likes (Spotify Account) | Follows (Spotify Account) |
| **extrair_dados_playlist** | URL Playlist Resultante (Spotify) | CSV (data/processed) |
| **extrair_dados_artistas_seguidos** | IDs de Artistas (Spotify API) | CSV (data/processed) |
| **merge_datasets** | CSVs individuais (Processed) | CSV Consolidado (Processed) |
| **build_summaries** | CSVs (Processed) | Relatórios TXT (reports/summaries) |
| **build_personal_graphs** | CSVs (Processed) | PNGs (reports/figures/[persona]) |
| **build_cross_graphs** | CSV Consolidado (Processed) | PNGs (reports/figures/cross) |

---
**Observação Final:** O sucesso da auditoria depende do intervalo entre a **Fase 2** e a **Fase 3**. Recomenda-se um intervalo mínimo de 7 dias com interações diárias (escuta de rádio de artistas) para que o Spotify processe os dados e gere as playlists de recomendação.