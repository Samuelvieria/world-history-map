# IA.md — Pipeline de extração (livro → eventos no globo)

> Como a "IA" do projeto funciona. Complementa CLAUDE.md e VISUAL.md.
> Decisão: **Solução B — modelos pequenos locais especializados, SEM LLM
> generativo.** Roda local, offline, barato, e não fabrica (só marca trechos).

## Objetivo

Pegar um PDF de livro de história, digeri-lo e cravar cada acontecimento no
globo, na localização certa, com a história resumida. Sempre com **proveniência**
(o trecho-fonte) e **revisão humana** antes de publicar no mapa.

## Restrições que amarram a solução (por ordem de prioridade)

1. **Sem alucinação** (não inventar evento/data/lugar que não está no texto).
2. Rodar **local / offline** se preciso.
3. **Sem depender de API** de terceiro.
4. **Custo baixo** (custo vira hardware + tempo, não request).

Consequência: **LLM generativo NÃO é o núcleo.** O núcleo são modelos *encoder*
que fazem predição de spans — eles etiquetam trechos que existem, não geram texto,
então não conseguem fabricar um fato. (Um LLM local só entraria se essas
restrições fossem relaxadas — ver "Alternativa descartada C".)

## A tarefa quebrada em 8 subtarefas

| # | Subtarefa                                   | Dificuldade | Como resolver             |
|---|---------------------------------------------|-------------|---------------------------|
| 1 | PDF → texto limpo                           | fácil       | PyMuPDF (não é IA)        |
| 2 | Segmentar em frases/parágrafos              | fácil       | spaCy                     |
| 3 | Reconhecer entidades + **tipo de evento**   | médio       | **GLiNER** (zero-shot)    |
| 4 | Ligar num evento estruturado (relação)      | **DIFÍCIL** | GLiNER (relation) + regras|
| 5 | Lugar → coordenada, desambiguando           | **DIFÍCIL** | geoparser/Mordecai3+GeoNames |
| 6 | Normalizar data com incerteza               | médio       | HeidelTime / dateparser   |
| 7 | Resumo sem inventar nem infringir           | médio       | template dos campos       |
| 8 | Revisão humana + proveniência               | processo    | fila de aprovação         |

Passos 1,2,6,7,8 estão resolvidos e não dependem de "IA esperta". A briga é
nos passos **3, 4 e 5**.

## Stack do pipeline (Solução B)

```
PDF
 └─ PyMuPDF ──────────────► texto
     └─ spaCy ────────────► frases/parágrafos
         └─ GLiNER ───────► entidades + tipo de evento + relações
             │              (zero-shot: categorias declaradas em runtime)
             ├─ HeidelTime/dateparser ► data_inicio/fim + incerteza_data
             ├─ geoparser/Mordecai3 + GeoNames(local) ► lat/lng + confianca_local
             └─ template ─► resumo (só usa os campos já extraídos)
                 └─ FILA DE REVISÃO HUMANA ► aprova ► PostGIS ► globo
```

### Peça-chave: GLiNER (passos 3 e 4)

- Modelo encoder pequeno (tipo BERT). NER **zero-shot**: você declara em runtime
  as categorias — ex.: `["batalha", "tratado", "cidade", "pessoa", "data", "obra"]`
  — sem treinar e sem dataset rotulado.
- Roda em **CPU / hardware comum**. Suporta extração de **relação** (passo 4) e
  multi-task, além do NER.
- Faz **predição de spans** (não gera texto) → não fabrica; toda saída aponta pro
  trecho de origem. Em NER zero-shot, supera ChatGPT e LLMs ajustados.
- É multilíngue (usar variante que cubra **português**).
- Repo: https://github.com/urchade/GLiNER

### Peça-chave: geoparsing (passo 5)

- **Mordecai3** — resolve topônimo → GeoNames com ranking neural, desambigua por
  contexto ("Paris, França" vs "Paris, Texas") e faz *event geocoding* (liga o
  evento ao lugar onde ocorre). https://github.com/openeventdata/mordecai
- **geoparser** (alternativa, PyPI) — spaCy p/ reconhecer + SentenceTransformer
  p/ resolver, GeoNames em SQLite local. https://pypi.org/project/geoparser/
