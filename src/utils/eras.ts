export interface Era {
  id: string;
  nome: string;
  anoInicio: number;
  anoFim: number;
  cor: string;
}

// Fronteiras simplificadas para a Fase 0 (esqueleto). São aproximações didáticas
// comuns (ex: queda de Roma em 476, queda de Constantinopla em 1453, Revolução
// Francesa em 1789), não uma cronologia acadêmica precisa — refinar quando o
// modelo de dados ganhar fontes reais (Fase 1+).
// Paleta desaturada da direção "Gravura" (VISUAL.md), não os tons padrão
// do Tailwind que estavam aqui antes.
export const ERAS: Era[] = [
  { id: 'pre_historia', nome: 'Pré-História', anoInicio: -10000, anoFim: -3300, cor: '#6b6858' },
  { id: 'idade_bronze', nome: 'Idade do Bronze', anoInicio: -3300, anoFim: -1200, cor: '#b8862b' },
  { id: 'idade_ferro', nome: 'Idade do Ferro', anoInicio: -1200, anoFim: 476, cor: '#6e4a26' },
  { id: 'idade_media', nome: 'Idade Média', anoInicio: 476, anoFim: 1453, cor: '#45607a' },
  { id: 'idade_moderna', nome: 'Idade Moderna', anoInicio: 1453, anoFim: 1789, cor: '#7a5a89' },
  { id: 'idade_contemporanea', nome: 'Idade Contemporânea', anoInicio: 1789, anoFim: 2026, cor: '#8a4030' },
];

export const ANO_MIN = ERAS[0].anoInicio;
export const ANO_MAX = ERAS[ERAS.length - 1].anoFim;

export function eraPorAno(ano: number): Era | undefined {
  return ERAS.find((e) => ano >= e.anoInicio && ano < e.anoFim);
}
