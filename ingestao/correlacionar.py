"""Correlaciona candidatos APROVADOS de fontes (livros) DIFERENTES que
provavelmente descrevem o MESMO acontecimento histórico — ver
`extracao/correlacao.py`. Implementa o que o CLAUDE.md já previa na seção
"Validação por consenso" e nunca tinha sido construído: em vez de dois
marcadores duplicados no mapa para o mesmo evento, um evento corroborado por
N fontes (ver `publicar.py`, que funde por `grupo_correlacao`).

A regra só SUGERE o par por similaridade de título/local/data — nunca funde
sozinha. Cada par sugerido é mostrado com a divergência de data/local em
destaque (quando houver), e a pessoa decide: juntar, ou não é o mesmo
acontecimento. A resposta é salva de volta nos arquivos de origem a cada
decisão, no mesmo espírito de `revisar.py`.

Limitação conhecida: com 3+ arquivos, a correlação é só par a par — se A~B é
confirmado primeiro, um C que também descreve o mesmo evento pode não ser
oferecido pra correlacionar com A ou B (a transitividade não é resolvida).
Não é problema com os 2 livros de amostra de hoje; vira relevante se um
terceiro livro entrar.

Uso:
    ./.venv/Scripts/python.exe correlacionar.py amostras/saida_historia_antiga.json amostras/saida_historia_moderna.json
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any

from extracao.correlacao import candidatos_correlacionados


def _chave(c: dict[str, Any]) -> str:
    """Identificador estavel de um candidato ANTES de publicar.py existir
    (que so' cria `id` na hora de publicar) — usado so' pra lembrar 'esse
    par ja' foi perguntado e a resposta foi separar', sem perguntar de novo."""
    return f"{c['fonte_id']}::{c['titulo']['proveniencia']['span_inicio']}"


def _resumo(c: dict[str, Any]) -> str:
    titulo = c["titulo"]["valor"] if c["titulo"] else "(sem titulo)"
    local = c["local_nome_epoca"]["valor"] if c["local_nome_epoca"] else "(sem local)"
    return f"{titulo!r} — local={local!r} — {c['data_inicio']}..{c['data_fim']} — fonte={c['fonte_id']!r}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("arquivos", type=Path, nargs="+")
    args = parser.parse_args()

    if len(args.arquivos) < 2:
        print("Precisa de pelo menos 2 arquivos — correlacao e' ENTRE fontes diferentes.")
        return

    dados: dict[Path, list[dict[str, Any]]] = {
        p: json.loads(p.read_text(encoding="utf-8")) for p in args.arquivos
    }

    def salvar(caminho: Path) -> None:
        caminho.write_text(json.dumps(dados[caminho], ensure_ascii=False, indent=2), encoding="utf-8")

    sugeridos = 0
    confirmados = 0

    for i, arq_a in enumerate(args.arquivos):
        for arq_b in args.arquivos[i + 1 :]:
            aprovados_a = [c for c in dados[arq_a] if c["status"] == "aprovado" and not c.get("grupo_correlacao")]
            aprovados_b = [c for c in dados[arq_b] if c["status"] == "aprovado" and not c.get("grupo_correlacao")]
            pares = candidatos_correlacionados(aprovados_a, aprovados_b)
            if not pares:
                continue

            print(f"\n{arq_a.name} x {arq_b.name}: {len(pares)} par(es) candidato(s) a corroboracao.")

            for par in pares:
                ca, cb = par.candidato_a, par.candidato_b
                # ja' agrupado ou ja' respondido "separar" numa rodada anterior?
                if ca.get("grupo_correlacao") or cb.get("grupo_correlacao"):
                    continue
                if _chave(cb) in (ca.get("_correlacoes_rejeitadas") or []):
                    continue

                sugeridos += 1
                print(f"\n{'=' * 72}")
                print(f"Pontuacao de similaridade: {par.pontuacao:.2f}")
                print(f"  A) {_resumo(ca)}")
                print(f"  B) {_resumo(cb)}")

                if ca["data_inicio"] != cb["data_inicio"] or ca["data_fim"] != cb["data_fim"]:
                    print(f"  ATENCAO — datas divergem: A={ca['data_inicio']}..{ca['data_fim']}  B={cb['data_inicio']}..{cb['data_fim']}")
                local_a = ca["local_nome_epoca"]["valor"] if ca["local_nome_epoca"] else None
                local_b = cb["local_nome_epoca"]["valor"] if cb["local_nome_epoca"] else None
                if local_a != local_b:
                    print(f"  ATENCAO — local diverge: A={local_a!r}  B={local_b!r}")

                resposta = input("\n  Mesmo acontecimento? [j]untar / [s]eparar / [p]ular: ").strip().lower()
                if resposta in ("j", "juntar"):
                    grupo = f"grp_{uuid.uuid4().hex[:12]}"
                    ca["grupo_correlacao"] = grupo
                    cb["grupo_correlacao"] = grupo
                    confirmados += 1
                    salvar(arq_a)
                    salvar(arq_b)
                elif resposta in ("s", "separar"):
                    ca.setdefault("_correlacoes_rejeitadas", []).append(_chave(cb))
                    cb.setdefault("_correlacoes_rejeitadas", []).append(_chave(ca))
                    salvar(arq_a)
                    salvar(arq_b)
                # 'p'ular: nao marca nada, oferece de novo na proxima rodada

    print(f"\n{'=' * 72}")
    print(f"Pares sugeridos: {sugeridos}  |  confirmados (juntados): {confirmados}")
    if not sugeridos:
        print("Nenhum par acima do limiar de similaridade entre os arquivos dados.")


if __name__ == "__main__":
    main()