- Ambos rodam local com o dump do GeoNames.

### Datas, resumo, busca

- **Datas**: HeidelTime ou dateparser → intervalos com `incerteza_data`
  (exata | ano | decada | seculo | aproximada).
- **Resumo**: **slot-filling por template** a partir dos campos estruturados
  (ex.: "Em {ano}, em {lugar}: {tipo} envolvendo {atores}."). Não copia trecho do
  livro (direito autoral) e não gera texto livre (alucinação). Guardar o trecho
  verbatim só internamente, para proveniência.
- **Busca semântica** ("pesquiso Odesa"): sentence-transformers, local, encoder
  (não gera texto).

## Mapeamento pro modelo de dados (ver CLAUDE.md)

- GLiNER → `titulo`, `categoria`, `atores`, spans de origem em cada campo.
- HeidelTime/dateparser → `data_inicio`, `data_fim`, `incerteza_data`.
- geoparser → `lat`, `lng`, `local_nome_epoca`, `geocoding_fonte`, `confianca_local`.
- template → `resumo`.
- Proveniência (livro/página/trecho) presa a cada campo. **Sem span, o campo não
  existe** e o evento vai pra revisão como incompleto — nunca direto pro mapa.

## Riscos residuais (encarar de frente)

1. **Passo 4 (evento/relação) é o elo mais fraco.** Por isso a revisão humana NÃO
   é opcional — é o componente que segura a qualidade.
2. **Português** derruba a acurácia dos geoparsers prontos (feitos p/ inglês).
   Mitigação: GLiNER multilíngue reconhece, casa no GeoNames; aceitar imprecisão
   e revisar.
3. **Desambiguação histórica** (nomes de época) precisa de WHG/Pleiades por cima
   do GeoNames (fase posterior).

## Alternativas consideradas e descartadas

- **A — só NLP clássico (regras + NER estatístico).** 100% local e sem fabricar,
  mas passos 4/5 ficam fracos e exigem engenharia de regras por livro; recall
  baixo. Bom como fallback simples, fraco como núcleo.
- **C — LLM pequeno local com extração restrita.** Melhor nos passos difíceis e
  em PT, roda local, mas **é LLM generativo** — pode fabricar relação plausível
  mesmo com verificação de span; exige hardware. Só se a regra "sem LLM" for
  relaxada.

## Ordem de implementação

1. GLiNER num parágrafo real → entidades + tipo, no formato do modelo de dados,
   com span preso. (Geocoding como stub no começo.)
2. Datas (HeidelTime/dateparser) + template de resumo.
3. Geoparser + GeoNames local.
4. Fila de revisão + gravação no PostGIS.
5. Depois: WHG/Pleiades para geocodificação histórica.

## Referências

- GLiNER: https://github.com/urchade/GLiNER
- Mordecai3 (geoparser + event geocoder): https://github.com/openeventdata/mordecai
- geoparser (PyPI): https://pypi.org/project/geoparser/
- spaCy: https://spacy.io/
- HeidelTime: https://github.com/HeidelTime/heideltime
- GeoNames (dump): https://www.geonames.org/
- sentence-transformers: https://www.sbert.net/

---

## STATUS — passo 1 implementado e medido

Código em [`ingestao/`](./ingestao/) (ver `ingestao/README.md` para detalhe e
como rodar). Resumo do que a medição real mostrou:

**A premissa central se sustentou.** GLiNER devolve span (`start`/`end`) que
indexa corretamente o texto original, e em nenhum teste marcou entidade que não
estivesse no texto. Proveniência íntegra em 100% dos candidatos gerados. A
escolha por encoder em vez de LLM generativo está validada nesse ponto.

**Números** (gabarito de 4 eventos, `ingestao/amostras/paragrafo_teste.txt`):
local 3/4 · categoria 4/4 · data 4/4 · candidatos completos 4/5.
É **um** parágrafo — indicação de viabilidade, não medida de acurácia.

**Três correções ao que este documento supunha:**

1. O README oficial do GLiNER documenta a saída só como `text`/`label`. Na
   versão 0.2.28 vem também `start`, `end` e `score`. Verificado antes de
   escrever o pipeline (`ingestao/sondar_api.py`), já que tudo depende disso.

