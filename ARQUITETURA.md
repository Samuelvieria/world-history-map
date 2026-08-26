# ARQUITETURA.md — Globo Histórico Interativo

> Este arquivo dá contexto ao Claude Code. Coloque-o na raiz do projeto.
> Ele resume as decisões tomadas no planejamento inicial.

## O que é o projeto

Aplicação **web** com um **globo terrestre interativo** (que gira, tipo Google
Earth) onde acontecimentos históricos aparecem como pontos clicáveis. O usuário
pode:

- Pesquisar um evento ("Segunda Guerra Mundial", "Odesa") e ver os pontos no globo.
- Clicar num ponto e ver um resumo do acontecimento.
- Filtrar por período usando uma **timeline de duas alças** (início e fim), com
  faixas nomeadas por era (Idade do Bronze, Idade do Ferro, Idade Média, etc.).
- Filtrar por **nível de importância** dos eventos (barra horizontal).
- **Alimentar o sistema com livros** (upload de PDF): a IA extrai eventos,
  geolocaliza e adiciona ao mapa — sempre com revisão humana antes de publicar.

O mapa de fundo e as fronteiras devem mudar conforme o período selecionado
(mundo desenhado como era na época, não só como é hoje).

## Stack decidida

- **Frontend:** React + `react-globe.gl` (MIT, wrapper sobre Three.js). Camadas
  nativas de points, arcs, labels, rings, tooltips e clique.
  - Upgrade futuro possível: **CesiumJS** (Apache 2.0) se precisar de terreno 3D
    real e precisão pesada. NÃO começar por ele.
- **Backend:** Python + **FastAPI**.
- **Banco:** **PostgreSQL + PostGIS** (consultas espaciais + temporais).
- **Ingestão:** PDF → texto (PyMuPDF/pdfplumber) → extração via LLM ancorada no
  texto → geocodificação → fila de revisão humana → banco.
- **Editor/IDE:** VS Code + Claude Code.

## Fluxo de dados (3 subsistemas)

1. **Ingestão** (o livro vira eventos): PDF → Extração IA (com trecho-fonte) →
   Geocodificação → Revisão humana → aprovado.
2. **Dados**: Banco espaço-temporal (PostGIS) guarda onde + quando + fonte.
3. **App/Frontend**: Globo + timeline + busca consomem do banco.

Regra de ouro contra alucinação: **a IA só sugere; o humano aprova.** Todo evento
extraído precisa estar rastreável até um trecho da fonte (proveniência).

## Modelo de dados — o evento (núcleo do projeto)

```json
{
  "id": "evt_001",
  "titulo": "Batalha de Stalingrado",
  "resumo": "Resumo em palavras próprias (NÃO copiar trechos longos da fonte).",
  "data_inicio": "1942-08-23",
  "data_fim": "1943-02-02",
  "incerteza_data": "exata",         // exata | ano | decada | seculo | aproximada
  "lat": 48.7,
  "lng": 44.5,
  "local_nome_epoca": "Stalingrado",
  "local_nome_atual": "Volgogrado",
  "geocoding_fonte": "WHG",          // de onde veio a coordenada
  "confianca_local": 0.9,
  "nivel_importancia": 5,            // heurística subjetiva, 1..5 — assumir como tal
  "era": "idade_contemporanea",
  "atores": ["Alemanha Nazista", "União Soviética"],
  "tags": ["segunda_guerra_mundial", "batalha"]
}
```

Campos que separam brinquedo de ferramenta séria: `incerteza_data`,
`confianca_local`, `geocoding_fonte`, e a proveniência (livro/página/trecho,
guardada internamente).

## Validação por consenso (credibilidade)

- Não guardar "a verdade" e sim **asserções de fontes**.
- Tabela de fontes com **nível de confiabilidade** (institucional/PUC/revisão por
  pares = peso alto; livro genérico = médio; web aberta = baixo).
- Cada evento se liga a uma ou mais asserções.
- Calcular: **escore de corroboração** (nº de fontes independentes que concordam)
  e **confiança ponderada** (corroboração × peso das fontes).
- **Quando as fontes divergem, MOSTRAR a divergência — não forçar consenso.**
  História tem disputa legítima. Terceira fonte serve pra entender a divergência,
  não só pra "votar" (cuidado: repetição não é prova; narrativa popular ≠ correta).

## Geocodificação

- MVP: **Nominatim / GeoNames** (coordenadas modernas, aceitar imprecisão).
- Depois: **World Historical Gazetteer (WHG)** e **Pleiades** para nomes de época
  (Constantinopla/Istambul, Prússia, etc.). Geocoders comuns (Google) são
  inadequados para pesquisa histórica.

## Mapas por período

- Textura do globo: trivial trocar por era.
- Fronteiras históricas por ano: usar dataset aberto em GeoJSON (confirmar o
  repositório e a licença antes de usar). Carregar a camada correspondente ao
  período da timeline.

## Roadmap por fases (ordem: 1 → 2 → 3, NÃO começar pela IA)

- **Fase 0 — Esqueleto andante (SEM IA). ← ESTAMOS AQUI**
  React + react-globe.gl mostrando ~10 eventos de um JSON escrito à mão. Timeline
  de duas alças funcionando (filtra por data), filtro de importância, painel de
  resumo ao clicar. Prova o loop visual inteiro.
- **Fase 1 — Backend + banco.** FastAPI + PostGIS. Eventos saem do JSON pro banco.
  Rota de busca. Filtros por era e importância.
- **Fase 2 — Ingestão manual assistida.** Upload PDF → IA sugere eventos com
  trecho-fonte → tela de revisão (aprova/rejeita) → banco.
- **Fase 3 — Geocodificação histórica.** Trocar Nominatim por WHG/Pleiades.
  Mostrar incerteza na interface.
- **Fase 4 — Refino.** Automação, busca com embeddings, arcos de movimentação.

## Como quero que você trabalhe (regras)

- Direto e factual. Pensar passo a passo. Explicar causa raiz.
- **Nunca inventar** APIs, campos, dados ou fontes. Diferenciar fato de hipótese.
- Explicitar incertezas — pode dizer "não sei".
- Priorizar documentação oficial e citar referências.
- Respeitar direito autoral: guardar trecho-fonte internamente para proveniência,
  mas exibir ao usuário apenas resumo em palavras próprias.

## Referências

- react-globe.gl: https://github.com/vasturiano/react-globe.gl
- CesiumJS: https://cesium.com/platform/cesiumjs/
- World Historical Gazetteer: https://whgazetteer.org/ (docs: https://docs.whgazetteer.org/)
- Pleiades (mundo antigo): https://pleiades.stoa.org/
- PostGIS: https://postgis.net/
- FastAPI: https://fastapi.tiangolo.com/
