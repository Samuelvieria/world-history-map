import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import * as THREE from 'three';
import GlobeGL, { type GlobeMethods } from 'react-globe.gl';
import type { PositionedEvent } from '../utils/geo';
import { CATEGORIAS } from '../utils/categorias';
import { criarModeloParaEvento } from '../utils/models3d';

function corParaRgb(hex: string): string {
  const valor = parseInt(hex.replace('#', ''), 16);
  return `${(valor >> 16) & 255}, ${(valor >> 8) & 255}, ${valor & 255}`;
}

// Tiles da NASA GIBS (dominio publico). "Shaded relief + bathymetry" da'
// relevo de continente E de fundo de oceano, sem nuvens e sem ruas/fronteiras
// modernas — coerente com um globo historico, onde uma malha viaria de 2026
// seria anacronica.
//
// Detalhe cresce com o zoom, ao contrario de uma textura fixa: no nivel
// maximo equivale a ~65.536 px de largura, contra os 4.096 px da textura que
// vinha antes. Carrega so' os tiles visiveis.
//
// Nivel 8 e' o teto DESTA camada — nivel 9 responde HTTP 400 (verificado).
const GIBS_CAMADA = 'BlueMarble_ShadedRelief_Bathymetry';
const GIBS_NIVEL_MAX = 8;

// O teto de nivel e' imposto por `globeTileEngineMaxLevel` no componente, e
// nao aqui: a assinatura exige devolver string, entao nao ha' como recusar um
// tile por este caminho.
function urlDoTile(x: number, y: number, nivel: number): string {
  // REST do GIBS e' {TileMatrix}/{TileRow}/{TileCol} — ou seja, y antes de x,
  // ao contrario do padrao {z}/{x}/{y} de OSM.
  return (
    `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${GIBS_CAMADA}` +
    `/default/GoogleMapsCompatible_Level${GIBS_NIVEL_MAX}/${nivel}/${y}/${x}.jpeg`
  );
}

const CLOUDS_URL = '//unpkg.com/three-globe/example/clouds/clouds.png';
const CLOUDS_ALTITUDE = 0.006;
const CLOUDS_ROTATION_DEG_POR_FRAME = -0.006;

export interface GlobeHandle {
  flyTo: (lat: number, lng: number, altitude?: number) => void;
}

// Level-of-detail por altitude da camera (VISUAL.md). Longe: so' marcador 2D,
// que e' leve e sempre nitido. Perto: modelo 3D da categoria. Mais perto
// ainda: rotulo de texto nos eventos de maior destaque.
const ALTITUDE_LIMITE_3D = 1.6;
const ALTITUDE_LIMITE_ROTULOS = 1.0;

interface GlobeProps {
  events: PositionedEvent[];
  altitude: number;
  selectedId: string | null;
  onSelectEvent: (event: PositionedEvent) => void;
  onZoom: (altitude: number) => void;
}

const Globe = forwardRef<GlobeHandle, GlobeProps>(function Globe(
  { events, altitude, selectedId, onSelectEvent, onZoom },
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

  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;

    let cloudsMesh: THREE.Mesh | undefined;
    let frameId: number;
    new THREE.TextureLoader().load(CLOUDS_URL, (textura) => {
      const geometria = new THREE.SphereGeometry(
        globe.getGlobeRadius() * (1 + CLOUDS_ALTITUDE),
        75,
        75,
      );
      const material = new THREE.MeshPhongMaterial({ map: textura, transparent: true, opacity: 0.4 });
      cloudsMesh = new THREE.Mesh(geometria, material);
      globe.scene().add(cloudsMesh);

      const girar = () => {
        if (cloudsMesh) {
          cloudsMesh.rotation.y += (CLOUDS_ROTATION_DEG_POR_FRAME * Math.PI) / 180;
        }
        frameId = requestAnimationFrame(girar);
      };
      girar();
    });

    return () => {
      cancelAnimationFrame(frameId);
      if (cloudsMesh) globe.scene().remove(cloudsMesh);
    };
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

  const perto = altitude <= ALTITUDE_LIMITE_3D;
  const eventosCom3D = perto ? events : [];
  // Longe, todo evento vira um marcador 2D. Perto, o modelo 3D assume a forma
  // e so' os eventos de maior destaque mantem rotulo de texto.
  const eventosComMarcador2D = perto
    ? events.filter(
        (e) => altitude <= ALTITUDE_LIMITE_ROTULOS && e.nivel_importancia === 5,
      )
    : events;

  return (
    <GlobeGL
      ref={globeRef}
      globeTileEngineUrl={urlDoTile}
      globeTileEngineMaxLevel={GIBS_NIVEL_MAX}
      backgroundColor="#00000000"
      showAtmosphere
      atmosphereColor="#5b9bd5"
      atmosphereAltitude={0.16}
      onZoom={(pov) => onZoom(pov.altitude)}
      // Sem `pointsData`: a camada de pontos do react-globe.gl desenha
      // cilindros que sobem da superficie. Com a altura codificando
      // importancia, viravam tubos atravessando o globo — e vistos de angulo
      // raso, riscos coloridos pela tela. A forma agora vem do modelo 3D, e a
      // importancia, do tamanho + anel.
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
      objectsData={eventosCom3D}
      objectLat="displayLat"
      objectLng="displayLng"
      // Altitude 0: o modelo fica assentado no chao. Antes ele era erguido
      // junto com o cilindro e parecia flutuar no topo de um poste.
      objectAltitude={0}
      objectLabel={(e) => (e as PositionedEvent).titulo}
      objectThreeObject={(d) => {
        const evento = d as PositionedEvent;
        const modelo = criarModeloParaEvento(evento);
        // Modelos autorados em ~1-1.8 unidades; GLOBE_RADIUS do three-globe é
        // uma constante fixa (100), então a escala é um valor absoluto
        // calibrado visualmente, não derivado do raio do globo.
        const escala = 1.4 + (evento.nivel_importancia - 1) * 0.5;
        modelo.scale.set(escala, escala, escala);
        return modelo;
      }}
      onObjectClick={selecionarEClicar}
      htmlElementsData={eventosComMarcador2D}
      htmlLat="displayLat"
      htmlLng="displayLng"
      htmlAltitude={0.01}
      htmlElement={(d) => {
        const evento = d as PositionedEvent;
        const cor = CATEGORIAS[evento.categoria]?.cor ?? '#94a3b8';
        const el = document.createElement('div');
        el.className = 'globe-marker';

        if (perto) {
          const texto = document.createElement('span');
          texto.className = 'globe-marker__texto';
          texto.textContent = evento.titulo;
          el.appendChild(texto);
        } else {
          // Marcador 2D: um disco que sempre encara a camera. Nitido em
          // qualquer zoom e sem geometria 3D, entao nao vira "cano".
          const ponto = document.createElement('span');
          ponto.className = 'globe-marker__ponto';
          const tamanho = 7 + evento.nivel_importancia * 2;
          ponto.style.width = `${tamanho}px`;
          ponto.style.height = `${tamanho}px`;
          ponto.style.background = cor;
          ponto.style.boxShadow = `0 0 ${tamanho}px ${cor}`;
          el.appendChild(ponto);
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
