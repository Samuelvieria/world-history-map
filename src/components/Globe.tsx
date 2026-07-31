import { useEffect, useRef } from 'react';
import GlobeGL, { type GlobeMethods } from 'react-globe.gl';
import type { HistoricalEvent } from '../types/Event';

const CORES_IMPORTANCIA: Record<number, string> = {
  1: '#94a3b8',
  2: '#60a5fa',
  3: '#fbbf24',
  4: '#fb923c',
  5: '#ef4444',
};

interface GlobeProps {
  events: HistoricalEvent[];
  onSelectEvent: (event: HistoricalEvent) => void;
}

export default function Globe({ events, onSelectEvent }: GlobeProps) {
  const globeRef = useRef<GlobeMethods | undefined>(undefined);

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

  return (
    <GlobeGL
      ref={globeRef}
      globeImageUrl="//unpkg.com/three-globe/example/img/earth-blue-marble.jpg"
      backgroundColor="#00000000"
      pointsData={events}
      pointLat="lat"
      pointLng="lng"
      pointAltitude={0.01}
      pointRadius={(e) => 0.25 + ((e as HistoricalEvent).nivel_importancia) * 0.12}
      pointColor={(e) => CORES_IMPORTANCIA[(e as HistoricalEvent).nivel_importancia] ?? '#ef4444'}
      pointLabel={(e) => (e as HistoricalEvent).titulo}
      onPointClick={(e) => onSelectEvent(e as HistoricalEvent)}
    />
  );
}
