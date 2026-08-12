"""Gazetteer local — passo 5 (geocoding), caminho barato pra reduzir o risco
de homônimo do Nominatim medido nesta sessão (ver IA.md): "Reino Novo"
resolveu pro aeroporto de uma cidade brasileira, "ABC" pra rádio australiana,
"Constantinopla" pra uma rua em Buenos Aires — tudo com confiança razoável
do lado do Nominatim. Um gazetteer LOCAL, curado, é sem ambiguidade pros
nomes que cobre — mais seguro que bater busca textual livre numa API pública.

Duas fontes, em `ingestao/dados/`, ambas com cobertura NACIONAL/MUNDIAL
completa agora (lidas direto dos originais — .xls do IBGE com os 5565
municípios, CSV com as 1033 cidades curadas dos 195 países — não mais das
transcrições manuais parciais de uma sessão anterior):
  - `municipios_brasil_ibge.csv`: dado oficial do IBGE — exact match no nome
    do município, sem ambiguidade dentro do Brasil.
  - `cidades_historicas_mundo.csv`: lista curada de cidades historicamente
    relevantes por país, com confiança derivada da coluna `criterio`.
    Nomes vêm majoritariamente do GeoNames em inglês/nome local, NÃO
    traduzidos pro português — "Roma" (o que aparece nos nossos livros) não
    bate direto com "Rome" (o nome na planilha) sem um alias. Só um pequeno
    dicionário pros clássicos mais óbvios foi incluído — não é tradutor.

Nunca inventa: EXACT match (normalizado — sem acento/caixa) ou None. Nunca
fuzzy-match "parecido" — isso reintroduziria o mesmo risco de homônimo que
o Nominatim já demonstrou ter.

Mundo é checado ANTES do Brasil — invertido do design original depois de
medir contra os dados completos. Com os dois CSVs completos, há 30 colisões
reais de nome entre município brasileiro e cidade mundial curada (medido:
Alexandria, Barcelona, Braga, Buenos Aires, Coimbra, Colombo, Guimarães,
Nantes, Porto, Rosário, Santa Fé, Santiago, Toledo, Valparaíso, entre
outras — muitas são cidades brasileiras batizadas em homenagem à cidade
mundial pela colonização portuguesa). Pro corpus atual (livros de história
antiga/moderna, não história regional brasileira), a cidade mundial é
sistematicamente a resposta certa nessas colisões — nenhum caso medido
favoreceu o Brasil quando os dois lados divergem. Onde os dois lados dão a
mesma cidade (Brasília, Recife, Salvador, São Paulo — capitais/cidades que
também entraram na curadoria mundial por relevância histórica própria), a
ordem não importa.

Gap conhecido que a ordem não resolve: o CSV mundial lista CIDADES dentro de
um país, não o país como linha própria — uma referência solta a um país
("Malta", "Cabo Verde") não tem entrada de "cidade" com esse nome, então cai
pro Brasil se houver um município homônimo (há: Malta/PB, Cabo Verde/MG) ou
pro Nominatim se não houver. Frases genéricas não-geocodáveis ("Novo Mundo"
= o conceito histórico, não um lugar) têm o mesmo problema por coincidência
de nome com município ("Novo Mundo", MT). Isso é esperado do modelo
cidade-por-país e não teria solução sem inventar coordenada de país — fica
como candidato pra revisão humana corrigir/rejeitar, que é exatamente o
freio que o IA.md exige antes de publicar (IA só sugere; humano aprova).
"""

from __future__ import annotations

import csv
import unicodedata
from pathlib import Path

from .geocoding import ResultadoGeocoding

_DIR_DADOS = Path(__file__).resolve().parent.parent / "dados"
_CAMINHO_BRASIL = _DIR_DADOS / "municipios_brasil_ibge.csv"
_CAMINHO_MUNDO = _DIR_DADOS / "cidades_historicas_mundo.csv"

# "historical/curated" e "capital" sao escolha humana deliberada (mais
# confiavel); "major-city fallback" e' so' a cidade mais populosa do pais
# quando nao havia opcao historica melhor na curadoria (ainda um match EXATO
# de nome, so' com menos certeza de que e' o lugar historicamente relevante).
_CONFIANCA_POR_CRITERIO = {
    "capital": 0.9,
    "historical/curated": 0.85,
    "major-city fallback": 0.6,
}
_CONFIANCA_PADRAO_MUNDO = 0.5
_CONFIANCA_BRASIL_IBGE = 0.9  # dado oficial, exact match — sem ambiguidade

