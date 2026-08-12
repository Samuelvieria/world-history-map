"""Geocoding — passo 5 do IA.md, caminho barato (MVP): Nominatim.

MVP conforme o IA.md: "Nominatim / GeoNames (coordenadas modernas, aceitar
imprecisão)". Geocoders comuns resolvem o nome ATUAL do lugar, não o nome de
época — "Baixa Mesopotâmia" pode não achar nada, "Constantinopla" pode achar
por já ser um alias conhecido do OSM. Aceitar essa imprecisão é a decisão,
não um acidente; WHG/Pleiades (nomes de época de verdade) ficam pra depois.

Nunca inventa coordenada: sem resultado do Nominatim, devolve None. Um
lat/lng chutado seria pior que nenhum — entraria no banco parecendo dado e
cravaria um ponto errado no globo.

Respeita a política de uso do Nominatim (nominatim.org/release-docs/latest/api/Search/):
no máximo 1 requisição por segundo, User-Agent identificando a aplicação, sem
uso em massa. Com algumas dezenas de candidatos por vez (revisão humana é o
gargalo, não a geocodificação), isso nunca chega perto do limite.
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
