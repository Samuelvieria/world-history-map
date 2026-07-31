interface ImportanceFilterProps {
  minImportancia: number;
  onChange: (valor: number) => void;
}

const NIVEIS = [1, 2, 3, 4, 5];

export default function ImportanceFilter({ minImportancia, onChange }: ImportanceFilterProps) {
  return (
    <div className="importance-filter">
      <span className="importance-filter__label">Importância mínima</span>
      <div className="importance-filter__bar">
        {NIVEIS.map((nivel) => (
          <button
            key={nivel}
            className={`importance-filter__segment ${nivel <= minImportancia ? 'importance-filter__segment--active' : ''}`}
            onClick={() => onChange(nivel)}
            aria-label={`Importância mínima ${nivel}`}
          >
            {nivel}
          </button>
        ))}
      </div>
    </div>
  );
}
