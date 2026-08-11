import type { Feicao } from './geojson';

export type NivelNavegacao = 'mundo' | 'continente' | 'pais' | 'estado';

export interface PassoNavegacao {
  nivel: NivelNavegacao;
  /**
   * Identificador usado para filtrar os dados — sempre como vem do Natural
   * Earth, ou seja, em ingles ("Europe", "Brazil"). Separado do rotulo porque
   * a camada de estados casa pelo campo `admin`, que nao e' traduzido.
   */
  nome: string;
  /** Texto exibido ao usuario, em portugues. */
  rotulo: string;
  /**
   * Geometrias que recortam a regiao (vazio no nivel mundo).
   *
   * E' uma lista, nao uma feicao unica, porque um continente e' o conjunto
   * dos seus paises: recortar pela feicao do pais clicado faria "America do
   * Norte" listar eventos da Europa.
   */
  recorte: Feicao[];
}

/**
 * Importancia minima visivel em cada nivel.
 *
 * Derivado de `nivel_importancia` em vez de um campo `escopo` proprio: nao
 * exige mexer nos dados nem no pipeline de ingestao, e da' pra medir se o
 * resultado agrada antes de investir num campo novo. A distincao entre
 * "importancia" (quanto pesa) e "alcance" (ate' onde repercute) e' real e
 * pode virar campo separado depois — um evento pode ser importantissimo e
 * puramente local.
 */
const IMPORTANCIA_MINIMA: Record<NivelNavegacao, number> = {
  mundo: 5,
  continente: 4,
  pais: 3,
  estado: 1,
};

export function importanciaMinimaDoNivel(nivel: NivelNavegacao): number {
  return IMPORTANCIA_MINIMA[nivel];
}

/** Proximo nivel do drill-down, ou null se ja' e' o mais fundo. */
export function proximoNivel(nivel: NivelNavegacao): NivelNavegacao | null {
  const ordem: NivelNavegacao[] = ['mundo', 'continente', 'pais', 'estado'];
  const i = ordem.indexOf(nivel);
  return i >= 0 && i < ordem.length - 1 ? ordem[i + 1] : null;
}

export const TRILHA_INICIAL: PassoNavegacao[] = [
  { nivel: 'mundo', nome: 'Mundo', rotulo: 'Mundo', recorte: [] },
];

/**
 * Rotulo honesto para a regiao selecionada.
 *
 * As fronteiras vem do Natural Earth, que sao as de HOJE. Num mapa historico
 * isso pode virar afirmacao falsa: nao existia "Brasil" em 1500 nem "estados"
 * na Alemanha de 1200. A navegacao aqui e' ferramenta de busca geografica, nao
 * afirmacao de que a entidade existia na epoca — e o texto precisa dizer isso,
 * senao o mapa mente por omissao.
 */
export function rotuloDeRegiao(passo: PassoNavegacao): string {
  if (passo.nivel === 'mundo') return 'Mundo inteiro';
  return `Região que hoje é ${passo.rotulo}`;
}

/**
 * Cor por continente, usada no nivel mundo.
 *
 * No mundo os poligonos desenhados sao de PAISES, mas o clique entra no
 * continente. Pintar cada pais com a cor do seu continente deixa a agrupacao
 * visivel — sem isso o usuario clica num pais esperando entrar nele.
 */
const COR_CONTINENTE: Record<string, string> = {
  Africa: '234, 179, 8',
  Asia: '239, 68, 68',
  Europe: '59, 130, 246',
  'North America': '168, 85, 247',
  'South America': '34, 197, 94',
  Oceania: '20, 184, 166',
  Antarctica: '148, 163, 184',
};

export function corDoContinente(continente: string, opacidade = 0.28): string {
  const rgb = COR_CONTINENTE[continente] ?? '148, 163, 184';
  return `rgba(${rgb}, ${opacidade})`;
}
