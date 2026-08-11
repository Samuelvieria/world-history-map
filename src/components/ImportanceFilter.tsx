interface ImportanceFilterProps {
  minImportancia: number;
  /**
   * Piso imposto pelo nivel de navegacao atual (ver `importanciaMinimaDoNivel`
   * em navegacao.ts) — no nivel mundo, por exemplo, so' aparece importancia 5
   * mesmo que o usuario tenha escolhido um minimo menor aqui.
   *
   * Sem essa prop o widget mentia: mostrava "1" selecionado enquanto o app so'
   * exibia eventos de importancia 5, sem nenhuma pista visual do porque.
   */
  pisoNivel: number;
  onChange: (valor: number) => void;
}

const NIVEIS = [1, 2, 3, 4, 5];

export default function ImportanceFilter({ minImportancia, pisoNivel, onChange }: ImportanceFilterProps) {
  const efetivo = Math.max(minImportancia, pisoNivel);

  return (
    <div className="importance-filter">
      <span className="importance-filter__label">
        Importância mínima
        {pisoNivel > minImportancia && (
          <span className="importance-filter__piso" title="Este nível de zoom só mostra os eventos mais importantes; aproxime para liberar os demais.">
            {' '}(travado em {pisoNivel} neste zoom)
          </span>
        )}
      </span>
      <div className="importance-filter__bar">
        {NIVEIS.map((nivel) => {
          const bloqueado = nivel > minImportancia && nivel <= pisoNivel;
          return (
            <button
              key={nivel}
              className={[
                'importance-filter__segment',
                nivel <= efetivo && 'importance-filter__segment--active',
                bloqueado && 'importance-filter__segment--bloqueado',
              ]
                .filter(Boolean)
                .join(' ')}
              onClick={() => onChange(nivel)}
              aria-label={`Importância mínima ${nivel}`}
              title={bloqueado ? 'Bloqueado pelo zoom atual, não pela sua escolha' : undefined}
            >
              {nivel}
            </button>
          );
        })}
      </div>
    </div>
  );
}