2. **Passar muitos rótulos numa chamada só derruba o score ~3x** (competição
   entre rótulos). `"Constantinopla"`: 0.27 com 22 rótulos, 0.77 com 5, 0.84
   com 1. O pipeline faz uma chamada por grupo de rótulos. Achado de maior
   impacto — e não estava previsto aqui.

3. A **escolha do rótulo** pesa mais que o limiar: `ano` pega `1789` a 0.82
   onde `data` pegava a 0.46; `período` pega `2560 a.C.` a 0.54 onde `data`
   pegava a 0.21; `monumento` pega `Grande Pirâmide de Gizé` a 0.78 onde
   `cidade` não pegava nada.

**Risco nº 1 confirmado.** Rótulos de *evento* pontuam muito abaixo dos de
*entidade*: `cerco` sai a 0.39 contra 0.84 de `Constantinopla`, e `batalha`,
`conquista` e `cerco militar` não retornam nada. Daí limiar separado por tipo.
O passo 4 é mesmo o elo fraco — a revisão humana não é formalidade.

**Ainda não feito:** passos 2 (datas normalizadas, spaCy), 5 (geocoding — hoje
stub que devolve `None` de propósito, em vez de chutar coordenada), 8 (fila de
revisão + PostGIS). O agrupamento em eventos é hoje "uma frase = um candidato",
uma heurística explícita, não uma solução do passo 4.

**Requisito de ambiente:** `gliner` exige **Python >= 3.10** — o Python 3.9 que
vem no macOS não serve.

---

## DECISÃO — como resolver o passo 4 (relação/evento)

Reavaliação feita depois da medição, com dois dados que mudam o raciocínio:

**1. Custo deixou de ser argumento.** Um livro de 500 mil caracteres leva
**~16 minutos** (868 parágrafos × 1,08 s, CPU arm64). A ideia de cascata
"filtro barato → modelo caro" não se justifica por economia. Se a cascata
entrar, tem que ser por qualidade.

**2. O gargalo é só o passo 4.** Entidades saem a 0,82–0,93; eventos, a 0,39
ou nada.

**Escolhido: mineração de texto + regras, sem LLM.** Determinístico, auditável
e mantém a restrição "sem LLM generativo". Recall menor que um LLM, mas a
revisão humana já é parte do desenho — e dá pra medir antes de escalar.

O que a mineração contribui, que o GLiNER não dá:

- **Estrutura do livro** — capítulo "A Guerra do Peloponeso" faz todo evento
  ali herdar contexto temporal e geográfico. Ataca o passo 4 diretamente.
- **Índice remissivo** — livro de história costuma ter índice onomástico e
  toponímico: é lista de entidades curada por humano, já no arquivo.
- **Importância por espaço dedicado** — hoje `nivel_importancia` é chute
  subjetivo; nº de menções e páginas dedicadas é proxy auditável.
- **Correferência básica** — "A cidade, hoje chamada Istambul…" gerou um
  candidato espúrio no teste; resolver "a cidade" → Constantinopla elimina
  essa classe de erro.

**Avaliado e descartado por ora — GLiREL** (v1.2.1, zero-shot relation
extraction, encoder). Seria a opção "puro encoder" para o passo 4, mas todos
os modelos no HuggingFace estão com 0 downloads e nenhum declara suporte
multilíngue. Aposta arriscada para português; testar antes de adotar.

---

## STATUS — passo 1 real (PDF) implementado e MEDIDO contra dois livros inteiros

`ingestao/extracao/pdf.py` (PyMuPDF + normalização NFKC) e
`ingestao/ingerir_pdf.py` fecham o passo 1 de verdade — antes o pipeline só
recebia texto já digitado à mão. Rodado contra dois livros reais em
`ingestao/amostras/`: *História Antiga* (Beltrão/Davidson, 270 páginas) e
*História Moderna* (Dauwe, 192 páginas).

