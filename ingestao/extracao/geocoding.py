"""Geocoding — STUB. Passo 5 do IA.md, ainda nao implementado.

O IA.md manda tratar geocoding como stub no passo 1 e resolver depois com
Mordecai3 ou `geoparser` + dump local do GeoNames.

Este stub deliberadamente NAO chuta coordenada. Um lat/lng inventado e' pior
que nenhum: entraria no banco parecendo dado, cravaria um ponto errado no globo
e ninguem saberia que era palpite. Devolver `None` mantem o candidato
honestamente incompleto ate' o passo 5 existir.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoGeocoding:
    lat: float
    lng: float
    fonte: str
    confianca: float


def resolver(nome_lugar: str) -> ResultadoGeocoding | None:
    """Sempre None enquanto o passo 5 nao existir. Ver docstring do modulo."""
    _ = nome_lugar
    return None
