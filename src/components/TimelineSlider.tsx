import { useEffect, useState, type CSSProperties } from 'react';
import { ERAS, ANO_MIN, ANO_MAX, type Era } from '../utils/eras';
import { formatYear } from '../utils/date';

interface TimelineSliderProps {
  anoInicio: number;
  anoFim: number;
  onChange: (anoInicio: number, anoFim: number) => void;
}

function toPercent(ano: number, min: number, max: number): number {
  return ((ano - min) / (max - min)) * 100;
}

export default function TimelineSlider({ anoInicio, anoFim, onChange }: TimelineSliderProps) {
  // null = "Tudo" (escala completa, -10000 a 2026). Selecionar um periodo
  // troca a escala da barra fina para o intervalo dele — sem isso, a Idade
  // Contemporanea (237 anos) ocupa ~2% de uma barra que vai de -10000 a
  // 2026, e arrastar o cabo pra escolher um ano especifico ali fica
  // impraticavel. Os botoes resolvem isso: cada periodo ganha a MESMA
  // largura de botao, nao proporcional a duracao.
  const [eraAtiva, setEraAtiva] = useState<Era | null>(null);

  // Se o intervalo mudar por fora (ex.: busca que pula pra outra era) e sair
  // dos limites da era ativa, volta pra "Tudo" em vez de deixar a barra de
  // selecao renderizar fora do trilho.
  useEffect(() => {
    if (eraAtiva && (anoInicio < eraAtiva.anoInicio || anoFim > eraAtiva.anoFim)) {
      setEraAtiva(null);
    }
  }, [anoInicio, anoFim, eraAtiva]);

  const min = eraAtiva ? eraAtiva.anoInicio : ANO_MIN;
  const max = eraAtiva ? eraAtiva.anoFim : ANO_MAX;

  function selecionarEra(era: Era | null) {
    setEraAtiva(era);
    onChange(era ? era.anoInicio : ANO_MIN, era ? era.anoFim : ANO_MAX);
  }

  function handleInicioChange(value: number) {
    onChange(Math.min(value, anoFim), anoFim);
  }

  function handleFimChange(value: number) {
    onChange(anoInicio, Math.max(value, anoInicio));
  }

  return (
    <div className="timeline">
      <div className="timeline__periodos">
        <button
          className={`timeline__periodo ${eraAtiva === null ? 'timeline__periodo--ativo' : ''}`}
          onClick={() => selecionarEra(null)}
        >
          Tudo
        </button>
        {ERAS.map((era) => (
          <button
            key={era.id}
            className={`timeline__periodo ${eraAtiva?.id === era.id ? 'timeline__periodo--ativo' : ''}`}
            style={{ '--cor-periodo': era.cor } as CSSProperties}
            onClick={() => selecionarEra(era)}
          >
            {era.nome}
          </button>
        ))}
      </div>

      {/* A faixa colorida por era so' faz sentido como visao geral de "Tudo"
          — com um periodo ativo, a barra inteira e' so' aquele periodo. */}
      {eraAtiva === null && (
        <div className="timeline__eras">
          {ERAS.map((era) => (
            <div
              key={era.id}
              className="timeline__era"
              style={{
                left: `${toPercent(era.anoInicio, min, max)}%`,
                width: `${toPercent(era.anoFim, min, max) - toPercent(era.anoInicio, min, max)}%`,
                backgroundColor: era.cor,
              }}
              title={era.nome}
            >
              <span className="timeline__era-label">{era.nome}</span>
            </div>
          ))}
        </div>
      )}

      <div className="timeline__track">
        <div
          className="timeline__selection"
          style={{
            left: `${toPercent(anoInicio, min, max)}%`,
            width: `${toPercent(anoFim, min, max) - toPercent(anoInicio, min, max)}%`,
          }}
        />
        <input
          type="range"
          min={min}
          max={max}
          value={anoInicio}
          onChange={(e) => handleInicioChange(Number(e.target.value))}
          className="timeline__handle timeline__handle--inicio"
        />
        <input
          type="range"
          min={min}
          max={max}
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