**GPU muda a viabilidade do projeto.** Medido sem GPU: ~8s/página (CPU,
4 chamadas GLiNER por página) — um livro de 270 páginas custaria ~3h.
Descobertas duas causas, ambas silenciosas: `pip install` sozinho traz o
torch CPU-only mesmo com GPU NVIDIA na máquina; e `GLiNER.from_pretrained`
tem `map_location='cpu'` como padrão, não detecta CUDA por conta própria.
Com o torch certo (`+cu126`) e `extrator.py` passando `map_location='cuda'`
explicitamente: **~0,45s/página em regime permanente** (~18x mais rápido) —
carregar o modelo na GPU custa ~180s, mas isso é uma vez por processo, não
por página. Os dois livros inteiros (462 páginas úteis): **552s (~9,2 min)**
no total.

**Números reais (não sintéticos) dos dois livros:**

| | História Antiga | História Moderna |
|---|---|---|
| candidatos gerados | 1099 | 954 |
| completos (campos mínimos) | 15 (1,4%) | 13 (1,4%) |
| proveniência íntegra | 1099/1099 (100%) | 954/954 (100%) |
| data normalizada (passo 6) | 168 (15%) | 237 (25%) |
| resumo gerado (passo 7) | 294 (27%) | 265 (28%) |

A garantia central se sustenta em escala: **100% de proveniência íntegra em
2053 candidatos reais** — nenhum span mentiroso. A completude (1,4%) é bem
mais baixa que no parágrafo sintético (4/5 = 80%), confirmando com dado real
o que a seção do passo 4 já esperava: texto de livro de verdade (nota de
rodapé, gabarito de exercício, cabeçalho de página) é muito mais confuso que
um parágrafo escrito a dedo para o teste — a revisão humana (passo 8) não é
opcional aqui, é o que sustenta tudo.

**Exemplos reais que saíram corretos** (conferidos à mão): "Quarta Cruzada",
`batalha`, Constantinopla, 1202 → `1202-01-01`/`ano`. "Pantheon", `cultural`,
"século II d.C." → `0101-01-01..0200-12-31`/`seculo` (intervalo de século
calculado certo em dado real, não só no teste).

