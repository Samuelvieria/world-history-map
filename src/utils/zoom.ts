// Quanto mais afastada a câmera (altitude maior), menos importante um evento
// precisa ser pra ficar escondido: zoom out mostra só os grandes marcos;
// zoom in vai revelando os eventos secundários. Isso substitui a necessidade
// de agrupar/"clusterizar" pontos próximos — em vez de esconder por posição,
// escondemos por relevância até o usuário se aproximar o bastante.
const DEGRAUS: Array<{ altitudeMin: number; importanciaMinima: number }> = [
  { altitudeMin: 1.8, importanciaMinima: 5 },
  { altitudeMin: 1.2, importanciaMinima: 4 },
  { altitudeMin: 0.8, importanciaMinima: 3 },
  { altitudeMin: 0.5, importanciaMinima: 2 },
  { altitudeMin: 0, importanciaMinima: 1 },
];

export function importanciaMinimaPorZoom(altitude: number): number {
  const degrau = DEGRAUS.find((d) => altitude >= d.altitudeMin);
  return degrau ? degrau.importanciaMinima : 1;
}
