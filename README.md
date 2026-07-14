# Auditoria Algorítmica do Spotify

**Um estudo experimental sobre vieses e recomendação musical em plataformas de streaming.**

Trabalho de Conclusão de Curso — Gestão da Informação (FAGEN)
Universidade Federal de Uberlândia · Uberlândia-MG · 2026
Autor: **Marcos Rodrigues de Oliveira Júnior** · Orientador: **José Eduardo Ferreira Lopes**

---

## Sobre o projeto

Este repositório contém o código, os dados e o texto de uma auditoria de *caixa-preta*
do sistema de recomendação do Spotify. A pergunta central é: a curadoria automatizada
**favorece a diversidade cultural ou homogeneíza o gosto musical**?

A metodologia é a de auditoria por agentes-sonda (*sock puppet audit*, Sandvig et al., 2014):
quatro personas sintéticas com arquétipos contrastantes são construídas em contas reais do
Spotify, e comparam-se os estímulos declarados (*input*) com as recomendações geradas nos
*Daily Mixes* (*output*). Diante da remoção progressiva de campos da *Web API* do Spotify
durante a pesquisa — tratada como meta-evidência da opacidade da plataforma —, os dados
foram enriquecidos com as fontes externas **Last.fm** e **MusicBrainz**.

### Principais achados

- **Conteúdo:** os repertórios de artistas das personas permanecem integralmente disjuntos
  (Jaccard = 0, mais segregados que o acaso, *p* < 0,001).
- **Tema:** há convergência parcial de gêneros entre as personas.
- **Magnitude:** a diversidade converge por **expansão de riqueza de catálogo**, não por
  homogeneização de entropia.
- Confirmam-se um **viés de popularidade** (Daniel, +131% de ouvintes por artista) e um
  **viés de *hit*** dentro da cauda longa (Sofia, +405% de ouvintes por faixa).

> Leitura completa: **[docs/monografia.md](docs/monografia.md)** (texto integral) ·
> **[PDF](docs/TCC/template_tcc_bcc/template.pdf)**.

---

## As quatro personas

| Persona | Arquétipo | Lógica de seleção |
|---------|-----------|-------------------|
| **Beatriz** | *Mainstream* / viral | Ordenação pura por popularidade (grupo de controle) |
| **Daniel** | Lo-fi / funcional | Distribuição orgânica com peso em faixas funcionais |
| **Sofia** | Nicho / *underground* | Discografia profunda, artistas de baixa popularidade |
| **Ricardo** | Nostálgico / legado | Catálogo legado, prioriza lançamentos pré-2000 |

## Métricas

Diversidade e concentração via **Entropia de Shannon**, ***evenness* de Pielou**,
**Coeficiente de Gini**, **Índice Herfindahl-Hirschman (HHI)** e **Índice de Jaccard**,
com tratamento estatístico inferencial (intervalos de confiança por *bootstrap*, teste de
Mann-Whitney, rarefação e teste de permutação).

---

## Estrutura do repositório

```
├── README.md               Este arquivo
├── PIPELINE.md             Ordem de execução detalhada dos scripts (4 fases)
├── requirements.txt        Dependências Python
├── LICENSE                 Licença MIT
├── src/
│   ├── functions.py        Wrapper da API do Spotify (OAuth, paginação, I/O de CSV)
│   ├── collectors/         Constroem as personas nas contas (playlists, likes, follows)
│   ├── analysis/           Coleta de recomendações (extrair_*) e relatórios (build_*)
│   └── utils/              Reset das contas (limpar biblioteca e seguidos)
├── data/                   Dados: raw, inputs, outputs, consolidated
├── reports/                Figuras e sumários: inputs, outputs, comparison
└── docs/
    ├── monografia.md       Texto integral do TCC
    ├── monografia-word.md  Versão do texto para editor de texto
    └── TCC/                Template LaTeX, PDF final e referências
```

## Como executar

```bash
# 1. Ambiente virtual
python -m venv venvtcc
source venvtcc/Scripts/activate     # Windows Git Bash
# venvtcc\Scripts\activate          # Windows cmd

# 2. Dependências
pip install -r requirements.txt

# 3. Credenciais
# Crie um arquivo .env na raiz com as credenciais da API do Spotify
# (uma conta/persona por vez; o login OAuth é feito no navegador).
```

A execução do pipeline é **manual e sequencial**, em quatro fases (reset das contas →
ingestão dos estímulos → coleta das recomendações após 7+ dias → análise e geração de
relatórios). A ordem completa e o papel de cada script estão em **[PIPELINE.md](PIPELINE.md)**.

---

## Uso de Inteligência Artificial

Em conformidade com as diretrizes institucionais, o uso de ferramentas de IA como apoio
instrumental (desenvolvimento e revisão de código, revisão textual e diagramação) está
declarado na monografia. A concepção da pesquisa, a coleta e a análise dos dados e a
interpretação dos resultados são de autoria e responsabilidade do autor.

## Licença

Distribuído sob a licença **MIT**. Veja [LICENSE](LICENSE). O texto acadêmico e os dados
destinam-se a fins de pesquisa; ao reutilizá-los, cite o trabalho.
