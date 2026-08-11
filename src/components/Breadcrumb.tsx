import type { PassoNavegacao } from '../utils/navegacao';
import { rotuloDeRegiao } from '../utils/navegacao';

interface BreadcrumbProps {
  trilha: PassoNavegacao[];
  carregando: boolean;
  aviso: string | null;
  contador: string;
  onVoltarPara: (indice: number) => void;
}

export default function Breadcrumb({
  trilha,
  carregando,
  aviso,
  contador,
  onVoltarPara,
}: BreadcrumbProps) {
  const atual = trilha[trilha.length - 1];

  return (
    <nav className="breadcrumb" aria-label="Navegação por região">
      <div className="breadcrumb__trilha">
        {trilha.map((passo, indice) => {
          const ultimo = indice === trilha.length - 1;
          return (
            <span key={`${passo.nivel}-${passo.rotulo}`} className="breadcrumb__item">
              {indice > 0 && <span className="breadcrumb__sep">›</span>}
              {ultimo ? (
                <span className="breadcrumb__atual">{passo.rotulo}</span>
              ) : (
                <button className="breadcrumb__link" onClick={() => onVoltarPara(indice)}>
                  {passo.rotulo}
                </button>
              )}
            </span>
          );
        })}
        {carregando && <span className="breadcrumb__carregando">carregando…</span>}
        <span className="breadcrumb__sep">·</span>
        <span className="breadcrumb__contador">{contador}</span>
      </div>

      {/* As fronteiras vem do Natural Earth e sao as de hoje. Dizer isso na
          interface evita que o mapa afirme, por omissao, que a entidade
          existia no periodo selecionado. */}
      {atual.nivel !== 'mundo' && (
        <span className="breadcrumb__ressalva">{rotuloDeRegiao(atual)} (fronteira atual)</span>
      )}
      {aviso && <span className="breadcrumb__aviso">{aviso}</span>}
    </nav>
  );
}
