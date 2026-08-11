import type { Feicao } from './geojson';

// Fronteiras do Natural Earth (dominio publico), servidas pelo repo oficial
// nvkelso/natural-earth-vector.
//
// Sao fronteiras ATUAIS. Ver `rotuloDeRegiao` em navegacao.ts: aqui elas
// servem para navegar, nao para afirmar que a entidade existia na epoca.
const BASE = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson';

// 50m (2,9 MB) em vez de 110m (820 KB), apesar do peso.
//
// MEDIDO: com o 110m, metade dos eventos de teste caia FORA de qualquer pais
// — "Colombo/Bahamas", "Messina" e "Constantinopla" — porque a generalizacao
// encolhe ilhas e recua costas. Com o 50m so' Constantinopla continua
// escapando (fica no Bosforo, um estreito que a generalizacao fecha), e essa
// sobra e' coberta pela tolerancia em `pontoNaRegiao`.
//
// Essa precisao so' importa para o RECORTE (filtrar evento por dentro da
// fronteira) — usado a partir do nivel pais. No nivel mundo nao ha recorte
// nenhum (so' clique pra identificar o pais), e' onde entra `URL_PAISES_MUNDO`.
const URL_PAISES = `${BASE}/ne_50m_admin_0_countries.geojson`;

// 110m (820 KB) so' para desenhar o nivel MUNDO: ~180 paises simultaneos e' o
// maior poligono que o app desenha de uma vez, e o unico nivel sem recorte —
// entao a fronteira grosseira nao custa precisao, so' economiza vertice.
// MEDIDO (travamento reportado no nivel mundo): esse e' o candidato mais
// provavel, ja' que nenhum outro nivel desenha mais que uma duzia de regioes.
const URL_PAISES_MUNDO = `${BASE}/ne_110m_admin_0_countries.geojson`;

// 50m (2,2 MB) para estados. O 10m tem cobertura completa (4.596 estados, 253
// paises) mas pesa 39 MB — inviavel de baixar no navegador de uma vez. O 50m
// traz so' 294 estados e cobre principalmente paises grandes; quando o pais
// escolhido nao tiver estados aqui, o app pula o nivel em vez de mostrar tela
// vazia. Fatiar o 10m por pais em build-time e' o upgrade natural.
const URL_ESTADOS = `${BASE}/ne_50m_admin_1_states_provinces.geojson`;

interface ColecaoGeoJson {
  features: Feicao[];
}

const cache = new Map<string, Promise<Feicao[]>>();

async function carregar(url: string): Promise<Feicao[]> {
  let pendente = cache.get(url);
  if (!pendente) {
    pendente = fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`falha ao baixar fronteiras: HTTP ${r.status}`);
        return r.json() as Promise<ColecaoGeoJson>;
      })
      .then((colecao) => colecao.features.filter((f) => f.geometry))
      .catch((erro) => {
        // Nao deixa a promessa falha no cache: a proxima tentativa refaz o
        // pedido em vez de repetir o erro para sempre.
        cache.delete(url);
        throw erro;
      });
    cache.set(url, pendente);
  }
  return pendente;
}

function texto(f: Feicao, chave: string): string {
  const v = f.properties[chave];
  return typeof v === 'string' ? v : '';
}

// O Natural Earth traz nomes localizados; NAME_PT da' "Tanzânia" em vez de
// "Tanzania". Cai para o nome em ingles quando a traducao nao existe.
export function nomeDoPais(f: Feicao): string {
  return (
    texto(f, 'NAME_PT') ||
    texto(f, 'NAME') ||
    texto(f, 'ADMIN') ||
    texto(f, 'name') ||
    'Desconhecido'
  );
}

/**
 * Identificador do pais, em ingles.
 *
 * Precisa ser separado de `nomeDoPais`: a camada de estados casa pelo campo
 * `admin`, que vem em ingles ("Brazil"). Usar o nome traduzido para filtrar
 * faria "Brasil" nunca casar com "Brazil", e nenhum estado apareceria.
 */
export function idDoPais(f: Feicao): string {
  return texto(f, 'ADMIN') || texto(f, 'NAME') || texto(f, 'name') || 'Desconhecido';
}

/** Identificador do continente (em ingles, como vem no dado) — usado so' pra
 * colorir o nivel mundo por agrupamento (ver `corDoContinente`). */
export function continenteDoPais(f: Feicao): string {
  return texto(f, 'CONTINENT') || 'Desconhecido';
}

export function nomeDoEstado(f: Feicao): string {
  return texto(f, 'name') || texto(f, 'NAME') || 'Desconhecido';
}

function paisDoEstado(f: Feicao): string {
  return texto(f, 'admin') || texto(f, 'ADMIN');
}

/** Paises precisos (50m) — so' para o recorte de evento, nunca para desenhar o mundo. */
export async function paises(): Promise<Feicao[]> {
  return carregar(URL_PAISES);
}

/** Paises grosseiros (110m) — o poligono clicavel do nivel mundo. */
export async function paisesParaMundo(): Promise<Feicao[]> {
  return carregar(URL_PAISES_MUNDO);
}

/**
 * Versao precisa (50m) do pais identificado por `idDoPais`, para usar como
 * recorte depois que o usuario clica no poligono grosseiro do nivel mundo.
 *
 * Sem isso o recorte herdaria a fronteira encolhida do 110m e o bug que
 * `URL_PAISES` documenta (evento costeiro cai fora do pais) voltaria.
 */
export async function paisPreciso(nomeId: string): Promise<Feicao | undefined> {
  const todos = await paises();
  return todos.find((f) => idDoPais(f) === nomeId);
}

export async function estadosDoPais(nomePais: string): Promise<Feicao[]> {
  const todos = await carregar(URL_ESTADOS);
  return todos.filter((f) => paisDoEstado(f) === nomePais);
}
