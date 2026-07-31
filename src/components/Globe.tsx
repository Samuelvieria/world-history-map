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

// Altura do cilindro (points layer) codifica a importância — ver VISUAL.md,
// "Codificação de importância": nivel_importancia 1 quase raso, 5 bem alto.
function alturaPorImportancia(nivelImportancia: number): number {
  return 0.01 + (nivelImportancia - 1) * 0.045;
}

const CLOUDS_URL = '//unpkg.com/three-globe/example/clouds/clouds.png';
const CLOUDS_ALTITUDE = 0.006;
const CLOUDS_ROTATION_DEG_POR_FRAME = -0.006;

export interface GlobeHandle {
  flyTo: (lat: number, lng: number, altitude?: number) => void;
}

// Ver VISUAL.md, "Level-of-detail": zoom distante só pontos simples; zoom
// médio ganha o ícone 2D por categoria; zoom perto nos eventos de maior
// destaque ganha também o rótulo de texto.
const ALTITUDE_LIMITE_ICONES = 1.6;
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
  const eventosComAnel = events.filter(
    (e) => e.nivel_importancia >= 4 || e.id === selectedId,
  );

  const eventosCom3D = altitude <= ALTITUDE_LIMITE_ICONES ? events : [];
  const eventosComRotulo =
    altitude <= ALTITUDE_LIMITE_ROTULOS ? events.filter((e) => e.nivel_importancia === 5) : [];

  return (
    <GlobeGL
      ref={globeRef}
      globeImageUrl="//unpkg.com/three-globe/example/img/earth-blue-marble.jpg"
      bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
      backgroundColor="#00000000"
      showAtmosphere
      atmosphereColor="#3a7bd5"
      atmosphereAltitude={0.18}
      onZoom={(pov) => onZoom(pov.altitude)}
      pointsData={events}
      pointLat="displayLat"
      pointLng="displayLng"
      pointAltitude={(e) => alturaPorImportancia((e as PositionedEvent).nivel_importancia)}
      pointRadius={(e) => 0.2 + ((e as PositionedEvent).nivel_importancia - 1) * 0.03}
      pointColor={(e) => CATEGORIAS[(e as PositionedEvent).categoria]?.cor ?? '#94a3b8'}
      pointLabel={(e) => (e as PositionedEvent).titulo}
      onPointClick={selecionarEClicar}
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
      objectAltitude={(e) => alturaPorImportancia((e as PositionedEvent).nivel_importancia)}
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
      htmlElementsData={eventosComRotulo}
      htmlLat="displayLat"
      htmlLng="displayLng"
      htmlAltitude={(e) => alturaPorImportancia((e as PositionedEvent).nivel_importancia) + 0.06}
      htmlElement={(d) => {
        const evento = d as PositionedEvent;
        const el = document.createElement('div');
        el.className = 'globe-marker';
        const texto = document.createElement('span');
        texto.className = 'globe-marker__texto';
        texto.textContent = evento.titulo;
        el.appendChild(texto);
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
