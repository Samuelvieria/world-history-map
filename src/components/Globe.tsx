import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import GlobeGL, { type GlobeMethods } from 'react-globe.gl';
import type { PositionedEvent } from '../utils/geo';
import { CATEGORIAS } from '../utils/categorias';
import { svgDaCategoria } from '../utils/icones';
import type { Feicao } from '../utils/geojson';

function corParaRgb(hex: string): string {
  const valor = parseInt(hex.replace('#', ''), 16);
  return `${(valor >> 16) & 255}, ${(valor >> 8) & 255}, ${valor & 255}`;
}

// Tiles da NASA GIBS (dominio publico), duas camadas conforme o zoom — sem
// nuvens e sem ruas/fronteiras modernas em nenhuma delas, coerente com um
// globo historico, onde uma malha viaria de 2026 seria anacronica.
//
// LONGE (mundo/pais): "Shaded relief + bathymetry", 500 m/pixel,
// cobre oceano (com textura de fundo) e terra. Nivel 8 e' o teto DESTA
// camada — nivel 9 responde HTTP 400 (verificado).
const GIBS_CAMADA_LONGE = 'BlueMarble_ShadedRelief_Bathymetry';
const GIBS_NIVEL_MAX_LONGE = 8;

// PERTO (dentro de estado): ASTER GDEM, ~30 m/pixel (16x mais fino),
// resolve o pixelado que aparecia ao aproximar de um estado (ex.: Brasil).
// Verificado do mesmo jeito: nivel 12 responde 200, nivel 13 responde 400.
// Trade-off aceito: e' relevo (DEM), NAO tem dado de oceano — mar vira cor
// solida nesta camada. So' entra em uso alem do nivel 8, onde o usuario ja'
// esta' dentro de um pais/estado e o oceano normalmente saiu de quadro.
const GIBS_CAMADA_PERTO = 'ASTER_GDEM_Color_Shaded_Relief';
const GIBS_NIVEL_MAX_PERTO = 12;

// O teto de nivel e' imposto por `globeTileEngineMaxLevel` no componente, e
// nao aqui: a assinatura exige devolver string, entao nao ha' como recusar um
// tile por este caminho.
function urlDoTile(x: number, y: number, nivel: number): string {
  // REST do GIBS e' {TileMatrix}/{TileRow}/{TileCol} — ou seja, y antes de x,
  // ao contrario do padrao {z}/{x}/{y} de OSM.
  const [camada, nivelMax] =
    nivel > GIBS_NIVEL_MAX_LONGE
      ? [GIBS_CAMADA_PERTO, GIBS_NIVEL_MAX_PERTO]
      : [GIBS_CAMADA_LONGE, GIBS_NIVEL_MAX_LONGE];
  return (
    `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${camada}` +
    `/default/GoogleMapsCompatible_Level${nivelMax}/${nivel}/${y}/${x}.jpeg`
  );
}

export interface GlobeHandle {
  flyTo: (lat: number, lng: number, altitude?: number) => void;
}

interface GlobeProps {
  events: PositionedEvent[];
  /** Regioes clicaveis do nivel atual do drill-down. */
  regioes: Feicao[];
  rotuloDaRegiao: (f: Feicao) => string;
  /** Cor de preenchimento da regiao, em rgba. */
  corDaRegiao: (f: Feicao) => string;
  /** Mostrar o titulo ao lado do icone (so' onde nao vira amontoado). */
  mostrarRotulos: boolean;
  selectedId: string | null;
  onSelectEvent: (event: PositionedEvent) => void;
  onSelectRegiao: (f: Feicao) => void;
  onZoom: (altitude: number) => void;
}

