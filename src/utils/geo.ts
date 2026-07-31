import type { HistoricalEvent } from '../types/Event';

export interface PositionedEvent extends HistoricalEvent {
  displayLat: number;
  displayLng: number;
}

const RAIO_AFASTAMENTO_GRAUS = 0.35;

// Quando dois ou mais eventos caem exatamente no mesmo ponto (ex: dois marcos
// diferentes na mesma cidade), afasta os marcadores visualmente em círculo ao
// redor do local real, pra nenhum ficar escondido atrás do outro e todos
// continuarem clicáveis. A posição histórica real (lat/lng) não é alterada,
// só a posição de exibição do marcador.
export function aplicarOffsetColisoes(eventos: HistoricalEvent[]): PositionedEvent[] {
  const grupos = new Map<string, HistoricalEvent[]>();
  for (const evento of eventos) {
    const chave = `${evento.lat.toFixed(1)},${evento.lng.toFixed(1)}`;
    const grupo = grupos.get(chave);
    if (grupo) grupo.push(evento);
    else grupos.set(chave, [evento]);
  }

  const resultado: PositionedEvent[] = [];
  for (const grupo of grupos.values()) {
    if (grupo.length === 1) {
      const [evento] = grupo;
      resultado.push({ ...evento, displayLat: evento.lat, displayLng: evento.lng });
      continue;
    }
    grupo.forEach((evento, indice) => {
      const angulo = (2 * Math.PI * indice) / grupo.length;
      resultado.push({
        ...evento,
        displayLat: evento.lat + RAIO_AFASTAMENTO_GRAUS * Math.cos(angulo),
        displayLng: evento.lng + RAIO_AFASTAMENTO_GRAUS * Math.sin(angulo),
      });
    });
  }
  return resultado;
}
