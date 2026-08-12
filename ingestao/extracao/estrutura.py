"""Estrutura do livro como pista pra mineração — passo 4 do IA.md ("Estrutura
do livro... ataca o passo 4 diretamente"), decisão já escrita no documento
mas nunca implementada até agora.

MEDIDO em revisão manual real (ver IA.md): de 12 candidatos rejeitados numa
amostra de 15, 3 vinham de seções claramente NÃO narrativas — "Resposta
Comentada" (resposta de exercício sobre uma tese acadêmica, não um evento),
"Objetivos" (lista do que o aluno deverá aprender) e "Atividade Final"
(enunciado de exercício citando um autor). Não é acaso: os livros de amostra
são material didático EAD, com uma estrutura de seção bem previsível — "Aula
N", "Módulo N", "UNIDADE N | título", e rótulos fixos ("Objetivos", "Resposta
Comentada", "Atividade Final", "Dicas", "Informação sobre a próxima aula",
"Resumo", "Bibliografia", "Referências", "Exercícios", "Glossário").

O que este módulo faz: acha o cabeçalho de seção mais próximo por regex
(linha isolada que bate com um rótulo conhecido) e classifica em narrativo/
não-narrativo. NÃO deleta nem inventa nada — só marca, para quem revisa
poder priorizar (ver revisar.py) e para dar o "norte" do título de seção
como contexto visível, sem auto-preencher campo nenhum a partir dele (isso
seria inferência sem span próprio — quem decide usar o contexto é o humano).

Heurística explícita, não solução geral: um cabeçalho maior que a lista
abaixo, ou fora do padrão "Aula/Módulo/Unidade N", passa batido. Isso é
esperado — o upgrade natural seria usar `get_text("dict")` do PyMuPDF para
achar cabeçalho por tamanho de fonte/negrito de verdade, em vez de adivinhar
pelo formato da linha (texto plano só).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Rótulos de seção vistos nos dois livros de amostra, que sinalizam texto de
# APARATO DIDÁTICO (metadado da aula), não relato histórico. Ancorado na
# linha INTEIRA (não substring) — "objetivos" dentro de uma frase de
# narrativa comum não deve disparar isso, só quando a linha É o rótulo.
_ROTULOS_NAO_NARRATIVOS = (
    "objetivos",
    "meta da aula",
    "metas da aula",
    "pré-requisito",
    "pré-requisitos",
    "resposta comentada",
    "respostas comentadas",
    "atividade final",
    "atividade",
    "atividades",
    "exercício",
    "exercícios",
    "dicas",
    "informação sobre a próxima aula",
    "resumo da aula",
    "bibliografia",
    "referências",
    "referências bibliográficas",
    "glossário",
    "leitura complementar",
)

_RE_ROTULO_SECAO = re.compile(
    r"^[ \t]*(" + "|".join(_ROTULOS_NAO_NARRATIVOS) + r")[ \t\.:]*$",
    re.MULTILINE | re.IGNORECASE,
)

# "Aula 3 – O trabalho com modelos: o Mediterrâneo", "Módulo 1",
# "UNIDADE 2 | A CONSOLIDAÇÃO DA CULTURA MODERNA" — marcador de capítulo/
# lição, narrativo por padrão (o conteúdo ali é aula de história, não
# aparato didático) mas dá contexto de tópico pra quem revisa.
_RE_MARCADOR_LICAO = re.compile(
    r"^[ \t]*((?:Aula|M[oó]dulo|Unidade|UNIDADE)\s+\d+[^\n]{0,80})[ \t]*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Secao:
    titulo: str
    inicio: int  # posicao no texto onde o cabecalho comeca
    narrativa: bool


def detectar_secoes(texto: str) -> list[Secao]:
    """Acha cabeçalhos de seção no texto, ordenados pela posição em que aparecem."""
    secoes: list[Secao] = []
    for m in _RE_ROTULO_SECAO.finditer(texto):
        secoes.append(Secao(titulo=m.group(1).strip(), inicio=m.start(), narrativa=False))
    for m in _RE_MARCADOR_LICAO.finditer(texto):
        secoes.append(Secao(titulo=m.group(1).strip(), inicio=m.start(), narrativa=True))
    secoes.sort(key=lambda s: s.inicio)
    return secoes


def secao_em(posicao: int, secoes: list[Secao]) -> Secao | None:
    """Seção vigente numa posição do texto — a última cujo cabeçalho vem antes
    dela. None se a posição vem antes de qualquer cabeçalho detectado."""
    atual: Secao | None = None
    for secao in secoes:
        if secao.inicio > posicao:
            break
        atual = secao
    return atual
