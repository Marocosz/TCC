```
# ==============================================================================
# PIPELINE DE DADOS: AUDITORIA ALGORÍTMICA SPOTIFY (PERSONAS SINTÉTICAS)
# ==============================================================================
# Este documento descreve o fluxo lógico e a ordem de execução dos scripts 
# para garantir o rigor metodológico da auditoria de "Caixa-Preta".

---

### FASE 1: SETUP E HIGIENIZAÇÃO (TABULA RASA)
Antes de qualquer coleta, é vital garantir que a conta esteja "neutra" (Cold Start). 
Resíduos de interações passadas invalidariam a auditoria por contaminação de dados.

1.  **src/utils/clear_library.py**: 
    - O que faz: Remove todos os "Likes" da biblioteca.
    - Por que agora: Garante que o histórico de músicas salvas esteja zerado.
2.  **src/utils/clear_follows.py**: 
    - O que faz: Deixa de seguir todos os artistas.
    - Por que agora: Limpa as conexões explícitas que a IA usa para o "Radar de Novidades".

---

### FASE 2: ALIMENTAÇÃO E INGESTÃO (TRAINING INPUT)
Aqui construímos a identidade da Persona. É a fase onde injetamos os dados que 
queremos que a IA processe.

3.  **src/analysis/build_persona_raw_data.py**: 
    - O que faz: Minera as "Playlists Sementes" (URLs) e extrai metadados dos artistas.
    - Função no fluxo: Define a "matéria-prima" que compõe o gosto de cada perfil.
4.  **src/collectors/create_[persona]_playlist.py**: 
    - O que faz: Cria a playlist oficial na conta e adiciona as músicas (Meta: 200 faixas).
    - Função no fluxo: É o "Input" principal. É o que a conta vai efetivamente "consumir".
5.  **src/collectors/sync_persona_follows.py**: 
    - O que faz: Segue os artistas principais daquelas 200 músicas.
    - Função no fluxo: Força o algoritmo de Filtragem Colaborativa e NLP a consolidar o perfil.

*Nota: Após esta fase, ocorre o período de "Treinamento Passivo" (Escuta/Rádios).*

---

### FASE 3: EXTRAÇÃO DE AUDITORIA (DATA COLLECTION)
Após o sistema "aprender" o perfil, extraímos o que ele gerou como recomendação.

6.  **src/analysis/extrair_dados_playlist.py**: 
    - O que faz: Baixa as playlists geradas pela IA (Descobertas da Semana, Daily Mix).
    - Função no fluxo: Coleta o "Output" da caixa-preta para comparação.
7.  **src/analysis/extrair_dados_artistas_seguidos.py**: 
    - O que faz: Extrai metadados detalhados de todos os artistas que a persona segue.
    - Função no fluxo: Cria a linha de base (Baseline) estatística da persona.

---

### FASE 4: PROCESSAMENTO E INSIGHTS (REPORTING)
Transformação de dados brutos em informação acadêmica.

8.  **src/analysis/merge_datasets.py**: 
    - O que faz: Consolida os CSVs individuais em um único dataset de análise.
9.  **src/analysis/build_summaries.py**: 
    - O que faz: Gera os arquivos .txt em `reports/summaries/`.
    - Resultado: "Fichas técnicas" com médias de popularidade e era musical.
10. **src/analysis/build_personal_graphs.py**: 
    - O que faz: Gera os gráficos individuais (Insight 1 a 5) em `reports/figures/[persona]/`.
11. **src/analysis/build_cross_graphs.py**: 
    - O que faz: Gera visualizações comparativas em `reports/figures/cross/`.
    - Resultado: Gráficos que mostram as diferenças de comportamento entre Beatriz, Daniel, Ricardo e Sofia.

---