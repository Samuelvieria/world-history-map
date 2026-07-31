"""Segmentacao de texto em frases.

PROVISORIO. O IA.md define spaCy como a ferramenta do passo 2. Esta versao por
regex existe so' para destravar o spike do passo 1 sem baixar mais um modelo
(o disco desta maquina esta em 95%). Trocar por spaCy quando o passo 2 for
implementado de fato — a interface `segmentar_frases` deve continuar igual.

O cuidado especifico aqui: texto historico em portugues e' cheio de "a.C." e
"d.C.", e um split ingenuo em "." parte a frase no meio da data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Abreviacoes comuns em texto historico PT cujo ponto NAO termina frase.
_ABREVIACOES = (
    "a.C.",
    "d.C.",
    "a.E.C.",
    "E.C.",
    "séc.",
    "sec.",
    "Sr.",
    "Sra.",
    "Dr.",
    "ca.",
    "cf.",
    "etc.",
)

_MARCADOR = "\x00"  # sentinela que nao aparece em texto normal


@dataclass(frozen=True)
class Frase:
    texto: str
    inicio: int  # offset absoluto no texto original
    fim: int

    def contem(self, span_inicio: int, span_fim: int) -> bool:
        return span_inicio >= self.inicio and span_fim <= self.fim


def segmentar_frases(texto: str) -> list[Frase]:
    """Divide em frases preservando os offsets absolutos do texto original.

    Os offsets sao o que permite casar cada entidade (que vem com span
    absoluto do GLiNER) com a frase a que pertence.
    """
    protegido = texto
    for abrev in _ABREVIACOES:
        protegido = protegido.replace(abrev, abrev.replace(".", _MARCADOR))

    if len(protegido) != len(texto):
        # A protecao precisa preservar o comprimento, senao os offsets mentem.
        raise AssertionError("protecao de abreviacoes alterou o comprimento do texto")

    frases: list[Frase] = []
    inicio = 0
    for match in re.finditer(r"[.!?]+(?=\s|$)", protegido):
        fim = match.end()
        bruto = texto[inicio:fim]
        if bruto.strip():
            deslocamento = len(bruto) - len(bruto.lstrip())
            frases.append(
                Frase(
                    texto=bruto.strip(),
                    inicio=inicio + deslocamento,
                    fim=fim,
                )
            )
        inicio = fim

    resto = texto[inicio:]
    if resto.strip():
        deslocamento = len(resto) - len(resto.lstrip())
        frases.append(
            Frase(
                texto=resto.strip(),
                inicio=inicio + deslocamento,
                fim=len(texto.rstrip()),
            )
        )

    return frases
