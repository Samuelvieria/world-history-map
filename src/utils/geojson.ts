// Utilidades de geometria para GeoJSON, sem dependencia externa.

type Anel = number[][];
export type Geometria =
  | { type: 'Polygon'; coordinates: Anel[] }
  | { type: 'MultiPolygon'; coordinates: Anel[][] };

export interface Feicao {
  type: 'Feature';
  properties: Record<string, unknown>;
  geometry: Geometria | null;
}

/** Ray casting num anel. Retorna true se o ponto esta' dentro. */
function dentroDoAnel(lng: number, lat: number, anel: Anel): boolean {
  let dentro = false;
  for (let i = 0, j = anel.length - 1; i < anel.length; j = i++) {
    const [xi, yi] = anel[i];
    const [xj, yj] = anel[j];
    const cruza =
      yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi;
    if (cruza) dentro = !dentro;
  }
  return dentro;
}

/** Um poligono e' [anel externo, ...buracos]. */
function dentroDoPoligono(lng: number, lat: number, poligono: Anel[]): boolean {
  if (!poligono.length || !dentroDoAnel(lng, lat, poligono[0])) return false;
  // Se cair num buraco, esta' fora.
  return !poligono.slice(1).some((buraco) => dentroDoAnel(lng, lat, buraco));
}

/**
 * Teste ponto-em-poligono de verdade, em vez de bounding box.
 *
 * A bbox seria bem mais simples, mas erra feio justamente onde este app
 * precisa acertar: as caixas de Europa e Asia se sobrepoem, e a da Russia
 * cobre meio hemisferio. Um evento em Lisboa cairia "dentro" da Asia.
 */
export function pontoDentro(lng: number, lat: number, geometria: Geometria | null): boolean {
  if (!geometria) return false;
  if (geometria.type === 'Polygon') {
    return dentroDoPoligono(lng, lat, geometria.coordinates);
  }
  return geometria.coordinates.some((poligono) => dentroDoPoligono(lng, lat, poligono));
}

/** O ponto cai em alguma das geometrias? */
export function pontoDentroDeAlguma(
  lng: number,
  lat: number,
  geometrias: Geometria[],
): boolean {
  return geometrias.some((g) => pontoDentro(lng, lat, g));
}

/** Menor distancia (em graus) do ponto a um vertice da geometria. */
function distanciaAproximada(lng: number, lat: number, geometria: Geometria): number {
  const poligonos: Anel[][] =
    geometria.type === 'Polygon' ? [geometria.coordinates] : geometria.coordinates;
  let menor = Infinity;
  for (const poligono of poligonos) {
    for (const [x, y] of poligono[0] ?? []) {
      const d = Math.hypot(x - lng, y - lat);
      if (d < menor) menor = d;
    }
  }
  return menor;
}

// ~0,4 grau equivale a algo entre 40 e 45 km perto do equador.
const TOLERANCIA_GRAUS = 0.4;

/**
 * Ponto dentro da regiao, com folga para a costa.
 *
 * Teste estrito perde eventos demais para ser usavel: com o Natural Earth
 * 110m, "Colombo/Bahamas", "Messina" e "Constantinopla" caiam FORA de
 * qualquer pais. Trocar para 50m resolveu quase tudo, mas Istambul continua
 * escapando — fica no Bosforo, um estreito que a generalizacao fecha.
 *
 * A causa e' sistematica, nao azar: eventos historicos sao
 * desproporcionalmente costeiros (portos, capitais maritimas), e a
 * coordenada em si e' aproximada — o modelo de dados ate' carrega
 * `confianca_local`. Exigir precisao de fronteira de um dado que se assume
 * impreciso e' contraditorio, entao um ponto a menos de ~40 km da regiao
 * conta como dentro dela.
 */
export function pontoNaRegiao(
  lng: number,
  lat: number,
  geometrias: Geometria[],
): boolean {
  if (pontoDentroDeAlguma(lng, lat, geometrias)) return true;
  return geometrias.some((g) => distanciaAproximada(lng, lat, g) <= TOLERANCIA_GRAUS);
}

/**
 * Centro para onde a camera deve voar, e uma medida do tamanho da feicao.
 *
 * Usa o centroide da bbox, nao o centroide de area: e' mais barato e, para
 * enquadrar a camera, a diferenca nao aparece. Feicoes que cruzam a
 * antimeridiana (Russia, Fiji) ficam com centro errado — limitacao aceita,
 * anotada aqui para nao virar susto depois.
 */
export function enquadrar(geometrias: (Geometria | null)[]): {
  lat: number;
  lng: number;
  extensao: number;
} {
  const padrao = { lat: 0, lng: 0, extensao: 180 };

  let minLng = Infinity;
  let maxLng = -Infinity;
  let minLat = Infinity;
  let maxLat = -Infinity;

  for (const geometria of geometrias) {
    if (!geometria) continue;
    const poligonos: Anel[][] =
      geometria.type === 'Polygon' ? [geometria.coordinates] : geometria.coordinates;
    for (const poligono of poligonos) {
      for (const [lng, lat] of poligono[0] ?? []) {
        if (lng < minLng) minLng = lng;
        if (lng > maxLng) maxLng = lng;
        if (lat < minLat) minLat = lat;
        if (lat > maxLat) maxLat = lat;
      }
    }
  }

  if (!Number.isFinite(minLng)) return padrao;

  return {
    lat: (minLat + maxLat) / 2,
    lng: (minLng + maxLng) / 2,
    extensao: Math.max(maxLng - minLng, maxLat - minLat),
  };
}

/** Altitude de camera que enquadra uma feicao daquela extensao angular. */
export function altitudePara(extensao: number): number {
  return Math.min(2.2, Math.max(0.25, extensao / 45));
}
