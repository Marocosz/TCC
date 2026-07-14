# Ajuste de citações — NBR 10520:2023 (caixa alta → inicial maiúscula)

**Status: A VALIDAR na próxima compilação.** Esta mudança não pôde ser testada
(sem LaTeX na máquina de edição). Ao compilar, confira e, se necessário, reverta
(instruções no fim).

## O que foi feito

Adicionado o arquivo **`abntex2-alf.bst`** nesta pasta (versão da PR #276 do
abnTeX2, que implementa a NBR 10520:2023). O `bibtex` usa o `.bst` da pasta do
projeto **no lugar** do que vem na distribuição (TeX Live/Overleaf), sem precisar
mexer na classe nem no `template.tex`.

## Por que isso, e não uma opção de pacote

- O `abntex2` **oficial ainda não integrou** a NBR 10520:2023 — a PR #276 (a
  implementação completa) está **fechada sem merge**; a issue #260 está aberta há
  ~2 anos. Ou seja, "atualizar o pacote" não resolve: a versão oficial (a sua,
  `v1.9.7`) não tem a norma.
- A caixa alta **não** vem de opção nem de macro do preâmbulo: é o `.bst` que
  grava o sobrenome em CAIXA ALTA dentro do `.bbl`. O TeX não faz *title-case*
  (não converte "BAUER" de volta para "Bauer"), então a correção **tem** de ser
  no `.bst`.
- Este `.bst` muda o default `abnt.cite.style` para `#1` (2023): passa a gravar a
  forma parentética em **caixa mista com ";"** (ex.: `Bauer; Schedl`) e põe
  *et al.* em itálico. Como as opções da classe `facom-ufu-abntex2`
  (`alf, abnt-emphasize=bf, abnt-etal-list=0, abnt-repeated-author-omit=yes`) **não**
  pedem `abnt-cite-style`, o default do `.bst` prevalece — nada sobrescreve.

Resultado esperado: `(THALER; SUNSTEIN, 2008)` → `(Thaler; Sunstein, 2008)`.
As citações textuais (`\citeonline`) já eram em caixa mista e continuam iguais.
A **lista de referências** (regida pela NBR 6023) permanece com sobrenomes em
caixa alta — o professor pediu ajuste só nas citações.

## IMPORTANTE ao compilar

É preciso **rodar o bibtex de novo** para regenerar o `template.bbl` com o novo
`.bst`. No Overleaf: *Menu → Recompile from scratch* (ou apague o `template.bbl`
e o `template.aux` cacheados). Se compilar localmente:
`pdflatex → bibtex → pdflatex → pdflatex`. Só rodar `pdflatex` **não** aplica a
mudança (ele reusaria o `.bbl` antigo, em caixa alta).

## Como verificar

Abra o PDF e confira qualquer citação parentética: deve aparecer
`(Thaler; Sunstein, 2008)`, não `(THALER; SUNSTEIN, 2008)`.

## Como reverter

Apague este `.bst` da pasta:
`docs/TCC/template_tcc_bcc/abntex2-alf.bst` e recompile do zero. O `bibtex`
voltará a usar o `.bst` do sistema (caixa alta).

## Origem

abnTeX2 PR #276 (`nbr10520-2023`), arquivo `bibtex/bst/abntex2/abntex2-alf.bst`.
Apenas este arquivo foi trazido (o mínimo para a norma nas citações); as demais
mudanças da PR — itálico em `\apud`/`Id.`/`Ibid.`, notas de rodapé reduzidas —
não foram incluídas por não terem sido pedidas e por exigirem também o `.sty`.
