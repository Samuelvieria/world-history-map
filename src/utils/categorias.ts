import type { Categoria } from '../types/Event';

interface DefinicaoCategoria {
  nome: string;
  cor: string;
}

// Paleta de pigmento da direção "Gravura" (VISUAL.md) — tons desaturados,
// nenhum é o default de uma lib de UI. Vermelho fica reservado só pra
// batalha/guerra (semântico), não é mais "a cor da marca" usada em tudo.
// O ícone de cada categoria é o SVG de `icones.ts` (mesmo desenho nos
// marcadores do globo, na legenda e no painel de evento) — não existe
// mais um glifo Unicode separado pra essas duas telas.
export const CATEGORIAS: Record<Categoria, DefinicaoCategoria> = {
  batalha: { nome: 'Batalha / guerra', cor: '#8a4030' },
  construcao: { nome: 'Construção / estrutura', cor: '#b8862b' },
  naval: { nome: 'Naval / expedição', cor: '#45607a' },
  politico: { nome: 'Político / tratado', cor: '#7a5a89' },
  cultural: { nome: 'Cultural / científico', cor: '#3f7a70' },
  religioso: { nome: 'Religioso', cor: '#a68b3f' },
  descoberta: { nome: 'Descoberta / exploração', cor: '#6a9788' },
  desastre: { nome: 'Desastre / epidemia', cor: '#6b6858' },
};
