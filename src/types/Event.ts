export type IncertezaData = 'exata' | 'ano' | 'decada' | 'seculo' | 'aproximada';

// Ver VISUAL.md — tabela "Sistema de marcadores por categoria".
export type Categoria =
  | 'batalha'
  | 'construcao'
  | 'naval'
  | 'politico'
  | 'cultural'
  | 'religioso'
  | 'descoberta'
  | 'desastre';

// Substitui o modelo 3D genérico da categoria por um mais específico, pra
// eventos onde vale a pena — ex: as pirâmides ganham formato de pirâmide em
// vez do prédio genérico de "construção". Ver utils/models3d.ts.
export type Modelo3D = 'piramide' | 'pessoa' | 'barco';

export interface HistoricalEvent {
  id: string;
  titulo: string;
  resumo: string;
  data_inicio: string;
  data_fim: string;
  incerteza_data: IncertezaData;
  lat: number;
  lng: number;
  local_nome_epoca: string;
  local_nome_atual: string;
  geocoding_fonte: string;
  confianca_local: number;
  nivel_importancia: 1 | 2 | 3 | 4 | 5;
  era: string;
  categoria: Categoria;
  modelo3D?: Modelo3D;
  atores: string[];
  tags: string[];
}
