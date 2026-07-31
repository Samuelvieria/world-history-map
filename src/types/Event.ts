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
  atores: string[];
  tags: string[];
}
