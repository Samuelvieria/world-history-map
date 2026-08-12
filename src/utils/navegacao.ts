import type { Feicao } from './geojson';

export type NivelNavegacao = 'mundo' | 'pais' | 'estado';

export interface CameraPose {
  lat: number;
  lng: number;
  altitude: number;
}

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
   * Geometria que recorta a regiao (vazio no nivel mundo). Lista por
   * uniformidade com `pontoNaRegiao`/`enquadrar` (que operam sobre varias
   * geometrias); hoje sempre 0 ou 1 feicao — o pais ou estado clicado.
   */
  recorte: Feicao[];
  /**
   * Pose da camera no momento em que o usuario SAIU deste passo pra
   * mergulhar mais fundo — None enquanto o passo e' o atual. Sem isso,
   * "voltar" so' sabia reenquadrar o recorte inteiro, o que jogava a camera
   * pra um ponto generico (ex.: mundo sempre voltava pra lat 20/lng 10) em
   * vez de restaurar de onde a pessoa realmente tinha saido.
   */
  camera?: CameraPose;
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
  pais: 3,
  estado: 1,
};

export function importanciaMinimaDoNivel(nivel: NivelNavegacao): number {
  return IMPORTANCIA_MINIMA[nivel];
}

/** Proximo nivel do drill-down, ou null se ja' e' o mais fundo. */
export function proximoNivel(nivel: NivelNavegacao): NivelNavegacao | null {
  const ordem: NivelNavegacao[] = ['mundo', 'pais', 'estado'];
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
 *
 * Opacidade baixa de proposito (0.1, era 0.28): em 0.28 a cor virava uma
 * mancha de tinta lisa sobre o relevo fotografico da NASA (Globe.tsx),
 * competindo com ele em vez de so' indicar agrupamento. O relevo tem que
 * continuar legivel por baixo — a cor e' so' uma pista, nao a informacao
 * principal (essa e' o marcador do evento).
 */
// Paleta de pigmento da direção "Gravura" (VISUAL.md), não os tons padrão
// do Tailwind que estavam aqui antes — cada rgb corresponde a um token de
// cor de index.css (convertido pra rgb porque corDoContinente monta a
// string rgba() direto, sem passar por CSS custom property).
const COR_CONTINENTE: Record<string, string> = {
  Africa: '184, 134, 43', // --ochre
  Asia: '138, 64, 48', // --terra
  Europe: '69, 96, 122', // --steel
  'North America': '122, 90, 137', // --plum
  'South America': '63, 122, 112', // --teal
  Oceania: '166, 139, 63', // --olive
  Antarctica: '107, 104, 88', // --slate
};

export function corDoContinente(continente: string, opacidade = 0.1): string {
  const rgb = COR_CONTINENTE[continente] ?? '107, 104, 88';
  return `rgba(${rgb}, ${opacidade})`;
}
