"""Correlaciona candidatos que provavelmente descrevem o MESMO acontecimento,
possivelmente extraídos de LIVROS DIFERENTES — o que o CLAUDE.md já previa na
seção "Validação por consenso" e nunca tinha sido construído: não guardar "a
verdade" e sim asserções de fontes, calcular corroboração quando fontes
independentes concordam, e mostrar a divergência quando elas discordam em vez
de forçar consenso.

Este módulo só PONTUA pares de candidatos por similaridade — nunca funde nada
sozinho. A decisão de "isso é o mesmo evento" fica com quem revisa (ver
`correlacionar.py`), na mesma linha de "a IA só sugere, o humano aprova" que
`citacoes.py` e `revisar.py` já seguem. Regra determinística (Jaccard de
tokens + sobreposição de data), não LLM — mesma restrição do resto do projeto.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

# Palavras curtas demais pra contar como sinal — preposição/artigo comum em
# português infla a similaridade entre títulos que não tem nada a ver
# ("Batalha de Roma" vs "Cerco de Roma" já compartilham "de"; o que importa
# e' "batalha"/"cerco" vs "roma").
_PARADAS = {
    "de", "da", "do", "dos", "das", "a", "o", "as", "os",
    "em", "e", "um", "uma", "no", "na", "nos", "nas",
}


def _tokens(texto: str) -> set[str]:
    """Tokens normalizados (sem acento, minúsculo, sem pontuação, sem
    parada) — base pra comparar título/local entre candidatos de fontes
    diferentes, que raramente usam a mesma grafia exata."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    brutos = set(re.findall(r"[a-z0-9]+", sem_acento.lower()))
    return brutos - _PARADAS


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _chave_data(data_iso: str) -> tuple[int, int, int]:
    """Converte 'AAAA-MM-DD' (ou '-AAAA-MM-DD' pra a.C., ver datas.py) numa
    chave numerica comparavel de verdade.

    Comparar as strings ISO direto com `<=` PARECE dar certo (a.C. sempre
    comeca com '-', que ordena antes de qualquer digito, entao a.C. vs d.C.
    da' a ordem certa por acidente) mas quebra entre duas datas a.C. de
    magnitude diferente: "-2998-01-01" (2999 a.C.) vs "-0499-01-01" (500
    a.C.) comparam como STRING na ordem errada, porque '0' < '2' no segundo
    digito — o oposto da ordem cronologica (500 a.C. e' mais recente que
    2999 a.C.). Sem essa conversao pra inteiro, `_sobrepoe_datas` mentiria
    justamente no caso mais comum em historia antiga: comparar dois eventos
    a.C. entre si.
    """
    negativo = data_iso.startswith("-")
    corpo = data_iso[1:] if negativo else data_iso
    ano_str, mes_str, dia_str = corpo.split("-")
    ano = -int(ano_str) if negativo else int(ano_str)
    return (ano, int(mes_str), int(dia_str))


def _sobrepoe_datas(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Os intervalos [data_inicio, data_fim] se cruzam?

    Permissivo quando falta informação de data em qualquer lado (devolve
    True) — nesse caso o título/local carregam todo o peso da decisão, e um
    candidato incompleto não deveria ser descartado só por não ter data
    normalizada ainda.
    """
    if not (a.get("data_inicio") and a.get("data_fim") and b.get("data_inicio") and b.get("data_fim")):
        return True
    inicio_a, fim_a = _chave_data(a["data_inicio"]), _chave_data(a["data_fim"])
    inicio_b, fim_b = _chave_data(b["data_inicio"]), _chave_data(b["data_fim"])
    return inicio_a <= fim_b and inicio_b <= fim_a


LIMIAR_SIMILARIDADE = 0.5


def pontuar(a: dict[str, Any], b: dict[str, Any]) -> float:
    """0.0 a 1.0. Sem título em algum dos dois, ou datas que não se cruzam,
    a pontuação e' sempre 0 — não há base pra comparar."""
    if not a.get("titulo") or not b.get("titulo"):
        return 0.0
    if not _sobrepoe_datas(a, b):
        return 0.0

    pts_titulo = _jaccard(_tokens(a["titulo"]["valor"]), _tokens(b["titulo"]["valor"]))
    pts_local = 0.0
    if a.get("local_nome_epoca") and b.get("local_nome_epoca"):
        pts_local = _jaccard(_tokens(a["local_nome_epoca"]["valor"]), _tokens(b["local_nome_epoca"]["valor"]))

    # Titulo pesa mais: dois eventos DIFERENTES no MESMO lugar sao comuns
    # (varias batalhas em Roma, por exemplo) e nao significam a mesma coisa;
    # dois com titulo parecido, sim.
    return 0.7 * pts_titulo + 0.3 * pts_local


@dataclass(frozen=True)
class Correlacao:
    candidato_a: dict[str, Any]
    candidato_b: dict[str, Any]
    pontuacao: float


def candidatos_correlacionados(
    candidatos_a: list[dict[str, Any]], candidatos_b: list[dict[str, Any]]
) -> list[Correlacao]:
    """Compara TODOS os pares entre duas listas (tipicamente de fontes
    diferentes) e devolve os que passam do limiar, do mais provavel pro
    menos. O(n*m) — aceitavel: o volume de candidatos que chega aqui e' o de
    APROVADOS na revisao humana (dezenas, nao milhares de candidatos crus).
    """
    encontrados = [
        Correlacao(ca, cb, pontuacao)
        for ca in candidatos_a
        for cb in candidatos_b
        if (pontuacao := pontuar(ca, cb)) >= LIMIAR_SIMILARIDADE
    ]
    encontrados.sort(key=lambda c: -c.pontuacao)
    return encontrados
