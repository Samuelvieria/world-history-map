import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import * as THREE from 'three';
import GlobeGL, { type GlobeMethods } from 'react-globe.gl';
import type { PositionedEvent } from '../utils/geo';

const CORES_IMPORTANCIA: Record<number, string> = {
  1: '#94a3b8',
  2: '#60a5fa',
  3: '#fbbf24',
  4: '#fb923c',
  5: '#ef4444',
};

function corParaRgb(hex: string): string {
  const valor = parseInt(hex.replace('#', ''), 16);
  return `${(valor >> 16) & 255}, ${(valor >> 8) & 255}, ${valor & 255}`;
}

const CLOUDS_URL = '//unpkg.com/three-globe/example/clouds/clouds.png';
const CLOUDS_ALTITUDE = 0.006;
const CLOUDS_ROTATION_DEG_POR_FRAME = -0.006;

export interface GlobeHandle {
  flyTo: (lat: number, lng: number, altitude?: number) => void;
}

// Abaixo desta altitude a câmera já está perto o bastante pra que os rótulos
// dos eventos de maior destaque não fiquem colados uns nos outros.
const ALTITUDE_LIMITE_ROTULOS = 1.0;

interface GlobeProps {
  events: PositionedEvent[];
  altitude: number;
  onSelectEvent: (event: PositionedEvent) => void;
  onZoom: (altitude: number) => void;
}

const Globe = forwardRef<GlobeHandle, GlobeProps>(function Globe(
  { events, altitude, onSelectEvent, onZoom },
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

  const eventosImportantes = events.filter((e) => e.nivel_importancia >= 4);
  const eventosDestaque = altitude <= ALTITUDE_LIMITE_ROTULOS ? events.filter((e) => e.nivel_importancia === 5) : [];

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
      pointAltitude={0.01}
      pointRadius={(e) => 0.16 + ((e as PositionedEvent).nivel_importancia - 1) * 0.15}
      pointColor={(e) => CORES_IMPORTANCIA[(e as PositionedEvent).nivel_importancia] ?? '#ef4444'}
      pointLabel={(e) => (e as PositionedEvent).titulo}
      onPointClick={selecionarEClicar}
      ringsData={eventosImportantes}
      ringLat="displayLat"
      ringLng="displayLng"
      ringColor={(e: object) => {
        const rgb = corParaRgb(CORES_IMPORTANCIA[(e as PositionedEvent).nivel_importancia] ?? '#ef4444');
        return (t: number) => `rgba(${rgb}, ${1 - t})`;
      }}
      ringMaxRadius={3}
      ringPropagationSpeed={1.2}
      ringRepeatPeriod={1800}
      htmlElementsData={eventosDestaque}
      htmlLat="displayLat"
      htmlLng="displayLng"
      htmlAltitude={0.02}
      htmlElement={(d) => {
        const evento = d as PositionedEvent;
        const el = document.createElement('div');
        el.className = 'globe-label-chip';
        el.textContent = evento.titulo;
        el.style.borderColor = CORES_IMPORTANCIA[evento.nivel_importancia] ?? '#ef4444';
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
