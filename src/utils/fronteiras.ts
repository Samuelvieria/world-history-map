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
const URL_PAISES = `${BASE}/ne_50m_admin_0_countries.geojson`;

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

// Ja' o campo CONTINENT so' existe em ingles, e sao poucos valores fixos.
const CONTINENTE_PT: Record<string, string> = {
  Africa: 'África',
  Asia: 'Ásia',
  Europe: 'Europa',
  'North America': 'América do Norte',
  'South America': 'América do Sul',
  Oceania: 'Oceania',
  Antarctica: 'Antártida',
};

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

/** Identificador do continente (em ingles, como vem no dado). */
export function continenteDoPais(f: Feicao): string {
  return texto(f, 'CONTINENT') || 'Desconhecido';
}

/** Nome do continente para exibicao. */
export function continenteEmPortugues(continente: string): string {
  return CONTINENTE_PT[continente] ?? continente;
}

export function nomeDoEstado(f: Feicao): string {
  return texto(f, 'name') || texto(f, 'NAME') || 'Desconhecido';
}

function paisDoEstado(f: Feicao): string {
  return texto(f, 'admin') || texto(f, 'ADMIN');
}

export async function paises(): Promise<Feicao[]> {
  return carregar(URL_PAISES);
}

export async function paisesDoContinente(continente: string): Promise<Feicao[]> {
  const todos = await paises();
  return todos.filter((f) => continenteDoPais(f) === continente);
}

export async function estadosDoPais(nomePais: string): Promise<Feicao[]> {
  const todos = await carregar(URL_ESTADOS);
  return todos.filter((f) => paisDoEstado(f) === nomePais);
}

/** Continentes existentes, derivados do campo CONTINENT dos paises. */
export async function continentes(): Promise<string[]> {
  const todos = await paises();
  const nomes = new Set(todos.map(continenteDoPais));
  // "Seven seas (open ocean)" e' uma categoria do Natural Earth para ilhas
  // oceanicas soltas; nao e' um continente navegavel.
  nomes.delete('Seven seas (open ocean)');
  nomes.delete('Desconhecido');
  return [...nomes].sort();
}
