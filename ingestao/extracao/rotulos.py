"""Rotulos zero-shot (em portugues) e o mapeamento deles pro modelo de dados.

GLiNER e' zero-shot: as categorias sao declaradas em runtime, sem treino. Isso
significa que a *escolha dos rotulos* e' o principal parametro de qualidade
deste passo — vale tratar esta lista como algo a calibrar com medicao, nao
como constante definitiva.

Os rotulos estao em portugues de proposito: o corpus e' em portugues e o modelo
e' multilingue, entao rotulo e texto no mesmo idioma tende a ajudar. Isso e'
uma hipotese a validar, nao um fato estabelecido.
"""

from __future__ import annotations

from .modelo import Categoria

# Rotulo zero-shot -> categoria do modelo de dados (VISUAL.md).
# Varios rotulos podem cair na mesma categoria: dar ao modelo palavras
# concretas ("cerco", "peste") costuma funcionar melhor em zero-shot do que
# pedir a categoria abstrata ("batalha", "desastre") diretamente.
ROTULOS_EVENTO: dict[str, Categoria] = {
    "batalha": "batalha",
    "guerra": "batalha",
    "cerco": "batalha",
    "conquista militar": "batalha",
    "tratado": "politico",
    "revolução": "politico",
    "código de leis": "politico",
    "construção": "construcao",
    "expedição marítima": "naval",
    "descobrimento": "descoberta",
    "epidemia": "desastre",
    "obra cultural": "cultural",
    "evento religioso": "religioso",
}

# Rotulos de entidade -> papel no evento.
ROTULOS_ATOR: tuple[str, ...] = ("pessoa", "império", "reino", "organização")

# "lugar" mede melhor que "cidade" (calibrar.py): pontua mais alto nas cidades
# E ainda alcanca lugares que nao sao cidade ("Grande Piramide de Gize"), que
# "cidade" perdia por completo. "monumento" entra como local tambem — um
# monumento e' onde o evento acontece.
ROTULOS_LOCAL: tuple[str, ...] = ("lugar", "monumento")

# Um rotulo so' de "data" perdia ano isolado (1789 -> 0.46) e data antiga
# (2560 a.C. -> 0.21). Separado em tres, os mesmos trechos sobem para 0.82 e
# 0.54. O modelo parece responder ao formato, nao a nocao abstrata de data.
ROTULOS_DATA: tuple[str, ...] = ("data histórica", "ano", "período")

# Limiares distintos por tipo, medidos em calibrar.py: rotulos de EVENTO
# pontuam bem mais baixo que rotulos de ENTIDADE neste modelo ("cerco" sai a
# 0.35 enquanto "Constantinopla" sai a 0.84; "batalha" e "conquista" nao saem
# de jeito nenhum). Usar um limiar unico obriga a escolher entre perder todo
# evento ou encher de ruido — em 0.1 o modelo chega a rotular "Grande Piramide
# de Gize" como "epidemia" (0.11).
LIMIAR_ENTIDADE = 0.5
LIMIAR_EVENTO = 0.3


def todos_rotulos() -> list[str]:
    """Lista unica de rotulos. Ver aviso em `grupos_de_rotulos`."""
    rotulos = list(ROTULOS_EVENTO)
    rotulos.extend(ROTULOS_ATOR)
    rotulos.extend(ROTULOS_LOCAL)
    rotulos.extend(ROTULOS_DATA)
    return rotulos


def grupos_de_rotulos() -> dict[str, tuple[list[str], float]]:
    """Rotulos separados por grupo, cada um com seu limiar.

    MEDIDO: passar todos os rotulos numa chamada so' derruba o score cerca de
    3x, porque os rotulos competem entre si pelo mesmo span. No paragrafo de
    teste, "Constantinopla" sai a 0.27 com 22 rotulos, 0.77 com 5 e 0.84 com 1.
    Com limiar 0.5, a versao de 22 rotulos perdia TODOS os locais e datas.

    Por isso o extrator faz uma chamada por grupo (4 no total, mais lento) em
    vez de uma chamada unica (rapida e ruim).
    """
    return {
        "evento": (list(ROTULOS_EVENTO), LIMIAR_EVENTO),
        "ator": (list(ROTULOS_ATOR), LIMIAR_ENTIDADE),
        "local": (list(ROTULOS_LOCAL), LIMIAR_ENTIDADE),
        "data": (list(ROTULOS_DATA), LIMIAR_ENTIDADE),
    }


def categoria_de(rotulo: str) -> Categoria | None:
    return ROTULOS_EVENTO.get(rotulo)


def e_evento(rotulo: str) -> bool:
    return rotulo in ROTULOS_EVENTO


def e_ator(rotulo: str) -> bool:
    return rotulo in ROTULOS_ATOR


def e_local(rotulo: str) -> bool:
    return rotulo in ROTULOS_LOCAL


def e_data(rotulo: str) -> bool:
    return rotulo in ROTULOS_DATA


def limiar_de(rotulo: str) -> float:
    return LIMIAR_EVENTO if e_evento(rotulo) else LIMIAR_ENTIDADE
