import type { CSSProperties } from 'react';
import { CATEGORIAS } from '../utils/categorias';
import { svgDaCategoria } from '../utils/icones';
import type { Categoria } from '../types/Event';

const NIVEIS_IMPORTANCIA = [1, 2, 3, 4, 5];

export default function Legend() {
  return (
    <div className="legend">
      <div className="legend__secao">
        <span className="legend__label">Categoria</span>
        <div className="legend__categorias">
          {Object.entries(CATEGORIAS).map(([id, { nome, cor }]) => (
            <div key={id} className="legend__categoria" title={nome}>
              <span
                className="legend__categoria-icone"
                style={{ '--cor': cor } as CSSProperties}
                dangerouslySetInnerHTML={{ __html: svgDaCategoria(id as Categoria, 11) }}
              />
            </div>
          ))}
        </div>
      </div>
      <div className="legend__secao">
        <span className="legend__label">Importância (tamanho)</span>
        <div className="legend__itens legend__itens--bolinhas">
          {NIVEIS_IMPORTANCIA.map((nivel) => (
            <div key={nivel} className="legend__item">
              <span
                className="legend__bolinha"
                style={{ width: 5 + nivel * 2, height: 5 + nivel * 2 }}
              />
              <span>{nivel}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