**Achado novo, corrigido**: `resumo` começava com letra minúscula quando
tinha local mas não tinha data ("em Europa: RENASCIMENTO." em vez de "Em
Europa: ...") — o ramo com prefixo não passava pela mesma maiusculização do
ramo sem prefixo. Corrigido em `extracao/resumo.py`, com teste de regressão.

**Gap novo, documentado, não corrigido**: "terceiro milênio antes de Cristo"
não normaliza (fica `None`, corretamente — não inventa) porque `datas.py`
não reconhece a unidade "milênio", só ano/década/século/data completa. Comum
em história antiga; próximo a acrescentar no mesmo padrão dos outros
intervalos.

---

## STATUS — passo 8 (fila de revisão) implementado em CLI

`ingestao/revisar.py`: lê o JSON de `ingerir_pdf.py`, mostra cada candidato
pendente com o trecho-fonte por baixo (uso interno de quem revisa — nunca
tela do mapa) e grava aprovação/rejeição de volta a cada resposta, não só no
fim. Testado com decisões simuladas (aprovar/rejeitar/pular/sair) contra o
JSON real da ingestão de *História Antiga* — persistência por decisão
confirmada campo a campo.

Deliberadamente **não** grava no mapa nem converte para `HistoricalEvent`:
falta geocoding real (passo 5, ainda stub — candidato aprovado sem `lat`/
`lng` não tem onde aparecer) e falta o backend/banco da Fase 1 do CLAUDE.md,
que ainda não existe. O script avisa explicitamente quantos aprovados ficam
"presos" sem coordenada, em vez de deixar isso implícito.

---

## STATUS — revisão manual real de 15 candidatos completos, achado sério

Revisão (por mim, como exercício de avaliar `revisar.py` — a aprovação de
verdade continua sendo do humano, não foi gravada no arquivo real) dos 15
candidatos "completos" de *História Antiga* contra o trecho-fonte de cada
um: **3 aprovados, 12 rejeitados (20% de acerto)** — bem abaixo do que
"completo" (tem todos os campos mínimos) sugere à primeira vista. Ter os 4
campos não quer dizer que descrevem um evento de verdade.

**Risco novo, não previsto nas seções anteriores**: citação bibliográfica
"(AUTOR, ANO)" sendo lida como se `ANO` fosse a data do evento — e às vezes
`AUTOR` como ator. 4 das 12 rejeições eram exatamente isso: zigurates "de
1999" (na verdade `CARDOSO, 1999`, a citação do livro-fonte), pirâmides "de
1987" (`KEMP, 1987`), "conquistas militares" "de 1990" (`DONADONI, 1990`),
"guerra" "de 1991" (citação não identificada, mas mesmo padrão). Isso é
sistemático — o rótulo "ano"/"data histórica" do GLiNER não distingue "ano
que aparece dentro de uma referência bibliográfica" de "ano do evento
narrado". Mitigação possível (não implementada, é decisão de design):
detectar por regex o padrão `(PALAVRA, ANO)` e descartar candidato de
data/ator cujo span cai dentro desse parêntese — regra determinística,
mesmo espírito do resto do passo 4.

**Bug encontrado**: quando uma palavra quebra entre duas linhas do PDF
("Reino\nNovo"), o span capturado inclui a quebra de linha literal — o
`valor` sai como `'Reino \nNovo'`, e isso vaza pro `resumo` também. Não
corrigido ainda; precisa de cuidado para não quebrar a invariante de que
`CampoExtraido.valor` bate exatamente com `Proveniencia.trecho` (mudar um
sem o outro corrompe a verificação de integridade).

---

## STATUS — estrutura do livro implementada (passo 4); BERTimbau e HIPE-2026 descartados

`ingestao/extracao/estrutura.py`: implementa o que a seção "O que a
mineração contribui" (acima) já previa e nunca tinha sido construído —
"Estrutura do livro... faz todo evento ali herdar contexto temporal e
geográfico". Detecta cabeçalho de seção por regex sobre linha isolada
(padrão medido nos dois livros de amostra, material didático EAD: "Aula N",
"Módulo N", "UNIDADE N", e rótulos fechados — "Objetivos", "Meta da aula",
"Pré-requisitos", "Resposta Comentada", "Atividade Final", "Dicas",
"Bibliografia" etc.) e classifica em narrativo/não-narrativo. Não deleta
nada — só marca (`secao_titulo`, `secao_narrativa`); `revisar.py` esconde
não-narrativo por padrão (`--incluir-nao-narrativo` reverte).

**Confirmado**: nenhum dos dois PDFs de amostra tem sumário/bookmark
embutido (`doc.get_toc()` devolve 0 em ambos) — a leitura de cabeçalho no
texto plano era mesmo o único caminho, não um atalho por preguiça de
verificar a alternativa mais fácil.

**Bug real encontrado e corrigido**: a primeira versão calculava a seção
pela posição de **início da frase inteira** (`frase.inicio`). Blocos de
exercício sem pontuação interna (ex. "Atividade Final\nLeia o fragmento a
seguir...") virsm UMA frase só para `segmentar_frases`, cujo início cai
antes do próprio cabeçalho — o candidato "pirâmides" (pág. 267, o mesmo
caso `KEMP, 1987` da seção de citação acima) não recebia `secao_titulo`
nenhum por isso. Corrigido: a seção agora é calculada pela posição do CAMPO
ÂNCORA (`titulo`, ou o próximo disponível), não da frase. Medido antes/depois
numa amostra de 15 candidatos completos revisados à mão: passou de 1/15
para os 3/15 esperados pela revisão manual original.

**Pesquisa concluída sobre duas sugestões externas (BERTimbau, HIPE-2026)**:

- **BERTimbau** (BERT-CRF fine-tuned no HAREM): confirmado que é encoder,
  não LLM — compatível com a restrição. Mas **não substitui o GLiNER**:
  exige fine-tuning supervisionado (não é zero-shot), e as categorias do
  HAREM (PESSOA/LOCAL/ORGANIZACAO/TEMPO/VALOR + ACONTECIMENTO no cenário
  Total) não têm a granularidade de evento histórico que o projeto precisa
  ("cerco", "tratado", "cerco militar" como rótulos distintos). F1 real
  medido no paper original: 83,7% (Large) / 83,1% (Base) no cenário
  Selective, 78,5% no Total — não os "83,93%" que uma pesquisa externa
  citou sem fonte primária confirmada. Descartado como substituto; como
  complemento de entidade genérica, o ganho não justificaria manter dois
  modelos.
- **HIPE-2026** (extração de relação pessoa-lugar em texto histórico
  multilíngue, arXiv:2606.25935): **irrelevante para o caso** — cobre
  francês/alemão/inglês, nunca português, em jornais históricos europeus
  (não livros didáticos). Boa parte dos sistemas participantes usa LLM
  generativo via prompting, o que contraria a restrição do projeto. Valor
  residual é só conceitual (a moldura "quem-esteve-onde-quando" é análoga
  ao passo 4), não há dataset/modelo/código reaproveitável.

---

## STATUS — passo 5 (geocoding real) implementado, caminho barato até o globo

Decisão explícita de escopo: em vez de construir a Fase 1 do CLAUDE.md
(FastAPI + PostGIS) agora, `ingestao/publicar.py` faz a ponte mais simples
possível — pega os `status="aprovado"` de `revisar.py`, geocodifica com
Nominatim (`extracao/geocoding.py`, MVP do IA.md, antes stub) e funde direto
em `src/data/events.json`, no formato que o app React já lê. Prova o loop
completo (livro → extração → revisão → mapa) sem banco de dados.

**Achado sério, medido contra os 21 aprovados reais desta sessão**: geocodificar
nome de lugar de época com Nominatim é traiçoeiro além do que "aceitar
imprecisão" já previa. Seis dos catorze primeiros resultados foram pra lugar
homônimo **errado**, não impreciso — "Reino Novo" (Egito) foi pro aeroporto
de uma cidade brasileira chamada Reino; "Quarta Cruzada"/Constantinopla foi
pra uma RUA de mesmo nome em Buenos Aires; "Tratado descritivo do Brasil"
(local extraído "ABC") foi pra sede da rádio australiana ABC; "Bastilha"
(três candidatos, incluindo "Revolução Francesa") foi pra um vilarejo na
Bretanha. Publicado uma vez, revertido do `events.json` antes de virar
achado permanente.

**Duas blindagens adicionadas, ambas medidas contra esse mesmo lote real**:

1. `CONFIANCA_MINIMA = 0.5` sobre o campo `importance` do Nominatim (a única
   confiança que a API gratuita dá — mede o quão proeminente o lugar é
   globalmente, não se a busca achou o lugar certo pra aquele nome). Separou
   limpo os 6 corretos (0,58–0,86) dos piores errados (0,05–0,41) nesta
   amostra.
2. `TAMANHO_MINIMO_NOME_LUGAR = 4` — o caso "ABC" furou o limiar de
   confiança (0,66, alto, porque a rádio australiana é um lugar
   genuinamente proeminente no índice do Nominatim) precisamente por ser uma
   sigla curta e ambígua. Custo aceito: um nome de lugar histórico curto mas
   legítimo (ex. "Ur", 2 letras) também cairia aqui — julgado pior perder um
   acerto raro do que publicar esse tipo de erro.

Resultado final: **6 de 21 aprovados publicados** (Pantheon, Mapa-múndi da
Babilônia, Concílio de Constança, Basílica de São Pedro, Reconquista, Bula
Intercœtera) — testado no app rodando de verdade (busca por "Pantheon",
painel abre com localização, data e resumo corretos, zero erro de console).
Os outros 15 ficam de fora com motivo explícito no relatório do script
(sem data normalizada, geocoding não achou nada, confiança baixa, nome
curto) — nunca silenciosamente.

---

## STATUS — correlação entre fontes implementada ("Validação por consenso")

Implementa a seção "Validação por consenso" do CLAUDE.md, prevista desde o
início e nunca construída: não guardar "a verdade", guardar asserções de
fontes, corroborar quando fontes independentes concordam, **mostrar a
divergência quando discordam em vez de forçar consenso**. Motivada por uma
lacuna real — dois livros diferentes descrevendo o mesmo acontecimento
viravam dois marcadores duplicados no mapa, sem nenhuma ligação.

`extracao/correlacao.py`: pontua pares de candidatos aprovados de fontes
diferentes por similaridade de título (Jaccard de tokens, sem acento/
pontuação/palavras de parada) + local + sobreposição de intervalo de data.
Só pontua — nunca funde sozinho. `correlacionar.py` mostra cada par sugerido
(com divergência de data/local em destaque) e só grava `grupo_correlacao`
compartilhado se um humano confirmar "juntar" — mesma régua de "a IA só
sugere, o humano aprova" que `citacoes.py`/`revisar.py` já seguem.

**Bug real achado escrevendo o teste, corrigido antes de virar problema em
produção**: comparar as strings de data ISO direto com `<=` parecia certo
(a.C. sempre começa com `-`, que ordena antes de d.C. por acidente feliz) mas
dava overlap ERRADO entre duas datas a.C. de magnitude diferente —
`"-2998-01-01"` (2999 a.C.) comparava como *menor* que `"-0499-01-01"` (500
a.C.) por causa do dígito seguinte, o oposto da ordem cronológica real (500
a.C. é mais recente). Corrigido convertendo pra tupla de inteiros
`(ano, mes, dia)` antes de comparar.

`publicar.py` agora agrupa aprovados por `grupo_correlacao` antes de
converter: um grupo de 2+ fontes vira **um** evento, com título/categoria/
local do membro de maior confiança, atores como **união** de todos os
membros, e a data normalizada de **maior precisão** entre os membros que
resolveram data. Corroboração por 2+ fontes ganha **+1 na importância**
(min. 5) — sinal real de relevância histórica, não inventado. Quando os
membros do grupo divergem em data ou local, o resumo publicado inclui a
divergência por extenso.

**Medido**: os dois livros de amostra não se sobrepõem tematicamente
(História Antiga = Mesopotâmia/Egito; História Moderna = Renascimento em
diante) — `correlacionar.py` contra os dois corretamente não sugere NENHUM
par (verdadeiro negativo, não falta de teste). A fusão foi comprovada de
ponta a ponta com um par sintético construído a mão ("Queda de
Constantinopla" em duas fontes fictícias, com data e atores levemente
diferentes): resumo saiu com "corroborado por 2 fontes", a divergência de
data apareceu por extenso, a data mais precisa (exata, não "ano") foi a
publicada, e os atores das duas fontes saíram unidos sem duplicar.

**Limitação conhecida, documentada**: com 3+ arquivos a correlação é só par
a par, sem fechamento transitivo (A~B confirmado pode não oferecer A~C ou
B~C mesmo que C descreva o mesmo evento) — não é problema com os 2 livros de
hoje, mas relevante se um terceiro entrar.

**Se um dia a regra "sem LLM" for relaxada**, a forma segura é o LLM receber
apenas os spans já ancorados e devolver **IDs de span**, com validação
rejeitando ID inexistente. Isso torna a alucinação de *fato* estruturalmente
impossível; sobra o erro de *agrupamento*, que é visível na revisão e não
corrompe a proveniência. É uma diferença de natureza, não de grau.

---

## STATUS — passo 2 implementado (data normalizada + resumo), MEDIDO

Código em `ingestao/extracao/datas.py` e `ingestao/extracao/resumo.py`,
encaixado no fim de `ExtratorGLiNER.extrair()`. Detalhe em
[`ingestao/README.md`](./ingestao/README.md#passo-2--normalização-de-data-e-resumo-novo).

**Mudança de plano em relação a este documento**: passo 2 usa **regex +
regras**, não HeidelTime nem `dateparser` como o texto acima sugeria.
Motivo — o formato que mais aparece em história em português (ano a.C., ex.
"2560 a.C.") não é bem coberto por nenhuma das duas: `dateparser` não modela
esse conceito, e HeidelTime é dependência Java pesada para cobrir só cinco
formatos de data (dia+mês+ano, mês+ano, ano isolado, década, século — com ou
sem marcador de aproximação). Mesma lógica do passo 4: regra determinística
e auditável em vez de biblioteca genérica, quando o problema real é estreito.

Anos a.C. usam numeração astronômica ISO 8601 (ano 1 a.C. = astronômico `0`),
para preservar ordem cronológica em comparação direta de string sem inventar
uma convenção própria. O resumo é slot-filling puro sobre campos já
extraídos — nunca gera texto livre, nunca copia o trecho-fonte.

**Medido depois da instalação do Python** (venv + `pip install -r
requirements.txt` + `COM_MODELO=1 python -m unittest testes`, 35/35 testes
passando, incluindo os dois de integração que baixam o GLiNER de verdade; e
`python spike_passo1.py` contra o parágrafo de teste): local 3/4, categoria
4/4, data bruta 4/4 — **idêntico ao passo 1**, nada regrediu — e **data
normalizada em 4/5 candidatos**. Os quatro normalizaram como o desenho
previa, inclusive o caso mais delicado: `"2560 a.C."` (com "por volta de" na
frase mas fora do span da entidade) saiu com `incerteza_data="aproximada"`,
confirmando que buscar o marcador de aproximação numa janela de contexto ao
redor do span — e não só dentro dele — funciona. Detalhe em
[`ingestao/README.md`](./ingestao/README.md#passo-2--normalização-de-data-e-resumo-novo).

**Achado não previsto**: o `resumo` fica redundante quando `titulo` e
`local_nome_epoca` apontam pro mesmo span (ex.: repete "Grande Pirâmide de
Gizé" duas vezes). Não é alucinação — o template só está mostrando fielmente
que dois campos do candidato coincidem — mas é cosmético a corrigir quando o
passo 4 evoluir.

---

## STATUS — gazetteer local pro passo 5, mundo com prioridade sobre Brasil

Motivado pelo achado da seção anterior sobre passo 5 (Nominatim resolvendo
homônimo com confiança alta): `extracao/gazetteer.py` adiciona uma camada
local, checada ANTES do Nominatim em `geocoding.resolver()` — exact match
normalizado (sem acento/caixa) contra dois CSVs em `ingestao/dados/`, nunca
fuzzy-match, `None` se não achar em nenhum dos dois.

Os dois CSVs foram lidos direto dos arquivos originais do usuário (`.xls` do
IBGE, `.csv` das cidades mundiais curadas) — não por transcrição manual no
chat, depois que uma tentativa anterior de transcrever à mão introduziu um
erro real (código IBGE duplicado entre dois municípios diferentes) e cobria
só uma fração pequena dos dados (16 de 27 unidades federativas do Brasil,
Afeganistão–Bahamas do mundo). Cobertura final: **5565 municípios** (100% do
Brasil) e **1033 cidades curadas de 195 países**.

**Achado real, medido contra os 191 locais únicos das duas amostras já
aprovadas**: com os dois CSVs completos, **30 nomes colidem** entre um
município brasileiro e uma cidade mundial curada — Alexandria, Barcelona,
Braga, Buenos Aires, Coimbra, Colombo, Nantes, Porto, Rosário, Santa Fé,
Santiago, Toledo, Valparaíso, entre outras (muitas são cidades brasileiras
batizadas em homenagem à cidade mundial, herança da colonização portuguesa).
Em **nenhuma** das colisões medidas o lado brasileiro era a resposta certa
para o corpus atual (história antiga/moderna, não história regional do
Brasil) — o design original (Brasil antes do mundo, pra resolver "Belém" =
Pará em vez de Belém bíblica) foi invertido com base nessa medição: **mundo
checado antes de Brasil**. Onde os dois lados dão a mesma cidade (Brasília,
Recife, Salvador, São Paulo — que também entraram na curadoria mundial por
relevância histórica própria), a ordem não importa.

Hit rate contra as 191 localizações: só 14 resolvem pelo gazetteer hoje
(Ankara, Atenas, Cairo, Paris, Veneza, Santiago de Compostela e outras) — os
outros 177 caem pro Nominatim, porque a maioria dos locais extraídos de
livros de história antiga/moderna são nomes do mundo antigo (Uruk, Mênfis,
Nínive, Mesopotâmia) que uma lista de cidades *modernas* por país não cobre
e nunca vai cobrir sem uma fonte de nomes de época (WHG/Pleiades, item 5 do
roadmap original).

**Gap residual, documentado, não resolvido**: o CSV mundial lista cidades
DENTRO de um país, não o país como linha própria. Uma referência solta a um
país ("Malta", "Cabo Verde") ou um termo genérico que colide por acaso com
nome de município ("Novo Mundo") ainda resolve errado pro Brasil, porque não
há entrada mundial concorrendo. Fica como candidato pra revisão humana
corrigir — a mesma régua de "IA só sugere, humano aprova" que sustenta o
resto do pipeline.
