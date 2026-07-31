import { useMemo, useRef, useState } from 'react';
import Globe, { type GlobeHandle } from './components/Globe';
import TimelineSlider from './components/TimelineSlider';
import ImportanceFilter from './components/ImportanceFilter';
import EventPanel from './components/EventPanel';
import SearchBar from './components/SearchBar';
import Legend from './components/Legend';
import eventsData from './data/events.json';
import type { HistoricalEvent } from './types/Event';
import { getYear } from './utils/date';
import { ANO_MIN, ANO_MAX } from './utils/eras';
import { importanciaMinimaPorZoom } from './utils/zoom';
import { aplicarOffsetColisoes } from './utils/geo';
import './App.css';

const events = eventsData as HistoricalEvent[];
const ALTITUDE_INICIAL = 2.2;

function App() {
  const [anoInicio, setAnoInicio] = useState(ANO_MIN);
  const [anoFim, setAnoFim] = useState(ANO_MAX);
  const [minImportancia, setMinImportancia] = useState(1);
  const [altitude, setAltitude] = useState(ALTITUDE_INICIAL);
  const [selectedEvent, setSelectedEvent] = useState<HistoricalEvent | null>(null);
  const globeRef = useRef<GlobeHandle>(null);

  const importanciaEfetiva = Math.max(minImportancia, importanciaMinimaPorZoom(altitude));

  const eventosFiltrados = useMemo(() => {
    return events.filter((evento) => {
      const anoEvento = getYear(evento.data_inicio);
      return anoEvento >= anoInicio && anoEvento <= anoFim && evento.nivel_importancia >= importanciaEfetiva;
    });
  }, [anoInicio, anoFim, importanciaEfetiva]);

  const eventosPosicionados = useMemo(() => aplicarOffsetColisoes(eventosFiltrados), [eventosFiltrados]);

  function handleRangeChange(novoInicio: number, novoFim: number) {
    setAnoInicio(novoInicio);
    setAnoFim(novoFim);
  }

  function handleSearchSelect(evento: HistoricalEvent) {
    const anoEvento = getYear(evento.data_inicio);
    if (anoEvento < anoInicio) setAnoInicio(Math.max(ANO_MIN, anoEvento - 10));
    if (anoEvento > anoFim) setAnoFim(Math.min(ANO_MAX, anoEvento + 10));
    if (evento.nivel_importancia < minImportancia) setMinImportancia(evento.nivel_importancia);

    setSelectedEvent(evento);
    globeRef.current?.flyTo(evento.lat, evento.lng, 0.5);
  }

  return (
    <div className="app">
      <header className="app__header">
        <h1>Globo Histórico Interativo</h1>
        <span className="app__contador">
          {eventosFiltrados.length} de {events.length} eventos
        </span>
      </header>

      <SearchBar events={events} onSelect={handleSearchSelect} />

      <div className="app__globe">
        <Globe
          ref={globeRef}
          events={eventosPosicionados}
          altitude={altitude}
          onSelectEvent={setSelectedEvent}
          onZoom={setAltitude}
        />
      </div>

      <ImportanceFilter minImportancia={minImportancia} onChange={setMinImportancia} />

      <Legend />

      <TimelineSlider anoInicio={anoInicio} anoFim={anoFim} onChange={handleRangeChange} />

      <EventPanel event={selectedEvent} onClose={() => setSelectedEvent(null)} />
    </div>
  );
}

export default App;
