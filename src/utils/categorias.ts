import type { Categoria } from '../types/Event';

interface DefinicaoCategoria {
  nome: string;
  cor: string;
  // Ícone 2D simples (Unicode), não modelo 3D — ver VISUAL.md ("Adiado").
  // Categorias sensíveis (ex: desastre/epidemia) usam símbolo neutro de
  // propósito: respeito antes de estética.
  icone: string;
}

export const CATEGORIAS: Record<Categoria, DefinicaoCategoria> = {
  batalha: { nome: 'Batalha / guerra', cor: '#ef4444', icone: '⚔' },
  construcao: { nome: 'Construção / estrutura', cor: '#f59e0b', icone: '🏛' },
  naval: { nome: 'Naval / expedição', cor: '#3b82f6', icone: '⚓' },
  politico: { nome: 'Político / tratado', cor: '#a855f7', icone: '👑' },
  cultural: { nome: 'Cultural / científico', cor: '#14b8a6', icone: '📖' },
  religioso: { nome: 'Religioso', cor: '#eab308', icone: '◈' },
  descoberta: { nome: 'Descoberta / exploração', cor: '#06b6d4', icone: '🧭' },
  desastre: { nome: 'Desastre / epidemia', cor: '#6b7280', icone: '●' },
};
