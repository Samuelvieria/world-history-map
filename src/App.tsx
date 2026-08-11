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
import { aplicarOffsetColisoes } from './utils/geo';
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
  const [, setAltitude] = useState(ALTITUDE_INICIAL);
  const [selectedEvent, setSelectedEvent] = useState<HistoricalEvent | null>(null);

  const [trilha, setTrilha] = useState<PassoNavegacao[]>(TRILHA_INICIAL);
  const [regioes, setRegioes] = useState<Feicao[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  const globeRef = useRef<GlobeHandle>(null);
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

  async function handleSelecionarRegiao(feicao: Feicao) {
    const proximo = proximoNivel(passoAtual.nivel);
    if (!proximo) return;

    // `nome` filtra os dados (ingles) e `rotulo` vai pra tela (portugues).
    let nome: string;
    let rotulo: string;
    let recorte: Feicao[];

    if (passoAtual.nivel === 'mundo') {
      nome = idDoPais(feicao);
      rotulo = nomeDoPais(feicao);
      // O poligono clicado e' o grosseiro (110m, so' de renderizacao — ver
      // paisesParaMundo). O recorte de evento precisa da versao precisa
      // (50m) do MESMO pais, senao volta o bug de evento costeiro caindo
      // fora da fronteira que `URL_PAISES` documenta.
      const preciso = await paisPreciso(nome);
      recorte = preciso ? [preciso] : [feicao];
    } else {
      nome = nomeDoEstado(feicao);
      rotulo = nome;
      recorte = [feicao];
    }

    setTrilha((atual) => [...atual, { nivel: proximo, nome, rotulo, recorte }]);
    setSelectedEvent(null);
    voar(recorte);
  }

  function handleVoltarPara(indice: number) {
    setTrilha((atual) => atual.slice(0, indice + 1));
    setSelectedEvent(null);
    voar(trilha[indice].recorte);
  }

  function handleRangeChange(novoInicio: number, novoFim: number) {
    setAnoInicio(novoInicio);
    setAnoFim(novoFim);
  }

  function handleSearchSelect(evento: HistoricalEvent) {
    const anoEvento = getYear(evento.data_inicio);
    if (anoEvento < anoInicio) setAnoInicio(Math.max(ANO_MIN, anoEvento - 10));
    if (anoEvento > anoFim) setAnoFim(Math.min(ANO_MAX, anoEvento + 10));
    if (evento.nivel_importancia < minImportancia) setMinImportancia(evento.nivel_importancia);

    // A busca e' global: se o resultado esta' fora da regiao aberta, volta
    // para o mundo em vez de "encontrar" um evento que fica invisivel.
    const recorte = passoAtual.recorte
      .map((f) => f.geometry)
      .filter((g): g is NonNullable<typeof g> => g !== null);
    const foraDaRegiao =
      recorte.length > 0 && !pontoNaRegiao(evento.lng, evento.lat, recorte);
    if (foraDaRegiao || evento.nivel_importancia < importanciaDoNivel) {
      setTrilha(TRILHA_INICIAL);
    }

    setSelectedEvent(evento);
    globeRef.current?.flyTo(evento.lat, evento.lng, 0.5);
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
          onSelectEvent={setSelectedEvent}
          corDaRegiao={corDaRegiao}
          mostrarRotulos={passoAtual.nivel === 'pais' || passoAtual.nivel === 'estado'}
          onSelectRegiao={handleSelecionarRegiao}
          onZoom={setAltitude}
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
