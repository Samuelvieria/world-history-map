import { ERAS, ANO_MIN, ANO_MAX } from '../utils/eras';
import { formatYear } from '../utils/date';

interface TimelineSliderProps {
  anoInicio: number;
  anoFim: number;
  onChange: (anoInicio: number, anoFim: number) => void;
}

const RANGE = ANO_MAX - ANO_MIN;

function toPercent(ano: number): number {
  return ((ano - ANO_MIN) / RANGE) * 100;
}

export default function TimelineSlider({ anoInicio, anoFim, onChange }: TimelineSliderProps) {
  function handleInicioChange(value: number) {
    onChange(Math.min(value, anoFim), anoFim);
  }

  function handleFimChange(value: number) {
    onChange(anoInicio, Math.max(value, anoInicio));
  }

  return (
    <div className="timeline">
      <div className="timeline__eras">
        {ERAS.map((era) => (
          <div
            key={era.id}
            className="timeline__era"
            style={{
              left: `${toPercent(era.anoInicio)}%`,
              width: `${toPercent(era.anoFim) - toPercent(era.anoInicio)}%`,
              backgroundColor: era.cor,
            }}
            title={era.nome}
          >
            <span className="timeline__era-label">{era.nome}</span>
          </div>
        ))}
      </div>

      <div className="timeline__track">
        <div
          className="timeline__selection"
          style={{
            left: `${toPercent(anoInicio)}%`,
            width: `${toPercent(anoFim) - toPercent(anoInicio)}%`,
          }}
        />
        <input
          type="range"
          min={ANO_MIN}
          max={ANO_MAX}
          value={anoInicio}
          onChange={(e) => handleInicioChange(Number(e.target.value))}
          className="timeline__handle timeline__handle--inicio"
        />
        <input
          type="range"
          min={ANO_MIN}
          max={ANO_MAX}
          value={anoFim}
          onChange={(e) => handleFimChange(Number(e.target.value))}
          className="timeline__handle timeline__handle--fim"
        />
      </div>

      <div className="timeline__labels">
        <span>{formatYear(anoInicio)}</span>
        <span>{formatYear(anoFim)}</span>
      </div>
    </div>
  );
}
