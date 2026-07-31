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
