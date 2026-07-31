# ingestao — passo 1 do IA.md

Spike do primeiro passo do pipeline: **texto em português → entidades tipadas
com span → `EventoCandidato`**, sem LLM generativo e sem geocoding (stub).

Nada aqui escreve no mapa. A saída é uma lista de *candidatos pendentes de
revisão humana*, por construção (ver "Decisões" abaixo).

## Rodar

Exige Python >= 3.10 (exigência do `gliner`; o Python 3.9 do sistema não serve).

```bash
python3.12 -m venv .venv
./.venv/bin/pip install -r requirements.txt

./.venv/bin/python spike_passo1.py    # extrai e mede contra gabarito
./.venv/bin/python calibrar.py        # diagnóstico de limiar vs rótulo
./.venv/bin/python sondar_api.py      # verifica o formato de saída do GLiNER

./.venv/bin/python -m unittest testes             # rápido, sem modelo
COM_MODELO=1 ./.venv/bin/python -m unittest testes  # inclui integração
```

Primeira execução baixa `urchade/gliner_multi-v2.1` (**1,16 GB**, licença
Apache-2.0) para o cache do HuggingFace. O venv ocupa ~940 MB.

## Resultado medido

Contra o gabarito de `amostras/paragrafo_teste.txt` (4 eventos conhecidos):

| Campo     | Antes da calibração | Depois |
| --------- | ------------------- | ------ |
| local     | 3/4                 | 3/4    |
| categoria | 2/4                 | **4/4** |
| data      | 2/4                 | **4/4** |
| candidatos completos | 1/5      | **4/5** |

Ressalva importante: isso é **um** parágrafo, escrito por nós. É indicação de
viabilidade, não medida de acurácia. Um número honesto exige um conjunto de
avaliação de verdade, com texto que ninguém escolheu a dedo.

## O que foi aprendido medindo (e não estava no IA.md)

1. **O README do GLiNER é incompleto.** Documenta a saída como `text` e
   `label`; na prática (0.2.28) vem também `start`, `end` e `score`. Como toda
   a proveniência depende do span, isso foi verificado antes de qualquer
   código — ver `sondar_api.py`. Os spans conferem contra o texto original.

2. **Passar muitos rótulos numa chamada só derruba o score ~3x.** Os rótulos
   competem pelo mesmo span. No parágrafo de teste, `"Constantinopla"` sai a
   **0.27 com 22 rótulos**, **0.77 com 5** e **0.84 com 1**. Com limiar 0.5,
   a versão de 22 rótulos perdia *todos* os locais e datas. Por isso o
   extrator faz **uma chamada por grupo** de rótulos (4 no total): mais lento,
   muito melhor. Este foi o achado de maior impacto.

3. **A escolha do rótulo importa mais que o limiar.** Medido em `calibrar.py`:

   | Rótulo    | Trecho                    | Score |
   | --------- | ------------------------- | ----- |
   | `cidade`  | `Grande Pirâmide de Gizé` | não pega |
   | `lugar`   | `Grande Pirâmide de Gizé` | 0.59  |
   | `monumento` | `Grande Pirâmide de Gizé` | 0.78 |
   | `data`    | `1789`                    | 0.46  |
   | `ano`     | `1789`                    | 0.82  |
   | `data`    | `2560 a.C.`               | 0.21  |
   | `período` | `2560 a.C.`               | 0.54  |

   Baixar o limiar é a saída errada: em 0.1 o modelo chega a rotular
   `Grande Pirâmide de Gizé` como `epidemia` (0.11).

4. **O risco nº 1 do IA.md se confirmou.** Rótulos de *evento* pontuam muito
   abaixo dos de *entidade* neste modelo: `"cerco"` sai a 0.39, enquanto
   `"Constantinopla"` sai a 0.84 — e `"batalha"`, `"conquista"` e
   `"cerco militar"` não retornam **nada**. Daí o limiar separado por tipo
   (0.3 para evento, 0.5 para entidade). O passo 4 (relação) é mesmo o elo
   fraco, e é o que sustenta a revisão humana como obrigatória.

## Limitações conhecidas

- **Agrupamento por frase é heurística, não solução do passo 4.** "A cidade,
  hoje chamada Istambul, tornou-se a capital otomana" vira um candidato
  separado, quando é continuação do evento anterior. Um dos 5 candidatos do
  parágrafo de teste é espúrio por isso.
- **Local específico vs cidade.** Em "a tomada da Bastilha em Paris", o
  extrator escolhe `Bastilha` (monumento, 0.77) sobre `Paris` (lugar, 0.73).
  Não é erro — a Bastilha é o local do evento — mas o modelo de dados hoje tem
  um campo só. Para geocoding (passo 5), a cidade tende a resolver melhor;
  vale considerar guardar os dois.
- **Segmentação por regex é provisória.** O IA.md prevê spaCy no passo 2.
  A versão atual protege `a.C.`/`d.C.` e afins, mas não substitui spaCy.
- **Calibração feita contra um único parágrafo** — risco real de overfitting
  à amostra.

## Decisões que valem manter

- `CampoExtraido` **não tem** construtor sem proveniência. A regra "sem span,
  o campo não existe" é estrutural, não convenção.
- `EventoCandidato` é um tipo **distinto** de `HistoricalEvent`
  (`src/types/Event.ts`). Um candidato só vira evento no mapa depois de
  aprovação humana; tipos separados impedem vazamento por descuido.
- O stub de geocoding devolve `None` em vez de chutar coordenada. Um lat/lng
  inventado é pior que nenhum: entraria no banco parecendo dado e cravaria um
  ponto errado no globo.
- O texto verbatim fica em `Proveniencia.trecho` para rastreabilidade interna
  e **nunca** deve ir para a tela (direito autoral — ver CLAUDE.md).

## Próximos passos (ordem do IA.md)

2. Datas: normalizar `2560 a.C.` / `outubro de 1347` em `data_inicio`,
   `data_fim` e `incerteza_data`; trocar a segmentação por spaCy.
3. Geocoding real (Mordecai3 ou `geoparser` + GeoNames local).
4. Fila de revisão + gravação no PostGIS.
5. WHG/Pleiades para nomes de época.
