"""Passo 2 do IA.md: data bruta (texto) -> data_inicio/data_fim + incerteza_data.

Decisao: regras + regex, NAO HeidelTime/dateparser. O IA.md citava essas duas
bibliotecas como opcao, mas nenhuma das duas resolve bem o caso que mais
aparece em texto historico em portugues: ano antes de Cristo ("2560 a.C.").
dateparser simplesmente nao tem esse conceito; HeidelTime e' uma dependencia
Java pesada para um parser que, medido no paragrafo de teste, so' precisa
cobrir cinco formatos (ver `normalizar`). Regex mantem a garantia central do
IA.md: determinismo auditável, sem chance de "inventar" uma data plausivel.

Formatos reconhecidos (com ou sem sufixo " a.C."/"a.E.C."):
  - dia + mes + ano  ("29 de maio de 1453")      -> incerteza "exata"
  - mes + ano        ("outubro de 1347")         -> incerteza "ano" (ver nota)
  - ano isolado      ("1453", "2560 a.C.")        -> incerteza "ano"
  - decada           ("década de 1980")           -> incerteza "decada"
  - seculo           ("século XV", "século XV a.C.") -> incerteza "seculo"

Nota sobre "mes + ano": o modelo de dados (CLAUDE.md) so' tem cinco niveis de
incerteza e nao existe um nivel "mes". Rotulamos como "ano" (o nivel mais
proximo que existe), mas `data_inicio`/`data_fim` guardam o intervalo do MES
conhecido, nao do ano inteiro — e' informacao real, nao motivo para descartar.

"aproximada" nao vem do formato da data em si, e sim de uma marcacao textual
ao redor ("por volta de", "cerca de", "ca."). Por isso `normalizar` aceita um
`contexto` (a janela de texto ao redor do span) alem do valor bruto — ver
`preencher_datas`, que monta essa janela a partir da proveniencia.

Anos antes de Cristo usam numeracao astronomica (ISO 8601): ano 1 a.C. =
astronomico 0, ano N a.C. = astronomico -(N-1). Isso preserva ordem
cronologica em comparacao de string e evita inventar uma convencao propria.

GAP CONHECIDO (achado numa ingestao real, nao no teste sintetico): "milenio"
("terceiro milenio antes de Cristo") nao e' reconhecido — cai em None, nunca
em data inventada, mas e' expressao comum em historia antiga e vale suportar
depois no mesmo padrao de _intervalo_seculo/_intervalo_decada.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

IncertezaData = Literal["exata", "ano", "decada", "seculo", "aproximada"]

MESES: dict[str, int] = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

_MESES_ALT = "|".join(sorted(MESES, key=len, reverse=True))

_RE_AC = re.compile(r"a\.\s*c\.|a\.\s*e\.\s*c\.", re.IGNORECASE)
_RE_APROXIMADA = re.compile(
    r"por volta de|cerca de|\bca\.\s*\d|aproximadamente", re.IGNORECASE
)
_RE_SECULO = re.compile(
    r"s[ée]cul[oa]?\.?\s+([ivxlcdm]+|\d{1,2})\b", re.IGNORECASE
)
_RE_DECADA = re.compile(r"d[ée]cada\s+de\s+(\d{4})", re.IGNORECASE)
_RE_DATA_COMPLETA = re.compile(
    rf"(\d{{1,2}})\s+de\s+({_MESES_ALT})\s+de\s+(\d{{1,5}})", re.IGNORECASE
)
_RE_MES_ANO = re.compile(rf"({_MESES_ALT})\s+de\s+(\d{{1,5}})", re.IGNORECASE)
# {1,5}: cobre ate' "10000 a.C." (data comum em livros de historia p/
# revolucao agricola), sem exagerar no alcance.
_RE_ANO = re.compile(r"\d{1,5}")

_ROMANOS = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}


@dataclass(frozen=True)
class DataNormalizada:
    data_inicio: str  # ISO 8601 (YYYY-MM-DD); ano negativo = a.C. (numeracao astronomica)
    data_fim: str
    incerteza_data: IncertezaData


def _romano_para_inteiro(texto: str) -> int | None:
    """Converte numeral romano (I..MMM) em inteiro. None se invalido."""
    texto = texto.lower()
    if not texto or any(c not in _ROMANOS for c in texto):
        return None
    total = 0
    anterior = 0
    for c in reversed(texto):
        valor = _ROMANOS[c]
        total += valor if valor >= anterior else -valor
        anterior = max(anterior, valor)
    return total


def _ano_astronomico(ano_historico: int, ac: bool) -> int:
    """Ano 1 a.C. -> 0; ano N a.C. -> -(N-1). Ano d.C. permanece igual."""
    return 1 - ano_historico if ac else ano_historico


def _iso(ano_astro: int, mes: int = 1, dia: int = 1) -> str:
    if ano_astro < 0:
        return f"-{abs(ano_astro):04d}-{mes:02d}-{dia:02d}"
    return f"{ano_astro:04d}-{mes:02d}-{dia:02d}"


_DIAS_POR_MES = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


def _dias_no_mes(mes: int) -> int:
    """Ignora ano bissexto de proposito: a diferenca (28 vs 29 em fevereiro)
    nao muda o nivel de incerteza reportado, so' o limite do intervalo em
    casos raros — nao vale a complexidade de checar bissexto para numeracao
    astronomica negativa."""
    return _DIAS_POR_MES[mes]


def _intervalo_seculo(n: int, ac: bool) -> tuple[str, str]:
    if not ac:
        return _iso((n - 1) * 100 + 1), _iso(n * 100, 12, 31)
    inicio_hist = n * 100
    fim_hist = (n - 1) * 100 + 1
    return _iso(_ano_astronomico(inicio_hist, True)), _iso(
        _ano_astronomico(fim_hist, True), 12, 31
    )


def _intervalo_decada(ano_inicio: int, ac: bool) -> tuple[str, str]:
    if not ac:
        return _iso(ano_inicio), _iso(ano_inicio + 9, 12, 31)
    inicio_hist = ano_inicio + 9
    fim_hist = ano_inicio
    return _iso(_ano_astronomico(inicio_hist, True)), _iso(
        _ano_astronomico(fim_hist, True), 12, 31
    )


def normalizar(raw: str, contexto: str = "") -> DataNormalizada | None:
    """Tenta normalizar uma data bruta extraida do texto. None se nao reconhecer.

    `contexto` e' a janela de texto ao redor do span (usada so' para detectar
    marcadores de aproximacao — "por volta de" raramente entra no span exato
    de uma entidade de data).
    """
    ac = bool(_RE_AC.search(raw))
    aproximada = bool(_RE_APROXIMADA.search(contexto) or _RE_APROXIMADA.search(raw))

    m = _RE_SECULO.search(raw)
    if m:
        bruto = m.group(1)
        n = int(bruto) if bruto.isdigit() else _romano_para_inteiro(bruto)
        if n is None or n <= 0:
            return None
        inicio, fim = _intervalo_seculo(n, ac)
        return DataNormalizada(inicio, fim, "aproximada" if aproximada else "seculo")

    m = _RE_DECADA.search(raw)
    if m:
        inicio, fim = _intervalo_decada(int(m.group(1)), ac)
        return DataNormalizada(inicio, fim, "aproximada" if aproximada else "decada")

    m = _RE_DATA_COMPLETA.search(raw)
    if m:
        dia, nome_mes, ano = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        mes = MESES[nome_mes]
        ano_astro = _ano_astronomico(ano, ac)
        data = _iso(ano_astro, mes, dia)
        return DataNormalizada(data, data, "aproximada" if aproximada else "exata")

    m = _RE_MES_ANO.search(raw)
    if m:
        nome_mes, ano = m.group(1).lower(), int(m.group(2))
        mes = MESES[nome_mes]
        ano_astro = _ano_astronomico(ano, ac)
        inicio = _iso(ano_astro, mes, 1)
        fim = _iso(ano_astro, mes, _dias_no_mes(mes))
        return DataNormalizada(inicio, fim, "aproximada" if aproximada else "ano")

    m = _RE_ANO.search(raw)
    if m:
        ano_astro = _ano_astronomico(int(m.group(0)), ac)
        return DataNormalizada(
            _iso(ano_astro, 1, 1),
            _iso(ano_astro, 12, 31),
            "aproximada" if aproximada else "ano",
        )

    return None


def ano_legivel(data_iso: str) -> str:
    """Inverso legivel de `_iso`, so' o ano: '-2559-01-01' -> '2560 a.C.'."""
    negativo = data_iso.startswith("-")
    ano_astro = -int(data_iso[1:].split("-", 1)[0]) if negativo else int(
        data_iso.split("-", 1)[0]
    )
    if ano_astro <= 0:
        return f"{1 - ano_astro} a.C."
    return str(ano_astro)


