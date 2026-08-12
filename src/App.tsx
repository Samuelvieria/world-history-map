import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Globe, { type GlobeHandle } from './components/Globe';
import TimelineSlider from './components/TimelineSlider';
import ImportanceFilter from './components/ImportanceFilter';
import EventPanel from './components/EventPanel';
import SearchBar from './components/SearchBar';
import Legend from './components/Legend';
import Breadcrumb from './components/Breadcrumb';
import eventsData from './data/events.json';
import type { HistoricalEvent } from './types/Event';
import { getYear } from './utils/date';
import { ANO_MIN, ANO_MAX } from './utils/eras';
import { aplicarOffsetColisoes, type PositionedEvent } from './utils/geo';
import {
  altitudePara,
  enquadrar,

  pontoNaRegiao,
  type Feicao,
} from './utils/geojson';
import {
  TRILHA_INICIAL,
  corDoContinente,
  importanciaMinimaDoNivel,
  proximoNivel,
  type CameraPose,
  type PassoNavegacao,
} from './utils/navegacao';
import {
  continenteDoPais,
  estadosDoPais,
  idDoPais,
  nomeDoEstado,
  nomeDoPais,
  paisesParaMundo,
  paisPreciso,
} from './utils/fronteiras';
import './App.css';

const events = eventsData as HistoricalEvent[];
const ALTITUDE_INICIAL = 2.2;

