const NIVEIS: Array<{ nivel: number; cor: string }> = [
  { nivel: 1, cor: '#94a3b8' },
  { nivel: 2, cor: '#60a5fa' },
  { nivel: 3, cor: '#fbbf24' },
  { nivel: 4, cor: '#fb923c' },
  { nivel: 5, cor: '#ef4444' },
];

export default function Legend() {
  return (
    <div className="legend">
      <span className="legend__label">Importância</span>
      <div className="legend__itens">
        {NIVEIS.map(({ nivel, cor }) => (
          <div key={nivel} className="legend__item">
            <span className="legend__dot" style={{ backgroundColor: cor, width: 6 + nivel * 2, height: 6 + nivel * 2 }} />
            <span>{nivel}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
