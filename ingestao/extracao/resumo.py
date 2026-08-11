"""Passo 7 do IA.md: resumo por slot-filling, NAO por geracao de texto livre.

O template so' rearranja campos ja' extraidos (titulo/categoria/local/data/
atores). Nunca copia o trecho-fonte verbatim (direito autoral — CLAUDE.md) e
nunca introduz informacao que nao esteja em outro campo do candidato
(alucinacao). Se um campo estiver ausente, o slot correspondente e' omitido —
a frase encolhe, nunca inventa para preencher o buraco.
"""

from __future__ import annotations

from .datas import ano_legivel
from .modelo import EventoCandidato

_CATEGORIA_LEGIVEL: dict[str, str] = {
    "batalha": "uma batalha",
    "construcao": "uma construção",
    "naval": "um evento naval",
    "politico": "um evento político",
    "cultural": "um evento cultural",
    "religioso": "um evento religioso",
    "descoberta": "uma descoberta",
    "desastre": "um desastre",
}


def gerar_resumo(candidato: EventoCandidato) -> str | None:
    """None se nao houver nem titulo nem categoria — nao ha' o que templatizar."""
    if candidato.titulo is None and candidato.categoria is None:
        return None

    corpo = candidato.titulo.valor if candidato.titulo else _categoria_legivel(candidato)

    partes: list[str] = []
    if candidato.data_inicio:
        partes.append(f"Em {ano_legivel(candidato.data_inicio)}")
    if candidato.local_nome_epoca:
        partes.append(f"em {candidato.local_nome_epoca.valor}")

    prefixo = ", ".join(partes)
    frase = f"{prefixo}: {corpo}" if prefixo else corpo

    if candidato.atores:
        nomes = ", ".join(a.valor for a in candidato.atores)
        frase += f", envolvendo {nomes}"

    # Maiuscula sempre no fim, nao so' no ramo sem prefixo: "em Europa: X"
    # (local sem data) tambem precisa comecar com "E" maiusculo. MEDIDO numa
    # ingestao real (Historia Moderna, pag. 27) — nao aparecia no teste
    # sintetico porque la' sempre havia data OU nem titulo nem local.
    return _iniciar_maiuscula(frase) + "."


def _iniciar_maiuscula(texto: str) -> str:
    """Maiuscula so' na primeira letra — `str.capitalize()` minusculiza o
    resto e destruiria nomes proprios ('Batalha de Waterloo' -> 'waterloo')."""
    return texto[:1].upper() + texto[1:] if texto else texto


def _categoria_legivel(candidato: EventoCandidato) -> str:
    if candidato.categoria is None:
        return "acontecimento"
    return _CATEGORIA_LEGIVEL.get(candidato.categoria.valor, candidato.categoria.valor)


def preencher_resumo(candidato: EventoCandidato) -> None:
    candidato.resumo = gerar_resumo(candidato)