function App() {
  const [anoInicio, setAnoInicio] = useState(ANO_MIN);
  const [anoFim, setAnoFim] = useState(ANO_MAX);
  const [minImportancia, setMinImportancia] = useState(1);
  const [selectedEvent, setSelectedEvent] = useState<HistoricalEvent | null>(null);

  const [trilha, setTrilha] = useState<PassoNavegacao[]>(TRILHA_INICIAL);
  const [regioes, setRegioes] = useState<Feicao[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  const globeRef = useRef<GlobeHandle>(null);
  // Pose "ao vivo" da camera — nao e' state de proposito (mudaria a cada
  // frame de zoom/arraste). So' lida no momento de um clique, pra guardar
  // "de onde a pessoa estava saindo" no passo de navegacao que ela deixa.
  const camPoseRef = useRef<CameraPose>({ lat: 20, lng: 10, altitude: ALTITUDE_INICIAL });
  const passoAtual = trilha[trilha.length - 1];

  // Carrega as regioes clicaveis do nivel atual.
  useEffect(() => {
    let cancelado = false;

    async function carregar() {
      setCarregando(true);
      setAviso(null);
      try {
        let proximas: Feicao[] = [];

        if (passoAtual.nivel === 'mundo') {
          // 110m (grosseiro) so' aqui: e' o unico nivel sem recorte de
          // evento (nao importa precisao de fronteira) e o unico que desenha
          // ~180 poligonos ao mesmo tempo (importa MUITO o custo de vertice).
          proximas = await paisesParaMundo();
        } else if (passoAtual.nivel === 'pais') {
          proximas = await estadosDoPais(passoAtual.nome);
          if (!proximas.length) {
            setAviso('Sem divisão estadual disponível para este país nos dados abertos.');
          }
        }

        if (!cancelado) setRegioes(proximas);
      } catch (erro) {
        if (!cancelado) {
          setRegioes([]);
          setAviso(erro instanceof Error ? erro.message : 'Falha ao carregar fronteiras.');
        }
      } finally {
        if (!cancelado) setCarregando(false);
      }
    }

    carregar();
    return () => {
      cancelado = true;
    };
  }, [passoAtual]);

  const importanciaDoNivel = importanciaMinimaDoNivel(passoAtual.nivel);
  const importanciaEfetiva = Math.max(minImportancia, importanciaDoNivel);

  const eventosFiltrados = useMemo(() => {
    const recorte = passoAtual.recorte
      .map((f) => f.geometry)
      .filter((g): g is NonNullable<typeof g> => g !== null);
    return events.filter((evento) => {
      const anoEvento = getYear(evento.data_inicio);
      if (anoEvento < anoInicio || anoEvento > anoFim) return false;
      if (evento.nivel_importancia < importanciaEfetiva) return false;
      // Dentro de uma regiao, so' os eventos que caem nela de fato.
      if (recorte.length && !pontoNaRegiao(evento.lng, evento.lat, recorte)) {
        return false;
      }
      return true;
    });
  }, [anoInicio, anoFim, importanciaEfetiva, passoAtual]);

  const eventosPosicionados = useMemo(
    () => aplicarOffsetColisoes(eventosFiltrados),
    [eventosFiltrados],
  );

  const rotuloDaRegiao = useCallback(
    (f: Feicao) => (passoAtual.nivel === 'pais' ? nomeDoEstado(f) : nomeDoPais(f)),
    [passoAtual.nivel],
  );

  const corDaRegiao = useCallback(
    (f: Feicao) =>
      // So' no mundo a cor agrupa por continente; nos niveis internos todas
      // as regioes sao irmas, entao um tom neutro basta.
      passoAtual.nivel === 'mundo'
        ? corDoContinente(continenteDoPais(f))
        : 'rgba(90, 155, 213, 0.12)',
    [passoAtual.nivel],
  );

  function voar(feicoes: Feicao[]) {
    if (!feicoes.length) {
      globeRef.current?.flyTo(20, 10, ALTITUDE_INICIAL);
      return;
    }
    const { lat, lng, extensao } = enquadrar(feicoes.map((f) => f.geometry));
    globeRef.current?.flyTo(lat, lng, altitudePara(extensao));
  }

  // O poligono clicado e' o grosseiro (110m, so' de renderizacao — ver
  // paisesParaMundo). O recorte de evento precisa da versao precisa (50m)
  // do MESMO pais, senao volta o bug de evento costeiro caindo fora da
  // fronteira que `URL_PAISES` documenta. Compartilhado por todo caminho que
  // entra num pais — do mundo, saltando de outro pais, ou clicando um evento.
  async function construirPassoPais(feicaoPaisGrosseiro: Feicao): Promise<PassoNavegacao> {
    const nome = idDoPais(feicaoPaisGrosseiro);
    const rotulo = nomeDoPais(feicaoPaisGrosseiro);
    const preciso = await paisPreciso(nome);
    return { nivel: 'pais', nome, rotulo, recorte: preciso ? [preciso] : [feicaoPaisGrosseiro] };
  }

  /** Pais (da lista grosseira do mundo) cuja fronteira contem o ponto — usada
   * pra resolver clique fora dos estados (salto pais->pais) e clique em
   * evento (entrar no pais dele). None se o ponto cair no oceano ou num gap. */
  async function paisQueContemPonto(lng: number, lat: number): Promise<Feicao | undefined> {
    const todos = await paisesParaMundo();
    return todos.find((f) => f.geometry && pontoNaRegiao(lng, lat, [f.geometry]));
  }

  /** Id do pais do contexto atual (o passo 'pais' ativo, ou o pai do passo
   * 'estado' ativo) — null no mundo, onde nao ha' "outro pais" pra comparar. */
  function paisDoContextoAtual(): string | null {
    if (passoAtual.nivel === 'pais') return passoAtual.nome;
    if (passoAtual.nivel === 'estado') return trilha[trilha.length - 2]?.nome ?? null;
    return null;
  }

  async function handleSelecionarRegiao(feicao: Feicao) {
    const proximo = proximoNivel(passoAtual.nivel);
    if (!proximo) return;

    const passo: PassoNavegacao =
      passoAtual.nivel === 'mundo'
        ? await construirPassoPais(feicao)
        : { nivel: proximo, nome: nomeDoEstado(feicao), rotulo: nomeDoEstado(feicao), recorte: [feicao] };

    // Guarda a pose de onde a pessoa esta' saindo, no passo que ela deixa —
    // e' o que faz "voltar" restaurar a vista de verdade em vez de saltar
    // pra um ponto generico (ver CameraPose em utils/navegacao.ts).
    const poseAoSair = camPoseRef.current;
    setTrilha((atual) => {
      const comPoseSalva = [...atual];
      const ultimo = comPoseSalva.length - 1;
      comPoseSalva[ultimo] = { ...comPoseSalva[ultimo], camera: poseAoSair };
      return [...comPoseSalva, passo];
    });
    setSelectedEvent(null);
    voar(passo.recorte);
  }

  /** Clique no globo que nao acertou nenhum poligono — dentro de um pais, se
   * cair em OUTRO pais, salta direto pra ele (mundo fica intacto por baixo,
   * sem precisar voltar pro mundo primeiro pra escolher outro pais). */
  async function handleClicarPontoLivre(lat: number, lng: number) {
    if (passoAtual.nivel === 'mundo') return;

    const paisClicado = await paisQueContemPonto(lng, lat);
    if (!paisClicado || idDoPais(paisClicado) === paisDoContextoAtual()) return;

    const passo = await construirPassoPais(paisClicado);
    setTrilha((atual) => [atual[0], passo]);
    setSelectedEvent(null);
    voar(passo.recorte);
  }

  async function handleSelecionarEvento(evento: PositionedEvent) {
    setSelectedEvent(evento);

    const paisDoEvento = await paisQueContemPonto(evento.lng, evento.lat);
    if (!paisDoEvento || idDoPais(paisDoEvento) === paisDoContextoAtual()) return;

    const passo = await construirPassoPais(paisDoEvento);
    setTrilha((atual) => [atual[0], passo]);
    // Sem voar() aqui: o Globe.tsx ja' leva a camera pro ponto exato do
    // evento (selecionarEClicar) — isso so' sincroniza o contexto/breadcrumb
    // por baixo, pra nao ficar "olhando pra Roma com o filtro ainda no Egito".
  }

  function handleVoltarPara(indice: number) {
    const alvo = trilha[indice];
    if (alvo.camera) {
      globeRef.current?.flyTo(alvo.camera.lat, alvo.camera.lng, alvo.camera.altitude);
    } else {
      voar(alvo.recorte);
    }
    setTrilha((atual) => atual.slice(0, indice + 1));
    setSelectedEvent(null);
  }

  function handleRangeChange(novoInicio: number, novoFim: number) {
    setAnoInicio(novoInicio);
    setAnoFim(novoFim);
  }

  async function handleSearchSelect(evento: HistoricalEvent) {
    const anoEvento = getYear(evento.data_inicio);
    if (anoEvento < anoInicio) setAnoInicio(Math.max(ANO_MIN, anoEvento - 10));
    if (anoEvento > anoFim) setAnoFim(Math.min(ANO_MAX, anoEvento + 10));
    if (evento.nivel_importancia < minImportancia) setMinImportancia(evento.nivel_importancia);

    setSelectedEvent(evento);
    globeRef.current?.flyTo(evento.lat, evento.lng, 0.5);

    // A busca e' global: se o resultado esta' fora da regiao aberta, entra
    // direto no pais do evento (mesmo caminho de handleSelecionarEvento) em
    // vez de resetar pro mundo — perderia contexto sem necessidade, e o
    // mundo tem piso de importancia MAIOR que pais (5 vs 3), tornando o
    // proprio evento buscado ainda mais provavel de ficar escondido.
    const recorte = passoAtual.recorte
      .map((f) => f.geometry)
      .filter((g): g is NonNullable<typeof g> => g !== null);
    const dentroDaRegiaoAtual = recorte.length > 0 && pontoNaRegiao(evento.lng, evento.lat, recorte);
    if (dentroDaRegiaoAtual) return;

    const paisDoEvento = await paisQueContemPonto(evento.lng, evento.lat);
    if (!paisDoEvento) {
      setTrilha(TRILHA_INICIAL); // sem pais resolvido (ex. meio do oceano) — mundo e' o unico contexto que garante mostrar o evento
    } else if (idDoPais(paisDoEvento) !== paisDoContextoAtual()) {
      const passo = await construirPassoPais(paisDoEvento);
      setTrilha((atual) => [atual[0], passo]);
    }
  }

  return (
    <div className="app">
      {/* Visivel so' para leitor de tela — o titulo da aba do navegador ja'
          cumpre esse papel na tela; um H1 flutuante colidia com a busca. */}
      <h1 className="visualmente-oculto">Globo Histórico Interativo</h1>

      <SearchBar events={events} onSelect={handleSearchSelect} />

      <div className="app__globe">
        <Globe
          ref={globeRef}
          events={eventosPosicionados}
          regioes={regioes}
          rotuloDaRegiao={rotuloDaRegiao}
          selectedId={selectedEvent?.id ?? null}
          onSelectEvent={handleSelecionarEvento}
          corDaRegiao={corDaRegiao}
          mostrarRotulos={passoAtual.nivel === 'pais' || passoAtual.nivel === 'estado'}
          onSelectRegiao={handleSelecionarRegiao}
          onZoom={(pose) => { camPoseRef.current = pose; }}
          onClicarPontoLivre={handleClicarPontoLivre}
        />
      </div>

      <Breadcrumb
        trilha={trilha}
        carregando={carregando}
        aviso={aviso}
        contador={`${eventosFiltrados.length} de ${events.length} eventos`}
        onVoltarPara={handleVoltarPara}
      />

      <ImportanceFilter
        minImportancia={minImportancia}
        pisoNivel={importanciaDoNivel}
        onChange={setMinImportancia}
      />

      <Legend />

      <TimelineSlider anoInicio={anoInicio} anoFim={anoFim} onChange={handleRangeChange} />

      <EventPanel event={selectedEvent} onClose={() => setSelectedEvent(null)} />
    </div>
  );
}

export default App;
