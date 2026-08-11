"""Ingestao real (passos 1, 3, 6, 7 do IA.md) contra um PDF de amostra.

Diferenca do `spike_passo1.py`: aquele mede contra um paragrafo sintetico
escrito a mao, com gabarito. Este roda contra um livro de verdade, sem
gabarito — o que dá pra medir aqui e' volume e sanidade estrutural
(completude, proveniencia), nao acuracia. Acuracia exige revisao humana
(passo 8), que ainda nao existe.

Uso:
    ./.venv/Scripts/python.exe ingerir_pdf.py amostras/livro.pdf --paginas 5
    ./.venv/Scripts/python.exe ingerir_pdf.py amostras/livro.pdf --inicio 10 --saida saida.json
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from extracao import ExtratorGLiNER
from extracao.pdf import contar_paginas_sem_texto, extrair_paginas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument(
        "--paginas", type=int, default=None, help="limita as N primeiras paginas com texto (teste rapido)"
    )
    parser.add_argument(
        "--inicio", type=int, default=1, help="pula para a pagina N (pula capa/sumario/creditos)"
    )
    parser.add_argument("--saida", type=Path, default=None, help="salva os candidatos em JSON")
    args = parser.parse_args()

    print(f"Lendo {args.pdf}...")
    paginas = extrair_paginas(args.pdf)
    vazias = contar_paginas_sem_texto(paginas)
    print(f"{len(paginas)} paginas no PDF, {vazias} sem texto extraivel (possivel imagem/scan, sem OCR aqui).")

    paginas_alvo = [p for p in paginas if p.numero >= args.inicio and p.texto.strip()]
    if args.paginas is not None:
        paginas_alvo = paginas_alvo[: args.paginas]

    if not paginas_alvo:
        print("Nenhuma pagina com texto no recorte pedido.")
        return

    print(
        f"Processando paginas {paginas_alvo[0].numero}..{paginas_alvo[-1].numero} "
        f"({len(paginas_alvo)} paginas com texto)."
    )

    extrator = ExtratorGLiNER()
    fonte_id = args.pdf.stem

    todos_candidatos = []
    inicio_tempo = time.time()
    for pagina in paginas_alvo:
        candidatos = extrator.extrair(pagina.texto, fonte_id=fonte_id, pagina=pagina.numero)
        todos_candidatos.extend(candidatos)
        print(f"  pagina {pagina.numero}: {len(candidatos)} candidato(s)")
    duracao = time.time() - inicio_tempo

    completos = sum(c.esta_completo() for c in todos_candidatos)
    integros = sum(c.proveniencia_integra() for c in todos_candidatos)
    com_data = sum(c.data_inicio is not None for c in todos_candidatos)
    com_resumo = sum(c.resumo is not None for c in todos_candidatos)

    print(f"\n{'=' * 72}")
    print(f"{len(todos_candidatos)} candidatos em {duracao:.1f}s "
          f"({duracao / len(paginas_alvo):.2f}s/pagina, {len(paginas_alvo) / duracao * 60:.1f} paginas/min)")
    print(f"completos (campos minimos):   {completos}/{len(todos_candidatos)}")
    print(f"proveniencia integra:         {integros}/{len(todos_candidatos)}")
    print(f"data normalizada (passo 6):   {com_data}/{len(todos_candidatos)}")
    print(f"resumo gerado (passo 7):      {com_resumo}/{len(todos_candidatos)}")

    if integros != len(todos_candidatos):
        print(
            "\nATENCAO: ha' candidato com proveniencia que nao confere. "
            "Isso nunca deveria acontecer — investigar antes de confiar em qualquer saida."
        )

    if args.saida:
        dados = [asdict(c) for c in todos_candidatos]
        args.saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nSalvo em {args.saida}")


if __name__ == "__main__":
    main()
