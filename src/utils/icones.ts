import type { Categoria } from '../types/Event';

// Icones 2D em SVG inline, um por categoria.
//
// Substituem os modelos 3D procedurais que existiam antes (utils/models3d.ts):
// geometria 3D fica refem do angulo da camera — uma espada vista de perfil
// virava um risco na tela — enquanto um icone 2D encara sempre o observador e
// le igual em qualquer posicao. Sao inline (sem download, sem dependencia de
// fonte de emoji) e herdam cor via `currentColor`.
//
// viewBox 24x24 em todos, para poderem ser trocados sem mexer no layout.
const CAMINHOS: Record<Categoria, string> = {
  // Espadas cruzadas
  batalha:
    'M4 3l10 10M20 3L10 13M6.5 15.5L3 19l2 2 3.5-3.5M17.5 15.5L21 19l-2 2-3.5-3.5',
  // Templo/edificio com colunas
  construcao: 'M3 21h18M5 21V10M9 21V10M15 21V10M19 21V10M2 10h20L12 3 2 10z',
  // Ancora
  naval: 'M12 7v14M12 7a2.5 2.5 0 100-5 2.5 2.5 0 000 5M5 12H3a9 9 0 0018 0h-2M8 10h8',
  // Coroa
  politico: 'M3 8l3.5 3L12 5l5.5 6L21 8l-2 10H5L3 8z',
  // Livro aberto
  cultural: 'M12 7v13M12 7C10 5 7 4.5 3 5v13c4-.5 7 0 9 2M12 7c2-2 5-2.5 9-2v13c-4-.5-7 0-9 2',
  // Losango (simbolo neutro, sem marcar nenhuma religiao especifica)
  religioso: 'M12 2l6 10-6 10-6-10 6-10z',
  // Bussola
  descoberta: 'M12 2a10 10 0 100 20 10 10 0 000-20zM15.5 8.5l-2 5-5 2 2-5 5-2z',
  // Circulo simples: evento sensivel (epidemia, desastre) pede marcador
  // sobrio, nao icone ilustrativo. Ver VISUAL.md.
  desastre: 'M12 4a8 8 0 100 16 8 8 0 000-16z',
};

const PREENCHIDOS: ReadonlySet<Categoria> = new Set<Categoria>([
  'politico',
  'religioso',
  'desastre',
]);

export function svgDaCategoria(categoria: Categoria, tamanho: number): string {
  const caminho = CAMINHOS[categoria] ?? CAMINHOS.desastre;
  const preenchido = PREENCHIDOS.has(categoria);
  return (
    `<svg viewBox="0 0 24 24" width="${tamanho}" height="${tamanho}" ` +
    `fill="${preenchido ? 'currentColor' : 'none'}" stroke="currentColor" ` +
    `stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ` +
    `aria-hidden="true"><path d="${caminho}"/></svg>`
  );
}
