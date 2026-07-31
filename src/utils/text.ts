// Marcas diacríticas combinantes (acentos) na forma decomposta NFD.
const DIACRITICOS = new RegExp('[̀-ͯ]', 'g');

export function normalize(texto: string): string {
  return texto.toLowerCase().normalize('NFD').replace(DIACRITICOS, '');
}