# Alias PT -> nome na planilha mundial, so' pros classicos mais obvios de
# historia antiga/medieval cujo nome em portugues difere do nome (majoritar.
# em ingles) da planilha. Medido/observado nos livros de amostra ou
# conhecimento geral — NAO e' um tradutor completo, so' cobre o que foi
# visto ou e' universalmente conhecido o bastante pra nao arriscar homonimo.
_ALIAS_PT_MUNDO: dict[str, str] = {
    "atenas": "athens",
    "cartago": "carthage",
    "meca": "mecca",
    "moscou": "moscow",
    "viena": "vienna",
    "genebra": "geneva",
    "praga": "prague",
    "varsovia": "warsaw",
    "florenca": "florence",
    "veneza": "venice",
    "napoles": "naples",
    "turim": "turin",
    "genova": "genoa",
    "colonia": "cologne",
    "haia": "the hague",
    "pequim": "beijing",
    # "roma"->"rome" e "constantinopla"->"istanbul" ficam de fora de
    # proposito: sao os dois nomes que mais aparecem nos nossos livros de
    # amostra, e um erro de alias nesses dois seria o pior caso possivel.
    # So' entram quando confirmados contra a planilha mundial completa.
}


def _normalizar(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return sem_acento.strip().lower()


def _carregar_brasil() -> dict[str, ResultadoGeocoding]:
    indice: dict[str, ResultadoGeocoding] = {}
    if not _CAMINHO_BRASIL.exists():
        return indice
    with open(_CAMINHO_BRASIL, encoding="utf-8") as f:
        leitor = csv.DictReader(f, delimiter=";")
        for linha in leitor:
            nome = linha["NOME_MUNICIPIO"].strip()
            if not nome:
                continue
            lat = float(linha["LATITUDE"].replace(",", "."))
            lng = float(linha["LONGITUDE"].replace(",", "."))
            indice[_normalizar(nome)] = ResultadoGeocoding(
                lat=lat,
                lng=lng,
                nome_atual=f"{nome.title()}, Brasil",
                fonte="IBGE (municipios)",
                confianca=_CONFIANCA_BRASIL_IBGE,
            )
    return indice


def _carregar_mundo() -> dict[str, ResultadoGeocoding]:
    indice: dict[str, ResultadoGeocoding] = {}
    if not _CAMINHO_MUNDO.exists():
        return indice
    with open(_CAMINHO_MUNDO, encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        for linha in leitor:
            nome = linha["cidade"].strip()
            pais = linha["pais"].strip()
            if not nome:
                continue
            confianca = _CONFIANCA_POR_CRITERIO.get(linha["criterio"].strip(), _CONFIANCA_PADRAO_MUNDO)
            indice[_normalizar(nome)] = ResultadoGeocoding(
                lat=float(linha["latitude"]),
                lng=float(linha["longitude"]),
                nome_atual=f"{nome}, {pais}",
                fonte="gazetteer mundial (curado)",
                confianca=confianca,
            )
    return indice


_brasil: dict[str, ResultadoGeocoding] | None = None
_mundo: dict[str, ResultadoGeocoding] | None = None


def resolver_local(nome_lugar: str) -> ResultadoGeocoding | None:
    """Busca EXATA (normalizada) no gazetteer local. None se nao achar —
    nunca fuzzy-match, nunca inventa. Mundo primeiro, Brasil como fallback
    (com alias PT->planilha) — ver docstring do modulo pro porque dessa
    ordem (30 colisoes reais medidas, mundo certo em todas onde divergem)."""
    global _brasil, _mundo
    if _brasil is None:
        _brasil = _carregar_brasil()
    if _mundo is None:
        _mundo = _carregar_mundo()

    chave = _normalizar(nome_lugar)
    chave_mundo = _ALIAS_PT_MUNDO.get(chave, chave)
    if chave_mundo in _mundo:
        return _mundo[chave_mundo]

    if chave in _brasil:
        return _brasil[chave]

    return None