const Globe = forwardRef<GlobeHandle, GlobeProps>(function Globe(
  {
    events,
    regioes,
    rotuloDaRegiao,
    corDaRegiao,
    mostrarRotulos,
    selectedId,
    onSelectEvent,
    onSelectRegiao,
    onZoom,
  },
  ref,
) {
  const globeRef = useRef<GlobeMethods | undefined>(undefined);

  useImperativeHandle(ref, () => ({
    flyTo(lat, lng, altitude = 0.5) {
      globeRef.current?.pointOfView({ lat, lng, altitude }, 1000);
    },
  }));

  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;
    globe.pointOfView({ lat: 20, lng: 10, altitude: 2.2 }, 0);
    const controls = globe.controls();
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.4;
    // A rotação automática move a câmera entre o mousedown e o mouseup de um
    // clique, o que faz o OrbitControls interpretar o gesto como arraste e
    // suprimir o onPointClick. Parar a rotação assim que o usuário interage
    // evita que os pontos fiquem "difíceis de clicar".
    const pararRotacao = () => {
      controls.autoRotate = false;
    };
    controls.addEventListener('start', pararRotacao);
    return () => controls.removeEventListener('start', pararRotacao);
  }, []);

  function selecionarEClicar(dado: object) {
    const evento = dado as PositionedEvent;
    onSelectEvent(evento);
    globeRef.current?.pointOfView({ lat: evento.displayLat, lng: evento.displayLng, altitude: 0.5 }, 1000);
  }

  // Anel pulsante: destaca os eventos de importância máxima sempre, e o
  // evento selecionado no momento (mesmo que não seja de importância máxima).
  // O anel e' plano, deitado na superficie — nao acrescenta volume.
  const eventosComAnel = events.filter(
    (e) => e.nivel_importancia >= 4 || e.id === selectedId,
  );

  return (
    <GlobeGL
      ref={globeRef}
      globeTileEngineUrl={urlDoTile}
      globeTileEngineMaxLevel={GIBS_NIVEL_MAX_PERTO}
      backgroundColor="#00000000"
      showAtmosphere
      atmosphereColor="#5b9bd5"
      atmosphereAltitude={0.16}
      onZoom={(pov) => onZoom(pov.altitude)}
      // Regioes clicaveis do drill-down (mundo -> pais -> estado).
      // Altitude baixinha e cor quase transparente: a malha serve de alvo de
      // clique e de contorno, sem tapar o relevo dos tiles.
      polygonsData={regioes}
      polygonGeoJsonGeometry={(f) =>
        // O .d.ts do react-globe.gl declara `coordinates: number[]`, mas
        // GeoJSON de Polygon e' number[][][] e de MultiPolygon e'
        // number[][][][] — a tipagem publicada esta' errada. Em runtime a
        // geometria e' repassada intacta ao three-globe, que espera o GeoJSON
        // de verdade; o cast so' contorna o tipo incorreto.
        (f as Feicao).geometry as unknown as { type: string; coordinates: number[] }
      }
      polygonAltitude={0.006}
      polygonCapColor={(f) => corDaRegiao(f as Feicao)}
      polygonSideColor={() => 'rgba(90, 155, 213, 0.05)'}
      polygonStrokeColor={() => 'rgba(190, 220, 255, 0.55)'}
      polygonLabel={(f) => rotuloDaRegiao(f as Feicao)}
      onPolygonClick={(f) => onSelectRegiao(f as Feicao)}
      polygonsTransitionDuration={300}
      ringsData={eventosComAnel}
      ringLat="displayLat"
      ringLng="displayLng"
      ringColor={(e: object) => {
        const evento = e as PositionedEvent;
        const selecionado = evento.id === selectedId;
        const rgb = selecionado ? '255, 255, 255' : corParaRgb(CATEGORIAS[evento.categoria]?.cor ?? '#94a3b8');
        return (t: number) => `rgba(${rgb}, ${1 - t})`;
      }}
      ringMaxRadius={(e: object) => ((e as PositionedEvent).id === selectedId ? 4.5 : 3)}
      ringPropagationSpeed={1.2}
      ringRepeatPeriod={1800}
      // Marcadores: icone 2D em SVG, nao mais modelo 3D. Geometria 3D ficava
      // refem do angulo da camera (uma espada de perfil virava um risco);
      // o icone 2D encara sempre o observador e le igual de qualquer posicao.
      htmlElementsData={events}
      htmlLat="displayLat"
      htmlLng="displayLng"
      htmlAltitude={0.012}
      htmlElement={(d) => {
        const evento = d as PositionedEvent;
        const cor = CATEGORIAS[evento.categoria]?.cor ?? '#94a3b8';
        const tamanho = 15 + evento.nivel_importancia * 3;
        const selecionado = evento.id === selectedId;

        const el = document.createElement('div');
        el.className = `globe-marker${selecionado ? ' globe-marker--ativo' : ''}`;
        el.title = evento.titulo;

        const disco = document.createElement('span');
        disco.className = 'globe-marker__icone';
        disco.style.color = cor;
        disco.style.width = `${tamanho}px`;
        disco.style.height = `${tamanho}px`;
        disco.innerHTML = svgDaCategoria(evento.categoria, Math.round(tamanho * 0.62));
        el.appendChild(disco);

        // No mundo ha' eventos demais para caber texto: os rotulos se
        // sobrepoem e um tapa o outro. So' nos niveis internos,
        // onde sobram poucos eventos, o titulo aparece; fora dai vale o
        // tooltip nativo (title) no hover.
        if (mostrarRotulos) {
          const texto = document.createElement('span');
          texto.className = 'globe-marker__texto';
          texto.textContent = evento.titulo;
          el.appendChild(texto);
        }

        el.addEventListener('click', (clickEvent) => {
          clickEvent.stopPropagation();
          selecionarEClicar(evento);
        });
        return el;
      }}
    />
  );
});

export default Globe;
