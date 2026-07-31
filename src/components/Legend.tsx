import { CATEGORIAS } from '../utils/categorias';

const NIVEIS_IMPORTANCIA = [1, 2, 3, 4, 5];

export default function Legend() {
  return (
    <div className="legend">
      <div className="legend__secao">
        <span className="legend__label">Categoria</span>
        <div className="legend__categorias">
          {Object.entries(CATEGORIAS).map(([id, { nome, cor, icone }]) => (
            <div key={id} className="legend__categoria" title={nome}>
              <span className="legend__categoria-icone" style={{ background: cor }}>
                {icone}
              </span>
            </div>
          ))}
        </div>
      </div>
      <div className="legend__secao">
        <span className="legend__label">Importância (altura)</span>
        <div className="legend__itens">
          {NIVEIS_IMPORTANCIA.map((nivel) => (
            <div key={nivel} className="legend__item">
              <span className="legend__barra" style={{ height: 4 + nivel * 3 }} />
              <span>{nivel}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