def _janela_contexto(texto_origem: str, span_inicio: int, span_fim: int) -> str:
    """Fatia de texto antes/depois do span, para procurar marcadores como
    'por volta de' que ficam fora do span exato da entidade de data."""
    inicio = max(0, span_inicio - 40)
    return texto_origem[inicio:span_fim]


def preencher_datas(candidato: "EventoCandidato") -> None:  # noqa: F821
    """Preenche data_inicio/data_fim/incerteza_data a partir de datas_brutas.

    Heuristica explicita, no mesmo espirito do agrupamento por frase em
    extrator.py: usa a PRIMEIRA data bruta que normaliza com sucesso. Um
    candidato pode ter mais de uma mencao de data (ex.: "nascido em X, morto
    em Y"); escolher a primeira e' uma simplificacao deliberada, nao uma
    solucao geral — fica visivel na revisao humana quando dar errado.
    """
    for campo in candidato.datas_brutas:
        p = campo.proveniencia
        contexto = _janela_contexto(candidato.texto_origem, p.span_inicio, p.span_fim)
        normalizada = normalizar(campo.valor, contexto)
        if normalizada is not None:
            candidato.data_inicio = normalizada.data_inicio
            candidato.data_fim = normalizada.data_fim
            candidato.incerteza_data = normalizada.incerteza_data
            return
