"""Estruturas de dados da extracao, com proveniencia obrigatoria.

Regra de ouro do IA.md: "Sem span, o campo nao existe e o evento vai pra
revisao como incompleto — nunca direto pro mapa."

Aqui essa regra e' *estrutural*, nao uma convencao: nao existe construtor de
`CampoExtraido` que aceite ausencia de span. Se o extrator nao souber apontar
o trecho de origem, ele nao consegue criar o campo — ponto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Espelha `Categoria` em src/types/Event.ts (VISUAL.md).
Categoria = Literal[
    "batalha",
    "construcao",
    "naval",
    "politico",
    "cultural",
    "religioso",
    "descoberta",
    "desastre",
]

StatusRevisao = Literal["pendente", "aprovado", "rejeitado"]


@dataclass(frozen=True)
class Proveniencia:
    """De onde o dado veio, com precisao de caractere.

    `trecho` e' o texto verbatim da fonte. E' guardado para rastreabilidade
    interna e NUNCA deve ser exibido ao usuario final (direito autoral — ver
    CLAUDE.md). O que vai pra tela e' o resumo gerado por template.
    """

    fonte_id: str
    span_inicio: int
    span_fim: int
    trecho: str
    pagina: int | None = None

    def __post_init__(self) -> None:
        if self.span_inicio < 0 or self.span_fim < 0:
            raise ValueError(f"span negativo: ({self.span_inicio}, {self.span_fim})")
        if self.span_fim <= self.span_inicio:
            raise ValueError(
                f"span vazio ou invertido: ({self.span_inicio}, {self.span_fim})"
            )
        if not self.trecho:
            raise ValueError("trecho vazio — proveniencia sem texto nao rastreia nada")

    def confere_com(self, texto_original: str) -> bool:
        """O span realmente indexa o trecho no texto original?

        Usado para detectar dessincronizacao entre o texto que o extrator viu e
        o texto arquivado. Se isso der falso, a proveniencia e' ficcao.
        """
        return texto_original[self.span_inicio : self.span_fim] == self.trecho


@dataclass(frozen=True)
class CampoExtraido:
    """Um valor extraido + de onde saiu. Nao existe um sem o outro."""

    valor: str
    confianca: float
    proveniencia: Proveniencia
    rotulo_origem: str = ""

    def __post_init__(self) -> None:
        if not self.valor.strip():
            raise ValueError("campo sem valor")
        if not 0.0 <= self.confianca <= 1.0:
            raise ValueError(f"confianca fora de [0,1]: {self.confianca}")


# Campos exigidos para um candidato ser considerado completo o bastante para
# a tela de revisao mostrar como "pronto para aprovar de imediato".
CAMPOS_MINIMOS = ("titulo", "categoria", "local_nome_epoca", "data_bruta")


@dataclass
class EventoCandidato:
    """Sugestao de evento, ANTES da revisao humana.

    Deliberadamente NAO e' um `HistoricalEvent` (src/types/Event.ts). Um
    candidato so' vira evento no mapa depois que uma pessoa aprova. Manter os
    dois tipos separados impede que algo extraido automaticamente vaze pro
    globo por descuido.
    """

    fonte_id: str
    texto_origem: str

    titulo: CampoExtraido | None = None
    categoria: CampoExtraido | None = None
    local_nome_epoca: CampoExtraido | None = None
    atores: list[CampoExtraido] = field(default_factory=list)
    datas_brutas: list[CampoExtraido] = field(default_factory=list)

    # Preenchidos por etapas posteriores do pipeline (IA.md passos 5, 6 e 7).
    # lat/lng ficam None no passo 1 — geocoding e' stub por decisao explicita.
    lat: float | None = None
    lng: float | None = None
    geocoding_fonte: str | None = None
    confianca_local: float | None = None
    data_inicio: str | None = None
    data_fim: str | None = None
    incerteza_data: str | None = None

    # Preenchido pelo passo 7 (extracao.resumo) — slot-filling por template,
    # nunca copia trecho-fonte verbatim (ver Proveniencia.trecho).
    resumo: str | None = None

    status: StatusRevisao = "pendente"

    @property
    def data_bruta(self) -> CampoExtraido | None:
        """Primeira data encontrada — atalho para a checagem de completude."""
        return self.datas_brutas[0] if self.datas_brutas else None

    def campos_faltando(self) -> list[str]:
        return [campo for campo in CAMPOS_MINIMOS if getattr(self, campo) is None]

    def esta_completo(self) -> bool:
        return not self.campos_faltando()

    def proveniencias(self) -> list[Proveniencia]:
        campos: list[CampoExtraido] = [
            c
            for c in (self.titulo, self.categoria, self.local_nome_epoca)
            if c is not None
        ]
        campos.extend(self.atores)
        campos.extend(self.datas_brutas)
        return [c.proveniencia for c in campos]

    def proveniencia_integra(self) -> bool:
        """Toda proveniencia deste candidato aponta mesmo para o texto de origem?"""
        return all(p.confere_com(self.texto_origem) for p in self.proveniencias())
