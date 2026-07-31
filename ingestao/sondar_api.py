"""Sondagem da API do GLiNER — roda ANTES de construir o pipeline.

Motivo: o README oficial documenta a saída de `predict_entities` apenas como
`text` e `label`. Todo o IA.md depende de **span** (posição do trecho no texto
original) para a proveniência — "sem span, o campo não existe". Em vez de
assumir que `start`/`end` vêm na resposta, este script verifica na prática e
falha ruidosamente se não vierem.

Uso:
    ./.venv/bin/python sondar_api.py
"""

import json

from gliner import GLiNER

MODELO = "urchade/gliner_multi-v2.1"

TEXTO = (
    "Em 29 de maio de 1453, o sultao Mehmed II conquistou Constantinopla, "
    "pondo fim ao Imperio Bizantino."
)

ROTULOS = ["pessoa", "lugar", "data", "organizacao", "batalha"]


def main() -> None:
    print(f"Carregando {MODELO} (primeira vez baixa ~1,2 GB)...")
    modelo = GLiNER.from_pretrained(MODELO)
    print("Modelo carregado.\n")

    entidades = modelo.predict_entities(TEXTO, ROTULOS, threshold=0.5)

    print(f"Tipo do retorno: {type(entidades)}")
    print(f"Quantidade de entidades: {len(entidades)}\n")

    if not entidades:
        print("ATENCAO: nenhuma entidade retornada — nao da pra inspecionar a forma.")
        return

    print("=== Entidade crua (primeira) ===")
    print(json.dumps(entidades[0], ensure_ascii=False, indent=2, default=str))

    chaves = sorted(entidades[0].keys())
    print(f"\n=== Chaves presentes ===\n{chaves}")

    # A verificacao que motivou este script.
    tem_span = "start" in entidades[0] and "end" in entidades[0]
    print(f"\n=== Tem span (start/end)? {tem_span} ===")

    if tem_span:
        print("Conferindo se o span realmente indexa o texto original:")
        todos_batem = True
        for ent in entidades:
            fatia = TEXTO[ent["start"] : ent["end"]]
            bate = fatia == ent["text"]
            todos_batem = todos_batem and bate
            marca = "ok" if bate else "DIVERGE"
            print(
                f"  [{marca}] {ent['label']:<12} "
                f"({ent['start']:>3},{ent['end']:>3}) "
                f"texto={ent['text']!r} fatia={fatia!r}"
            )
        print(
            f"\nProveniencia por span viavel: {todos_batem}"
            if todos_batem
            else "\nATENCAO: span nao indexa o texto original — proveniencia quebrada."
        )
    else:
        print(
            "ATENCAO: sem start/end na saida. O IA.md exige span para proveniencia;\n"
            "seria preciso recuperar a posicao por busca do texto (fragil com\n"
            "repeticoes) ou trocar de abordagem."
        )

    print("\n=== Todas as entidades ===")
    for ent in entidades:
        print(f"  {ent['label']:<12} {ent['text']!r} score={ent.get('score')}")


if __name__ == "__main__":
    main()
