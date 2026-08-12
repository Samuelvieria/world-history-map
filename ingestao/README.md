# ingestao — passos 1, 6 e 7 do IA.md

Spike do pipeline: **texto em português → entidades tipadas com span →
`EventoCandidato`**, agora com data normalizada (`data_inicio`/`data_fim`/
`incerteza_data`) e resumo por template — sem LLM generativo e sem geocoding
(ainda stub, passo 5).

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

./.venv/bin/python ingerir_pdf.py amostras/livro.pdf --paginas 5   # PDF real
```

Primeira execução baixa `urchade/gliner_multi-v2.1` (**1,16 GB**, licença
Apache-2.0) para o cache do HuggingFace. O venv ocupa ~940 MB.

**Se tiver GPU NVIDIA, vale muito instalar o torch com CUDA** — ver nota em
`requirements.txt`. MEDIDO numa RTX 3060: ingestão real de PDF caiu de
~8s/página (CPU) para ~0,45s/página (GPU) no regime permanente — um livro de
270 páginas passa de ~3h para ~5min. `extracao/extrator.py` já detecta CUDA
automaticamente quando disponível; só falta o torch certo instalado.

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

## Passo 2 — normalização de data e resumo (novo)

`extracao/datas.py` converte a data bruta extraída pelo GLiNER em
`data_inicio`/`data_fim`/`incerteza_data`. **Decisão que diverge do IA.md
original**: nem HeidelTime nem `dateparser`, e sim regex + regras.
Motivo — nenhuma das duas bibliotecas cobre o caso mais comum em texto
histórico em português, ano antes de Cristo ("2560 a.C."); `dateparser`
não tem esse conceito, e HeidelTime é uma dependência Java pesada para
cobrir só cinco formatos de data. Formatos reconhecidos: dia+mês+ano
(`"exata"`), mês+ano e ano isolado (`"ano"`), década (`"decada"`), século
em romano ou arábico (`"seculo"`), e qualquer um dos anteriores com marcador
de aproximação ("por volta de", "cerca de") na frase ao redor → `"aproximada"`.
Anos a.C. usam numeração astronomica ISO 8601 (ano 1 a.C. = astronômico `0`;
"2560 a.C." = `"-2559-01-01"`), o que preserva ordem cronológica em
comparação direta de string.

`extracao/resumo.py` gera o campo `resumo` por slot-filling puro a partir dos
campos já extraídos (`titulo`, `categoria`, `local_nome_epoca`, `data_inicio`,
`atores`) — nunca copia o trecho-fonte e nunca introduz informação que não
esteja em outro campo. Um candidato sem `titulo` nem `categoria` gera
`resumo = None` em vez de um texto vazio ou inventado.

Ambos os módulos são chamados automaticamente no fim de
`ExtratorGLiNER.extrair()`.

**Verificado por execução** (Python instalado depois, venv criado, `pip
install -r requirements.txt`, `COM_MODELO=1 python -m unittest testes` — 35/35
testes, incluindo os dois de integração que baixam o modelo de verdade — e
`python spike_passo1.py` contra o parágrafo de teste):

| Campo                     | Resultado |
| ------------------------- | --------- |
| local                     | 3/4 (igual ao passo 1 — nada regrediu) |
| categoria                 | 4/4 |
| data (raw, passo 1)       | 4/4 |
| **data normalizada (passo 6)** | **4/5 candidatos** |

Os 4 candidatos com data bruta normalizaram exatamente como o desenho previa:
`"29 de maio de 1453"` → `1453-05-29`/`exata`; `"outubro de 1347"` →
`1347-10-01..1347-10-31`/`ano`; `"1789"` → `1789-01-01..1789-12-31`/`ano`; e o
caso mais delicado, `"2560 a.C."` (com "por volta de" fora do span, só na
frase ao redor) → `-2559-01-01`/**`aproximada`** — confirma que a janela de
contexto (`_janela_contexto`, 40 caracteres antes do span) captura o marcador
de aproximação mesmo quando ele não faz parte da entidade extraída pelo
GLiNER. O quinto candidato (o da frase "A cidade, hoje chamada Istambul...",
já apontado como espúrio abaixo) não tem `titulo`/`categoria`/data — fica
incompleto por construção, como esperado.

**Observação nova, não estava prevista**: o `resumo` fica redundante quando o
`titulo` é o mesmo span que `local_nome_epoca` (candidato da Grande Pirâmide
de Gizé: "Grande Pirâmide de Gizé, envolvendo faraó Quéops" repete o nome).
Não é alucinação — é o slot-filling mostrando fielmente que dois campos
diferentes do candidato apontam pro mesmo texto — mas fica estranho de ler.
Vale revisitar quando o passo 4 (agrupamento em evento) evoluir; por ora é
cosmético, não corrompe proveniência nem factualidade.

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

## Passo 8 — fila de revisão (novo, em CLI)

`revisar.py` lê um JSON de `ingerir_pdf.py` e mostra, um candidato por vez,
todos os campos extraídos **com o trecho-fonte por baixo** (para conferência
— é uso interno de quem revisa, nunca vai pra tela do mapa; ver
`Proveniencia.trecho`). A pessoa responde aprovar/rejeitar/pular/sair; cada
resposta é salva de volta no mesmo arquivo na hora, não só no fim — fechar o
terminal no meio não perde o que já foi decidido.

```bash
./.venv/Scripts/python.exe revisar.py amostras/saida_historia_antiga.json --so-completos
```

**Isso não grava no mapa.** Só muda `status` para `"aprovado"`/`"rejeitado"`
no JSON. Ver `publicar.py` abaixo pro que falta depois disso.

## Passo 5 (geocoding real) + ponte pro globo — caminho barato

`publicar.py` pega os `status="aprovado"` de um ou mais JSONs, geocodifica
`local_nome_epoca` com **Nominatim** (MVP do IA.md — antes stub) e funde no
`src/data/events.json` que o app React já lê, no formato de
`HistoricalEvent`. **Não** é a Fase 1 do CLAUDE.md (FastAPI + PostGIS) — é o
caminho mais simples que prova o loop completo (livro → extração → revisão
→ mapa) sem construir backend/banco ainda.

```bash
./.venv/Scripts/python.exe publicar.py amostras/saida_historia_antiga.json amostras/saida_historia_moderna.json
```

Só publica um aprovado se tiver todos os campos obrigatórios E o Nominatim
achar coordenada com confiança suficiente — sem qualquer um desses, fica de
fora com motivo explícito no relatório, nunca silenciosamente.

**Achado sério, medido contra os 21 aprovados reais desta sessão**: geocodificar
nome de lugar de época é traiçoeiro além do "aceitar imprecisão" que o
IA.md já previa. 6 de 14 resultados iniciais foram pra lugar homônimo
**errado**: "Reino Novo" (Egito) foi pro aeroporto de uma cidade brasileira
chamada Reino; "Quarta Cruzada"/Constantinopla foi pra uma rua de mesmo nome
em Buenos Aires; local "ABC" foi pra sede da rádio australiana ABC;
"Bastilha" foi pra um vilarejo na Bretanha. Duas blindagens adicionadas e
medidas contra esse mesmo lote: `CONFIANCA_MINIMA = 0.5` sobre o `importance`
do Nominatim, e `TAMANHO_MINIMO_NOME_LUGAR = 4` (sigla como "ABC" tinha
confiança *alta* — 0,66 — por ser um lugar real proeminente, só que errado
pro nosso caso; confiança sozinha não bastava). Resultado: 6 de 21 publicados
de fato, testado no app rodando (busca por "Pantheon" abre painel com
localização/data/resumo corretos). Detalhe completo no IA.md.

## Correlação entre fontes ("Validação por consenso" do CLAUDE.md)

Sem isso, o mesmo acontecimento em dois livros diferentes virava dois
marcadores duplicados no mapa. `correlacionar.py` sugere pares de aprovados
de fontes diferentes que parecem descrever o mesmo evento (título/local/data
— `extracao/correlacao.py`), mostra a divergência quando houver, e só liga
os dois (`grupo_correlacao`) se um humano confirmar:

```bash
./.venv/Scripts/python.exe correlacionar.py amostras/saida_historia_antiga.json amostras/saida_historia_moderna.json
```

`publicar.py` funde cada grupo confirmado num evento só — corroborado por N
fontes, atores unidos, data de maior precisão entre os membros, divergência
(quando há) escrita por extenso no resumo em vez de escondida. Testado com
par sintético de ponta a ponta (os dois livros de amostra não se sobrepõem
tematicamente, então não geram par de verdade pra testar) — detalhe e
exemplo real no IA.md.

## Próximos passos (ordem do IA.md)

2. ~~Datas: normalizar `2560 a.C.` / `outubro de 1347`~~ feito (ver acima) —
   falta trocar a segmentação por spaCy.
3. ~~Geocoding real~~ feito via Nominatim (ver acima, caminho barato) — falta
   WHG/Pleiades pra nomes de época de verdade (item 5).
4. ~~Fila de revisão~~ feito em CLI (ver acima) — falta gravação num banco
   de verdade, que depende do backend da Fase 1 (ainda não existe).
5. WHG/Pleiades para nomes de época.
