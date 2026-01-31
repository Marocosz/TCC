# Documentação Técnica: Algoritmo de Geração de Playlist Estruturada (Lógica 80/80/40)

Este documento detalha o funcionamento, as regras de negócio e a lógica matemática implementada no script de geração de playlists para as Personas do TCC. O objetivo desta arquitetura é simular um comportamento humano verossímil, equilibrando **obsessão por artistas favoritos**, **consumo de rádio/hits** e **descoberta musical**.

---

## 1. Visão Geral da Arquitetura
Diferente de scripts lineares que apenas coletam as 200 músicas mais populares de uma lista, este algoritmo utiliza uma abordagem **estratificada em 3 camadas (Tiers)**.

### O Problema Resolvido
Evita-se dois extremos indesejados na auditoria algorítmica:
1.  **O "Robô":** Playlist com exatas 2 músicas de cada artista (artificial demais).
2.  **O "Fanático":** Playlist dominada por 20 músicas de um único artista (vício de perfil).

### A Solução: Distribuição Estocástica Controlada
O algoritmo garante totais fixos por etapa, mas a distribuição interna entre os artistas é aleatória dentro de limites pré-definidos (Min/Max).

---

## 2. Detalhamento das Etapas (Stages)

O script constrói a playlist final de **200 músicas** através de um fluxo sequencial e excludente (uma música selecionada na Etapa 1 não pode aparecer na Etapa 2).

### 🔹 Etapa 1: A Elite (Top 10 Artistas)
Representa os artistas favoritos da Persona, aqueles que ela escuta com profundidade (discografia).
* **Alvo:** Artistas ranqueados de 1º a 10º em popularidade no dataset.
* **Volume Total:** 80 músicas.
* **Regra de Cota:** Cada artista contribui com **mínimo de 5** e **máximo de 10** músicas.
* **Seleção:** Prioriza as *Top Tracks* absolutas de cada artista.

### 🔹 Etapa 2: O Mainstream (Top 11-20 Artistas)
Representa os artistas que a Persona gosta e ouve frequentemente (ex: no rádio ou playlists editoriais), mas sem a profundidade de fã.
* **Alvo:** Artistas ranqueados de 11º a 20º em popularidade.
* **Volume Total:** 80 músicas.
* **Regra de Cota:** Cada artista contribui com **mínimo de 3** e **máximo de 10** músicas.
* **Seleção:** Prioriza as *Top Tracks*, excluindo qualquer faixa já usada na Etapa 1 (caso haja feat/colaboração).

### 🔹 Etapa 3: A Cauda Longa (Diversidade Global)
Representa a descoberta musical, os "One-Hit Wonders" e a variedade.
* **Alvo:** Artistas do 21º em diante (analisa um pool dos próximos 100 artistas).
* **Volume Total:** 40 músicas (mais eventuais déficits das etapas anteriores).
* **Regra de Cota:** **Sem limite por artista**.
* **Seleção:** O algoritmo coleta todas as músicas desse pool gigante, ordena todas pela popularidade da **FAIXA** (não do artista) e seleciona as 40 melhores. Isso garante que entrem apenas hits de alta qualidade, independentemente de quem canta.

---

## 3. Mecanismos Técnicos Críticos

### 3.1. Função `distribuir_cotas()`
Este é o cérebro matemático do script. Ele resolve o problema de: *"Como distribuir 80 músicas entre 10 artistas, onde cada um deve ter entre 5 e 10, de forma que a soma seja exata e a distribuição pareça aleatória?"*

**Lógica:**
1.  **Alocação Mínima:** Primeiro, entrega o mínimo (ex: 5) para todos. (10 artistas * 5 = 50 músicas alocadas).
2.  **Saldo Restante:** Calcula quanto falta para chegar no total (80 - 50 = 30 músicas restantes).
3.  **Distribuição Randômica:** Sorteia um artista aleatoriamente. Se ele ainda não atingiu o máximo (10), entrega +1 música. Repete o sorteio até zerar o saldo.

### 3.2. Deduplicação Global (`seen_uris`)
Uma variável do tipo `set()` (conjunto) armazena os URIs de todas as faixas adicionadas.
* Antes de adicionar qualquer música em qualquer etapa, o script verifica: `if uri not in seen_uris`.
* Isso impede que uma música apareça duas vezes (comum em álbuns "Deluxe" ou coletâneas).

### 3.3. Compensação de Déficit (Fail-Safe)
O script é à prova de falhas de catálogo.
* **Cenário:** A Etapa 1 exige 5 músicas de um artista, mas ele só tem 3 singles lançados no Spotify.
* **Ação:** O script pega as 3 disponíveis e registra um "Déficit" de 2.
* **Resolução:** Esse déficit é somado automaticamente à meta da **Etapa 3**. Se faltaram 2 músicas na Etapa 1, a Etapa 3 buscará 42 músicas em vez de 40, garantindo que a playlist final tenha sempre **200 faixas**.

---

## 4. Variáveis de Configuração (`CONFIG`)

O script foi desenhado para ser modular. O dicionário `CONFIG` no início do arquivo permite ajustar o comportamento sem reescrever a lógica:

```python
CONFIG = {
    "CSV_PATH": "Caminho do arquivo de dados brutos",
    "PLAYLIST_NAME": "Nome da playlist a ser criada",
    
    "STAGE_1": {
        "total_tracks": 80,         # Meta de músicas da etapa
        "artist_range": (0, 10),    # Índices dos artistas no CSV (0 a 9)
        "tracks_per_artist": (5, 10)# Min/Max de músicas por artista
    },
    # ... configurações similares para Stage 2 e 3
}
```

## 5. Fluxo de Dados (I/O)

1.  **Input:** Lê o arquivo `.csv` gerado pelo `build_persona_raw_data.py`.
2.  **Processamento:**
    * Ordena artistas por popularidade.
    * Executa Etapa 1 -> Etapa 2 -> Etapa 3.
    * Gerencia saldo e deduplicação em memória.
3.  **Output 1 (Playlist):** Cria a playlist na conta do Spotify e adiciona as faixas.
4.  **Output 2 (Likes):** Executa a função `like_tracks_slowly` para curtir as faixas, simulando interação humana e evitando bloqueio de API (Rate Limiting).

---

## 6. Conclusão Acadêmica
Esta estrutura permite defender na metodologia do TCC que a **Persona Sintética** possui um **Grau de Fidelidade (Fidelity Score)** superior a bots simples, pois mimetiza a distribuição de Pareto (Lei 80/20) observada no consumo cultural humano: a maior parte do consumo concentra-se em poucos artistas favoritos, enquanto uma cauda longa garante a diversidade.