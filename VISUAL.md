# VISUAL.md — Direção visual do Globo Histórico

> Brief de design para os marcadores e a interface do mapa.
> Complementa o ARQUITETURA.md. Stack: React + react-globe.gl (Three.js/WebGL).

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

### Marcadores: ícone 2D, não modelo 3D

Os modelos 3D procedurais foram **removidos** (`utils/models3d.ts` não existe
mais). Motivo: geometria 3D fica refém do ângulo da câmera — uma espada vista
de perfil virava um risco na tela, o mesmo defeito dos cilindros. Hoje cada
categoria tem um ícone SVG inline (`utils/icones.ts`), que encara sempre o
observador, é nítido em qualquer zoom, não depende de fonte de emoji e não faz
requisição externa.

A camada de pontos do react-globe.gl também saiu: ela desenha cilindros, e com
altura codificando importância eles viravam tubos atravessando o globo.
Importância agora é **tamanho do ícone** + anel pulsante (o anel é plano).

### Mapa: tiles da NASA, não textura fixa

`BlueMarble_ShadedRelief_Bathymetry` via NASA GIBS (domínio público), com
relevo de continente e de fundo de oceano, sem nuvens e sem ruas modernas.
Detalhe cresce com o zoom (≈65.536 px no nível máximo, contra 4.096 px da
textura fixa anterior). Nível 8 é o teto desta camada — o 9 responde HTTP 400.

### Navegação hierárquica (drill-down)

Mundo → continente → país → estado, sempre no globo (zoom animado + breadcrumb),
com fronteiras do Natural Earth. Cada nível filtra por importância mínima
(5 / 4 / 3 / 1) e recorta geograficamente por ponto-em-polígono.

Duas decisões que valem manter:

- **O recorte de um continente é o conjunto dos seus países**, não a feição
  clicada. Sem isso, "América do Norte" listava eventos da Europa.
- **Identificador e rótulo são campos separados** (`nome` em inglês, `rotulo`
  em português). A camada de estados casa pelo campo `admin`, que não é
  traduzido — usar o nome exibido para filtrar faria "Brasil" nunca casar com
  "Brazil".

**Fronteiras são as de hoje, e a interface diz isso.** Não existia "Brasil" em
1500 nem "estados" na Alemanha de 1200: a navegação é ferramenta de busca
geográfica, não afirmação de que a entidade existia. O breadcrumb mostra
"Região que hoje é X (fronteira atual)".

### Armadilha medida: eventos costeiros somem no teste estrito

Com o Natural Earth **110m**, metade dos eventos de teste caía FORA de qualquer
país: Colombo/Bahamas, Messina e Constantinopla. A generalização encolhe ilhas
e recua costas — e eventos históricos são desproporcionalmente costeiros
(portos, capitais marítimas), então isso atinge o caso comum, não o raro.

Correção em duas partes: **50m** em vez de 110m (2,9 MB contra 820 KB, resolve
8 de 9) e **tolerância de ~40 km** em `pontoNaRegiao` para o que resta —
Istambul fica no Bósforo, um estreito que até o 50m fecha. A tolerância é
coerente com o modelo de dados, que já assume coordenada aproximada
(`confianca_local`).

### Limitações conhecidas

- **Estados só existem para parte dos países.** O Natural Earth 50m traz 294
  estados no mundo todo; o 10m tem cobertura completa (4.596) mas pesa 39 MB,
  inviável de baixar de uma vez. Quando o país não tem estados, o app avisa em
  vez de mostrar tela vazia. Fatiar o 10m por país em build-time é o upgrade.
- **`enquadrar` erra em feições que cruzam a antimeridiana** (Rússia, Fiji):
  usa centroide de bounding box.
- Rótulos de texto só aparecem nos níveis país/estado — no mundo eles se
  sobrepõem e um tapa o outro.

### Adiado (precisa de mais trabalho antes de fazer certo)

- Arcos/paths (campanhas, rotas, migrações) — faz sentido quando tivermos
  eventos com origem+destino nos dados.
- Fronteiras históricas por era — depende de um dataset GeoJSON aberto por ano,
  com licença confirmada (ver ARQUITETURA.md). Fase 3. É o que tornaria a navegação
  historicamente correta, em vez de apenas rotulada como moderna.
- Modelos 3D em GLB de verdade (Poly Pizza/Kenney/Quaternius) continuam um
  caminho válido para LOD alto, mas exigem verificar a licença de cada arquivo.
