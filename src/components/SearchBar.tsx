import { useMemo, useState } from 'react';
import type { HistoricalEvent } from '../types/Event';
import { normalize } from '../utils/text';
import { getYear, formatYear } from '../utils/date';

interface SearchBarProps {
  events: HistoricalEvent[];
  onSelect: (event: HistoricalEvent) => void;
}

const MAX_RESULTADOS = 6;

export default function SearchBar({ events, onSelect }: SearchBarProps) {
  const [termo, setTermo] = useState('');

  const resultados = useMemo(() => {
    const busca = normalize(termo.trim());
    if (!busca) return [];
    return events
      .filter((evento) => {
        const alvo = normalize(
          [evento.titulo, evento.local_nome_epoca, evento.local_nome_atual, ...evento.atores, ...evento.tags].join(
            ' ',
          ),
        );
        return alvo.includes(busca);
      })
      .slice(0, MAX_RESULTADOS);
  }, [events, termo]);

  function selecionar(evento: HistoricalEvent) {
    onSelect(evento);
    setTermo('');
  }

  return (
    <div className="search-bar">
      <input
        type="text"
        value={termo}
        onChange={(e) => setTermo(e.target.value)}
        placeholder="Buscar evento, local ou ator..."
        className="search-bar__input"
      />
      {resultados.length > 0 && (
        <ul className="search-bar__resultados">
          {resultados.map((evento) => (
            <li key={evento.id}>
              <button className="search-bar__resultado" onClick={() => selecionar(evento)}>
                <span className="search-bar__resultado-titulo">{evento.titulo}</span>
                <span className="search-bar__resultado-ano">{formatYear(getYear(evento.data_inicio))}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
