"""Passo 1 do IA.md: PDF -> texto limpo. Nao e' IA — so' extracao de texto que
ja' esta' embutido no arquivo (camada de texto do PDF), sem inferencia nenhuma.

Nao faz OCR. Se o PDF for so' imagem escaneada (sem camada de texto), a pagina
volta vazia — melhor um vazio honesto do que inventar texto. `paginas_com_texto`
avisa quantas paginas caem nesse caso, para nao passar despercebido.

MEDIDO contra os PDFs reais em `amostras/`: os acentos SAEM corretos
(verificado byte a byte via ToUnicode CMap da fonte — nao e' um bug de
extracao). O que sai errado sem tratamento e' a **ligadura tipografica**: PDFs
com boa tipografia usam um unico glifo para "fi" (U+FB01) em vez de "f"+"i",
e isso quebra qualquer casamento de palavra a jusante (GLiNER, os regex de
`datas.py`). `unicodedata.normalize("NFKC", ...)` decompoe a ligadura de volta
("ﬁgura" -> "figura") — e' compatibilidade Unicode padrao, nao um palpite.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PaginaPdf:
    """Uma pagina do PDF. `numero` e' 1-indexado, como se le no arquivo."""

    numero: int
    texto: str


def extrair_paginas(caminho: str | Path) -> list[PaginaPdf]:
    import pymupdf  # import tardio: abrir a lib custa um pouco, so' quando precisar

    paginas: list[PaginaPdf] = []
    with pymupdf.open(caminho) as doc:
        for indice, pagina in enumerate(doc):
            texto = unicodedata.normalize('NFKC', pagina.get_text())
            paginas.append(PaginaPdf(numero=indice + 1, texto=texto))
    return paginas


def contar_paginas_sem_texto(paginas: list[PaginaPdf]) -> int:
    """Paginas vazias apos extracao — indicio de PDF escaneado (sem OCR aqui)."""
    return sum(1 for p in paginas if not p.texto.strip())
