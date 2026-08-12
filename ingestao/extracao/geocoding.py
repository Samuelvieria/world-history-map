"""Geocoding — passo 5 do IA.md.

Duas camadas, nessa ordem:
  1. Gazetteer local (`extracao.gazetteer`) — municípios do IBGE + cidades
     historicamente relevantes do mundo, curados. Sem rede, sem ambiguidade
     pros nomes que cobre. Ver gazetteer.py pro porque disso existir: medido
     nesta sessão que o Nominatim resolve homônimo com confiança alta
     ("ABC" → sede da rádio australiana ABC, "Reino Novo" → aeroporto de
     uma cidade brasileira).
  2. Nominatim (MVP do IA.md) — só quando o gazetteer local não tem o nome.
     Geocoders comuns resolvem o nome ATUAL do lugar, não o nome de época —
     "Baixa Mesopotâmia" pode não achar nada. Aceitar essa imprecisão é a
     decisão, não um acidente; WHG/Pleiades (nomes de época de verdade)
     ficam pra depois.

Nunca inventa coordenada, em nenhuma das duas camadas: sem resultado, devolve
None. Um lat/lng chutado seria pior que nenhum — entraria no banco parecendo
dado e cravaria um ponto errado no globo.

Respeita a política de uso do Nominatim (nominatim.org/release-docs/latest/api/Search/):
no máximo 1 requisição por segundo, User-Agent identificando a aplicação, sem
uso em massa. Com algumas dezenas de candidatos por vez (revisão humana é o
gargalo, não a geocodificação), isso nunca chega perto do limite — e agora
menos ainda, já que o gazetteer local resolve boa parte sem bater rede.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = (
    "globo-historico-interativo/0.1 (uso educacional; "
    "github.com/Samuelvieria/world-history-map)"
)
_INTERVALO_MINIMO_S = 1.1  # politica do Nominatim: no maximo 1 req/s

_ultima_chamada = 0.0


@dataclass(frozen=True)
class ResultadoGeocoding:
    lat: float
    lng: float
    nome_atual: str
    fonte: str
    confianca: float


def _esperar_rate_limit() -> None:
    global _ultima_chamada
    decorrido = time.monotonic() - _ultima_chamada
    if decorrido < _INTERVALO_MINIMO_S:
        time.sleep(_INTERVALO_MINIMO_S - decorrido)
    _ultima_chamada = time.monotonic()


def resolver(nome_lugar: str) -> ResultadoGeocoding | None:
    """Gazetteer local primeiro (sem rede, sem ambiguidade pro que cobre);
    Nominatim so' se o local nao tiver o nome. None se nenhum dos dois
    achar — nunca chuta.
    """
    from . import gazetteer  # import tardio: evita ciclo (gazetteer importa daqui)

    resultado_local = gazetteer.resolver_local(nome_lugar)
    if resultado_local is not None:
        return resultado_local

    return _resolver_nominatim(nome_lugar)


def _resolver_nominatim(nome_lugar: str) -> ResultadoGeocoding | None:
    """Busca `nome_lugar` no Nominatim. None se nao achar nada — nunca chuta.

    `confianca` vem do campo `importance` do Nominatim: mede o quao
    proeminente aquele LUGAR e' em geral (o quao conhecido, globalmente),
    NAO o quao confiante a busca esta' de ter achado o lugar certo pra esse
    nome. E' o unico sinal de confianca real que a API gratuita devolve —
    documentado aqui pra ninguem confundir os dois sentidos depois.
    """
    _esperar_rate_limit()
    query = urllib.parse.urlencode({"q": nome_lugar, "format": "json", "limit": 1})
    req = urllib.request.Request(f"{_URL}?{query}", headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resultados = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as erro:
        raise RuntimeError(f"Nominatim falhou para {nome_lugar!r}: {erro}") from erro

    if not resultados:
        return None

    r = resultados[0]
    return ResultadoGeocoding(
        lat=float(r["lat"]),
        lng=float(r["lon"]),
        nome_atual=r["display_name"],
        fonte="Nominatim",
        confianca=float(r.get("importance", 0.5)),
    )
