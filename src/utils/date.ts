// Datas de eventos podem ser anteriores ao ano 0 (ex: "-2560-01-01" = 2560 a.C.).
// `Date` do JS lida mal com anos estendidos/negativos de forma consistente entre
// engines, então extraímos o ano diretamente da string ISO em vez de parsear com Date.
export function getYear(dateStr: string): number {
  const match = dateStr.match(/^(-?\d+)/);
  return match ? parseInt(match[1], 10) : 0;
}

export function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} a.C.`;
  return `${year} d.C.`;
}
