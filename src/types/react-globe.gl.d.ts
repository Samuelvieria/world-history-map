// Preenche uma lacuna de tipagem do react-globe.gl 2.38.
//
// `globeTileEngineMaxLevel` existe de fato em runtime: esta declarada em
// globe.gl e o react-kapsule repassa qualquer prop que nao seja metodo nem
// init-prop, chamando o metodo homonimo do componente. Mas ela nao aparece no
// .d.ts publicado, ao contrario de `globeTileEngineUrl`.
//
// Sem ela nao da' pra limitar o nivel maximo de tile, e o engine (default 17)
// pediria niveis que a camada do GIBS nao serve — nivel 9 ja' responde 400.
declare module 'react-globe.gl' {
  interface GlobeProps {
    globeTileEngineMaxLevel?: number;
  }
}

export {};
