"""Passo 1 do IA.md, ponta a ponta, com avaliacao contra gabarito.

Um spike que so' imprime a saida bonita nao diz se funcionou. Este script
compara o resultado com um gabarito escrito a mao para o paragrafo de teste,
de modo que o veredito seja medido, nao impressionista.

Uso:
    ./.venv/bin/python spike_passo1.py
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

from extracao import EventoCandidato, ExtratorGLiNER
from extracao.geocoding import resolver as resolver_geocoding

AMOSTRA = Path(__file__).parent / "amostras" / "paragrafo_teste.txt"
FONTE_ID = "amostra_teste_v1"

# Gabarito: o que uma pessoa esperaria extrair deste paragrafo.
# (local esperado, categoria esperada, trecho de data esperado)
GABARITO = [
    ("Constantinopla", "batalha", "1453"),
    ("Messina", "desastre", "1347"),
    ("Gizé", "construcao", "2560"),
    ("Paris", "politico", "1789"),
]


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    return sem_acento.lower()


def mostrar_candidato(indice: int, cand: EventoCandidato) -> None:
    print(f"\n{'─' * 72}")
    print(f"CANDIDATO {indice}")
    print(f"{'─' * 72}")

    def linha(nome: str, campo) -> None:
        if campo is None:
            print(f"  {nome:<18} (ausente)")
            return
        p = campo.proveniencia
        print(
            f"  {nome:<18} {campo.valor!r}\n"
            f"  {'':<18} conf={campo.confianca:.2f} rotulo={campo.rotulo_origem!r} "
            f"span=({p.span_inicio},{p.span_fim})"
        )

    linha("titulo", cand.titulo)
    linha("categoria", cand.categoria)
    linha("local_nome_epoca", cand.local_nome_epoca)

    if cand.atores:
        nomes = ", ".join(f"{a.valor!r}({a.confianca:.2f})" for a in cand.atores)
        print(f"  {'atores':<18} {nomes}")
    else:
        print(f"  {'atores':<18} (nenhum)")

    if cand.datas_brutas:
        datas = ", ".join(f"{d.valor!r}({d.confianca:.2f})" for d in cand.datas_brutas)
        print(f"  {'datas_brutas':<18} {datas}")
    else:
        print(f"  {'datas_brutas':<18} (nenhuma)")

    # Passo 5 ainda nao existe — mostrar explicitamente que nao ha coordenada.
    geo = (
        resolver_geocoding(cand.local_nome_epoca.valor)
        if cand.local_nome_epoca
        else None
    )
    print(f"  {'lat/lng':<18} {geo if geo else '(stub — passo 5 nao implementado)'}")

    faltando = cand.campos_faltando()
    print(f"  {'completo?':<18} {cand.esta_completo()}" + (f" faltando={faltando}" if faltando else ""))
    print(f"  {'proveniencia ok?':<18} {cand.proveniencia_integra()}")
    print(f"  {'status':<18} {cand.status}")


def avaliar(candidatos: list[EventoCandidato]) -> None:
    print(f"\n{'=' * 72}")
    print("AVALIACAO CONTRA GABARITO")
    print(f"{'=' * 72}")

    acertos_local = acertos_categoria = acertos_data = 0

    for local_esp, categoria_esp, data_esp in GABARITO:
        # Casa o candidato pela mencao ao local esperado no trecho da frase.
        casado = next(
            (
                c
                for c in candidatos
                if c.local_nome_epoca
                and normalizar(local_esp) in normalizar(c.local_nome_epoca.valor)
            ),
            None,
        )
        if casado is None:
            # Sem local extraido, tenta casar pela data — assim distinguimos
            # "nao achou o evento" de "achou o evento mas perdeu o local".
            casado = next(
                (
                    c
                    for c in candidatos
                    if any(data_esp in d.valor for d in c.datas_brutas)
                ),
                None,
            )

        if casado is None:
            print(f"\n  [PERDIDO]  {local_esp}: nenhum candidato correspondente")
            continue

        tem_local = casado.local_nome_epoca is not None and normalizar(
            local_esp
        ) in normalizar(casado.local_nome_epoca.valor)
        tem_categoria = (
            casado.categoria is not None and casado.categoria.valor == categoria_esp
        )
        tem_data = any(data_esp in d.valor for d in casado.datas_brutas)

        acertos_local += tem_local
        acertos_categoria += tem_categoria
        acertos_data += tem_data

        marca = lambda ok: "ok " if ok else "NAO"  # noqa: E731
        categoria_obtida = casado.categoria.valor if casado.categoria else None
        print(
            f"\n  {local_esp}:\n"
            f"    local     [{marca(tem_local)}]\n"
            f"    categoria [{marca(tem_categoria)}] esperada={categoria_esp!r} "
            f"obtida={categoria_obtida!r}\n"
            f"    data      [{marca(tem_data)}] esperava conter {data_esp!r}"
        )

    total = len(GABARITO)
    print(f"\n{'─' * 72}")
    print(f"  local:     {acertos_local}/{total}")
    print(f"  categoria: {acertos_categoria}/{total}")
    print(f"  data:      {acertos_data}/{total}")
    print(f"{'─' * 72}")


def main() -> None:
    texto = AMOSTRA.read_text(encoding="utf-8")
    print("TEXTO DE ENTRADA (sintetico, escrito para teste — nao e' trecho de livro):")
    print(texto)

    extrator = ExtratorGLiNER()
    print("Carregando modelo...")
    candidatos = extrator.extrair(texto, fonte_id=FONTE_ID, pagina=1)
    print(f"{len(candidatos)} candidato(s) a evento.")

    for i, cand in enumerate(candidatos, start=1):
        mostrar_candidato(i, cand)

    avaliar(candidatos)

    completos = sum(c.esta_completo() for c in candidatos)
    print(
        f"\nProntos para revisao com campos minimos: {completos}/{len(candidatos)}\n"
        "Nenhum vai pro mapa sem aprovacao humana (passo 8)."
    )


if __name__ == "__main__":
    main()
