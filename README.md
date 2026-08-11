# Globo Histórico Interativo

Aplicação web com um globo terrestre interativo onde acontecimentos históricos
aparecem como pontos clicáveis.

Documentos de contexto:

- [CLAUDE.md](./CLAUDE.md) — visão geral, stack, modelo de dados, roadmap
- [VISUAL.md](./VISUAL.md) — direção visual, marcadores, navegação, LOD
- [IA.md](./IA.md) — pipeline de extração (livro → eventos), sem LLM generativo

## Estado atual

**Frontend (Fase 0):** React + [react-globe.gl](https://github.com/vasturiano/react-globe.gl)
com 10 eventos de `src/data/events.json`.

- Globo com tiles da NASA GIBS (relevo + batimetria, detalhe cresce com o zoom)
- Marcadores em ícone 2D (SVG) coloridos por categoria; tamanho por importância
- Navegação hierárquica: **mundo → continente → país → estado**, filtrando
  eventos por nível (importância 5 / 4 / 3 / 1) e por recorte geográfico
- Timeline de duas alças com faixas por era
- Busca por evento, local ou ator, com voo de câmera
- Painel de resumo ao clicar num evento

**Ingestão (passo 1 do IA.md):** extração de entidades com proveniência por
span, em `ingestao/`. Ver [ingestao/README.md](./ingestao/README.md).

## Rodando o frontend

```bash
npm install
npm run dev     # http://localhost:5173
npm run build   # typecheck + build de produção
```

## Rodando a ingestão (opcional)

Exige **Python >= 3.10** — o Python 3.9 que vem no macOS não serve, é
exigência do `gliner`.

```bash
cd ingestao
python3.12 -m venv .venv
./.venv/bin/pip install -r requirements.txt

./.venv/bin/python spike_passo1.py            # extrai e mede contra gabarito
./.venv/bin/python -m unittest testes         # rápido, não carrega o modelo
COM_MODELO=1 ./.venv/bin/python -m unittest testes
```

A primeira execução baixa o modelo `urchade/gliner_multi-v2.1` (1,16 GB,
Apache-2.0); o venv ocupa ~940 MB.

## Dados externos usados

Nada é baixado no build — tudo é buscado em runtime, de fontes abertas:

| Dado | Fonte | Licença |
| --- | --- | --- |
| Tiles do globo | NASA GIBS (`BlueMarble_ShadedRelief_Bathymetry`) | domínio público |
| Fronteiras de países e estados | Natural Earth (via `nvkelso/natural-earth-vector`) | domínio público |
| Modelo de extração | `urchade/gliner_multi-v2.1` (HuggingFace) | Apache-2.0 |

As fronteiras são as **atuais**. A interface deixa isso explícito ("região que
hoje é X") — a navegação é ferramenta de busca geográfica, não afirmação de que
a entidade existia no período selecionado. Ver VISUAL.md.
