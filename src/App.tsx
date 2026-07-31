import { useMemo, useState } from 'react';
import Globe from './components/Globe';
import TimelineSlider from './components/TimelineSlider';
import ImportanceFilter from './components/ImportanceFilter';
import EventPanel from './components/EventPanel';
import eventsData from './data/events.json';
import type { HistoricalEvent } from './types/Event';
import { getYear } from './utils/date';
import { ANO_MIN, ANO_MAX } from './utils/eras';
import './App.css';

const events = eventsData as HistoricalEvent[];

function App() {
  const [anoInicio, setAnoInicio] = useState(ANO_MIN);
  const [anoFim, setAnoFim] = useState(ANO_MAX);
  const [minImportancia, setMinImportancia] = useState(1);
  const [selectedEvent, setSelectedEvent] = useState<HistoricalEvent | null>(null);

  const eventosFiltrados = useMemo(() => {
    return events.filter((evento) => {
      const anoEvento = getYear(evento.data_inicio);
      return (
        anoEvento >= anoInicio &&
        anoEvento <= anoFim &&
        evento.nivel_importancia >= minImportancia
      );
    });
  }, [anoInicio, anoFim, minImportancia]);

  function handleRangeChange(novoInicio: number, novoFim: number) {
    setAnoInicio(novoInicio);
    setAnoFim(novoFim);
  }

  return (
    <div className="app">
      <header className="app__header">
        <h1>Globo Histórico Interativo</h1>
        <span className="app__contador">
          {eventosFiltrados.length} de {events.length} eventos
        </span>
      </header>

      <div className="app__globe">
        <Globe events={eventosFiltrados} onSelectEvent={setSelectedEvent} />
      </div>

      <ImportanceFilter minImportancia={minImportancia} onChange={setMinImportancia} />

      <TimelineSlider anoInicio={anoInicio} anoFim={anoFim} onChange={handleRangeChange} />

      <EventPanel event={selectedEvent} onClose={() => setSelectedEvent(null)} />
    </div>
  );
}

export default App;
