# Globo Histórico Interativo

Aplicação web com um globo terrestre interativo onde acontecimentos históricos
aparecem como pontos clicáveis. Veja [CLAUDE.md](./CLAUDE.md) para o contexto
completo do projeto, stack e roadmap por fases.

## Estado atual: Fase 0 (esqueleto, sem IA)

React + [react-globe.gl](https://github.com/vasturiano/react-globe.gl) exibindo
10 eventos de `src/data/events.json`, com:

- Timeline de duas alças (filtra por ano, com faixas nomeadas por era)
- Filtro por nível de importância
- Painel de resumo ao clicar num ponto

## Rodando localmente

```bash
npm install
npm run dev
```
