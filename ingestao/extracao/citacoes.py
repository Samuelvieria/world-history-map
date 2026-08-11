"""Filtra citacao bibliografica sendo lida como data ou ator do evento.

Achado numa revisao manual real (ver IA.md, secao "revisao manual real de 15
candidatos"): zigurates "construidos em 1999" era na verdade a citacao
`(CARDOSO, 1999)` do proprio livro-fonte — o ano da referencia bibliografica,
nao a data do evento. O mesmo padrao apareceu com `(KEMP, 1987)` virando data
de piramide e `(DONADONI, 1990, p.15)` virando data de "conquistas
militares". Nao e' ruido aleatorio: e' sistematico, porque o rotulo
"ano"/"data historica" do GLiNER nao distingue "ano dentro de uma citacao"
de "ano do evento narrado" — os dois tem a mesma forma superficial (4 digitos).

Regra deterministica, no mesmo espirito do resto do passo 4: acha o span da
citacao INTEIRA por regex e descarta qualquer entidade (data ou ator) cujo
span cai dentro dela. Convencao observada no livro de amostra (estilo ABNT):
sobrenome em CAIXA ALTA, virgula, ano de 4 digitos, pagina opcional —
"(CARDOSO, 1999)", "(DONADONI, 1990, p.15)".
"""

from __future__ import annotations

import re
from typing import Any

_RE_CITACAO = re.compile(
    r"\(\s*[A-ZÀ-Ú][A-ZÀ-Ú\.\s]{1,40}\s*,\s*\d{4}[a-z]?(?:\s*,\s*p\.?\s*\d+)?\s*\)"
)


def spans_de_citacao(texto: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _RE_CITACAO.finditer(texto)]


def esta_dentro_de_citacao(inicio: int, fim: int, citacoes: list[tuple[int, int]]) -> bool:
    return any(c_inicio <= inicio and fim <= c_fim for c_inicio, c_fim in citacoes)


def filtrar_citacoes(entidades: list[dict[str, Any]], texto: str) -> list[dict[str, Any]]:
    """Remove de `entidades` qualquer uma cujo span caia dentro de uma citacao.

    `entidades` e' a saida crua do GLiNER (dicts com `start`/`end`) — ver
    `ExtratorGLiNER.entidades_cruas`.
    """
    citacoes = spans_de_citacao(texto)
    if not citacoes:
        return entidades
    return [e for e in entidades if not esta_dentro_de_citacao(e["start"], e["end"], citacoes)]
