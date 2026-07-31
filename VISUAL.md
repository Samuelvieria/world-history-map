# VISUAL.md — Direção visual do Globo Histórico

> Brief de design para os marcadores e a interface do mapa.
> Complementa o CLAUDE.md. Stack: React + react-globe.gl (Three.js/WebGL).

## Prior-art para estudar (roubar ideias de UI)

- **Chronas** — https://chronas.org/ — timeline embaixo, marcadores por tipo
  (batalha, pessoa, cidade, castelo), fronteiras que mudam por ano, ligado à
  Wikipédia. É o mais próximo do nosso projeto. Open source.
- **Running Reality** — https://runningreality.org/ — globo 3D, 3000 a.C. → hoje,
  cidades crescendo/sumindo pela timeline.
- **HistoryMaps** — https://history-maps.com/ — mapas 3D + timeline + imagens.
- **OpenHistoricalMap** — https://openhistoricalmap.org/ — OSM histórico editável.
- **Histography** — https://histography.io/ — timeline visual de eventos.

## Camadas do react-globe.gl e como usar cada uma

O react-globe.gl renderiza dados como camadas empilháveis. Mapeamento pro projeto:

- **Points layer** — marcador padrão: um cilindro que sobe da superfície.
  A **altura do cilindro** codifica a importância (`nivel_importancia`). Barato,
  aguenta muitos pontos. É o default.
- **Custom / 3D Objects layer** (`customThreeObject`) — aceita qualquer Object3D
  do Three.js, ou seja, **modelos GLB temáticos** (espada, barco, castelo).
  Usar só em level-of-detail alto (ver Performance). É o "uau".
- **HTML Elements layer** — ícone DOM (SVG/emoji) posicionado no globo. Ótimo
  pra ícone 2D nítido por categoria em zoom médio.
- **Rings layer** — anel/onda pulsante. Usar para destacar o evento selecionado
  ou eventos de importância máxima.
- **Arcs / Paths layer** — arcos e trajetos: movimentações, campanhas militares,
  rotas de comércio, migrações. Liga dois pontos no globo.
- **Polygons layer** — polígonos extrudados: **fronteiras históricas por era**
  (carregar o GeoJSON do período selecionado na timeline).
- **Labels layer** — nome do evento como texto no globo.

## Sistema de marcadores por categoria

Cada evento tem uma `categoria`. Mapa categoria → cor → ícone 2D → modelo 3D.
Sempre parear **cor + forma** (não depender só de cor — daltonismo + muitas
categorias).

| Categoria            | Cor        | Ícone 2D        | Modelo 3D (LOD alto)   |
| -------------------- | ---------- | --------------- | ---------------------- |
| Batalha / guerra     | vermelho   | espadas cruzadas| espada cravada / elmo  |
| Construção/estrutura | âmbar      | edifício        | castelo / templo       |
| Naval / expedição     | azul       | âncora          | caravela / barco       |
| Político / tratado   | roxo       | coroa/pergaminho| coroa / trono          |
| Cultural/científico  | verde-azul | livro/lâmpada   | livro / obelisco       |
| Religioso            | dourado    | símbolo neutro  | templo / estrutura     |
| Descoberta/exploração| ciano      | bússola         | bússola / bandeira     |
| Desastre / epidemia  | cinza      | marcador sóbrio | (evitar ícone caricato)|

Nota de bom senso: para eventos sensíveis (massacres, epidemias, genocídios),
usar marcador **sóbrio e discreto**, não ícone lúdico. Respeito > estética.

## Level-of-detail (LOD) — REGRA CRÍTICA DE PERFORMANCE

Navegador roda em hardware qualquer (celular de 3 anos). NÃO carregar milhares de
GLB de uma vez — mata draw calls e memória.

- **Zoom distante:** só pontos simples, ou heatmap/hexbin, ou clustering por
  região. Nada de 3D.
- **Zoom médio:** ícone 2D colorido por categoria (HTML Elements ou sprite).
- **Zoom perto / evento selecionado / importância máxima:** aí sim carrega o
  modelo GLB temático (Custom layer).
- Limitar o número de modelos 3D simultâneos (ex.: só os N mais próximos da
  câmera + o selecionado).

Orçamento de polígonos (fonte: guias de assets de jogo): props com algumas
centenas a poucos milhares de triângulos; vigie **draw calls**, não só polígonos.
Kenney/Quaternius compartilham atlas de textura → cena inteira em poucas draw
calls. Usar instancing quando repetir o mesmo modelo.

## Codificação de importância e de tempo

- **Importância** (`nivel_importancia` 1..5): altura do cilindro (points), tamanho
  do ícone, brilho, ou anel (rings) nos de nível máximo.
- **Tempo**: ao arrastar a timeline, eventos fora da janela somem (fade out) e os
  de dentro aparecem (fade in). As fronteiras (polygons) trocam junto.
- **Incerteza** (`incerteza_data`, `confianca_local`): marcador mais transparente
  ou tracejado = menos certo. Mostrar honestamente, não esconder.

## Fontes de modelos 3D (GLB prontos)

- **Poly Pizza** — https://poly.pizza/ — 10k+ low poly, sem login. Maioria CC-BY.
- **Kenney** — https://kenney.nl/ — CC0, atlas compartilhado, estilo coerente.
- **Quaternius** — https://quaternius.com/ — CC0.
- **KayKit** — CC0.

Licenças: preferir **CC0** (uso livre, sem atribuição). Para CC-BY, manter uma
lista de créditos e salvar o print da página de licença de cada modelo.

## Direção estética (escolher uma pra começar)

1. **Espaço / dados** — globo escuro sobre fundo estrelado, marcadores que
   brilham (glow). Moderno, ótimo pra muitos pontos, o "uau" imediato.
2. **Atlas / pergaminho** — globo com textura envelhecida, marcadores estilo
   ilustração de mapa antigo. Mais temático pra história, menos "tech".

Sugestão: começar na direção 1 (mais fácil de deixar bonito com react-globe.gl) e
oferecer a 2 como tema alternativo depois.

## Interação

- **Hover** → tooltip com o nome do evento (Labels/tooltip nativo).
- **Clique** → painel lateral com resumo + **proveniência** (fonte/livro/página) +
  confiança/incerteza.
- **Timeline** (duas alças) → atualiza marcadores E fronteiras.
- **Busca** → destaca e voa até os pontos do resultado.

## Checklist de performance

- LOD para 3D (acima).
- Instancing para marcadores repetidos.
- Fade/culling de eventos fora da janela de tempo.
- Cap de modelos GLB simultâneos.
- Atlas de textura; poucos materiais distintos.

## Estado da implementação (Fase 0)

O que já está no ar, versus o que fica pra depois:

- **Feito:** cor por categoria + ícone 2D (emoji, camada HTML) em zoom médio,
  altura do cilindro por importância, anel pulsante nos eventos de importância
  máxima e no evento selecionado, legenda de categoria + importância, busca com
  voo de câmera, timeline de duas alças, colisão de coordenadas idênticas
  resolvida com afastamento circular.
- **Adiado (precisa de mais trabalho antes de fazer certo):**
  - Modelos 3D (GLB) em LOD alto — precisa escolher e baixar assets com licença
    confirmada de Poly Pizza/Kenney/Quaternius, hospedar localmente e credenciar.
    Não inventar URLs de modelo sem checar.
  - Arcos/paths (campanhas, rotas, migrações) — faz sentido quando tivermos
    eventos com origem+destino nos dados.
  - Fronteiras históricas por era (Polygons layer) — depende de um dataset
    GeoJSON aberto por ano, com licença confirmada (ver CLAUDE.md). Fase 3.
