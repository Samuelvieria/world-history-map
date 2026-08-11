"""Passo 8 do IA.md: fila de revisao humana, em linha de comando.

Le um JSON gerado por `ingerir_pdf.py`, mostra cada candidato PENDENTE com a
proveniencia por baixo (pra decisao informada — ver `Proveniencia.trecho`:
uso interno, nunca vai pra tela do mapa), e deixa a pessoa aprovar, rejeitar
ou pular. Grava a decisao de volta no MESMO arquivo a cada resposta, nao so'
no final — interromper no meio (Ctrl+C, fechar o terminal) nao perde nada do
que ja' foi decidido.

NAO grava no mapa. Isso e' proposital, por duas razoes:
  1. Aprovar aqui so' muda `status` para "aprovado" — vira'/HistoricalEvent
     e' um passo separado (fase 1 do CLAUDE.md, com backend), pra manter a
     separacao de tipos que `modelo.py` documenta.
  2. Mesmo aprovado, um candidato sem lat/lng (geocoding, passo 5, ainda
     stub) nao tem onde aparecer no globo — fica sinalizado explicitamente
     no resumo final, nao escondido.

Uso:
    ./.venv/Scripts/python.exe revisar.py amostras/saida_historia_antiga.json
    ./.venv/Scripts/python.exe revisar.py amostras/saida_historia_antiga.json --so-completos
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CAMPOS_MINIMOS = ("titulo", "categoria", "local_nome_epoca")


def esta_completo(c: dict[str, Any]) -> bool:
    return all(c.get(campo) is not None for campo in CAMPOS_MINIMOS) and bool(c.get("datas_brutas"))


def _linha_campo(nome: str, campo: dict[str, Any] | None) -> str:
    if campo is None:
        return f"  {nome:<14} (ausente)"
    return f"  {nome:<14} {campo['valor']!r}  (conf={campo['confianca']:.2f}, rotulo={campo['rotulo_origem']!r})"


def mostrar(c: dict[str, Any], indice: int, total: int) -> None:
    print(f"\n{'=' * 72}")
    print(f"[{indice}/{total}]  fonte={c['fonte_id']!r}")
    print(f"{'=' * 72}")

    print(_linha_campo("titulo", c.get("titulo")))
    print(_linha_campo("categoria", c.get("categoria")))
    print(_linha_campo("local", c.get("local_nome_epoca")))

    datas = c.get("datas_brutas") or []
    if datas:
        print(f"  {'data_bruta':<14} {datas[0]['valor']!r}")
    else:
        print(f"  {'data_bruta':<14} (ausente)")
    print(f"  {'data normal.':<14} {c['data_inicio']} .. {c['data_fim']} ({c['incerteza_data']})")

    atores = c.get("atores") or []
    if atores:
        print(f"  {'atores':<14} {', '.join(a['valor'] for a in atores)}")

    print(f"  {'resumo':<14} {c['resumo']!r}")
    print(f"  {'lat/lng':<14} {c['lat']}, {c['lng']} (fonte={c['geocoding_fonte']})")

    # Contexto da fonte, so' pra quem revisa — nunca vai pro mapa (ver docstring).
    ancora = c.get("titulo") or c.get("categoria") or c.get("local_nome_epoca")
    if ancora:
        p = ancora["proveniencia"]
        texto = c["texto_origem"]
        inicio = max(0, p["span_inicio"] - 60)
        fim = min(len(texto), p["span_fim"] + 60)
        pagina = f" (pagina {p['pagina']})" if p.get("pagina") else ""
        print(f"\n  trecho-fonte{pagina}, so' para conferencia:")
        print(f"    ...{texto[inicio:fim]}...")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("arquivo", type=Path)
    parser.add_argument(
        "--so-completos", action="store_true", help="mostra so' candidatos com titulo+categoria+local+data"
    )
    args = parser.parse_args()

    dados: list[dict[str, Any]] = json.loads(args.arquivo.read_text(encoding="utf-8"))

    def salvar() -> None:
        args.arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

    pendentes = [c for c in dados if c["status"] == "pendente"]
    if args.so_completos:
        pendentes = [c for c in pendentes if esta_completo(c)]

    print(f"{len(pendentes)} candidato(s) pendente(s) de {len(dados)} no arquivo.")
    if not pendentes:
        print("Nada para revisar.")
        return

    for i, c in enumerate(pendentes, 1):
        mostrar(c, i, len(pendentes))
        while True:
            resposta = input("\n  [a]provar / [r]ejeitar / [p]ular / [s]air: ").strip().lower()
            if resposta in ("a", "aprovar"):
                c["status"] = "aprovado"
                break
            if resposta in ("r", "rejeitar"):
                c["status"] = "rejeitado"
                break
            if resposta in ("p", "pular", ""):
                break
            if resposta in ("s", "sair"):
                salvar()
                print(f"\nProgresso salvo em {args.arquivo}.")
                return
            print("  resposta invalida — use a, r, p ou s.")
        salvar()  # a cada decisao, nao so' no final

    aprovados = sum(1 for c in dados if c["status"] == "aprovado")
    rejeitados = sum(1 for c in dados if c["status"] == "rejeitado")
    ainda_pendentes = sum(1 for c in dados if c["status"] == "pendente")
    sem_coordenada = sum(1 for c in dados if c["status"] == "aprovado" and c["lat"] is None)

    print(f"\n{'=' * 72}")
    print(f"Fim da fila. aprovados={aprovados} rejeitados={rejeitados} pendentes={ainda_pendentes}")
    if sem_coordenada:
        print(
            f"ATENCAO: {sem_coordenada} aprovado(s) sem lat/lng — geocoding (passo 5) "
            "ainda e' stub, esses candidatos nao tem onde aparecer no globo ainda."
        )


if __name__ == "__main__":
    main()
