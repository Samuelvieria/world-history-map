import type { HistoricalEvent } from '../types/Event';
import { getYear, formatYear } from '../utils/date';

interface EventPanelProps {
  event: HistoricalEvent | null;
  onClose: () => void;
}

export default function EventPanel({ event, onClose }: EventPanelProps) {
  if (!event) return null;

  const anoInicio = formatYear(getYear(event.data_inicio));
  const anoFim = formatYear(getYear(event.data_fim));
  const periodo = event.data_inicio === event.data_fim ? anoInicio : `${anoInicio} – ${anoFim}`;

  return (
    <aside className="event-panel">
      <button className="event-panel__close" onClick={onClose} aria-label="Fechar">
        ×
      </button>
      <h2>{event.titulo}</h2>
      <p className="event-panel__periodo">
        {periodo}
        {event.incerteza_data !== 'exata' && (
          <span className="event-panel__incerteza"> (data {event.incerteza_data})</span>
        )}
      </p>
      <p className="event-panel__local">
        {event.local_nome_epoca}
        {event.local_nome_epoca !== event.local_nome_atual && ` (hoje: ${event.local_nome_atual})`}
      </p>
      <p className="event-panel__resumo">{event.resumo}</p>
      <div className="event-panel__atores">
        {event.atores.map((ator) => (
          <span key={ator} className="event-panel__tag">
            {ator}
          </span>
        ))}
      </div>
      <p className="event-panel__meta">
        Importância: {event.nivel_importancia}/5 · Fonte da localização: {event.geocoding_fonte}
      </p>
    </aside>
  );
}
