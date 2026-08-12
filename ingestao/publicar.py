"""Ponte barata entre a revisão humana (passo 8) e o globo — não é a Fase 1
do CLAUDE.md (FastAPI + PostGIS), é o caminho mais simples que prova o loop
completo (livro → extração → revisão → mapa) sem construir backend/banco.

Pega os candidatos com status="aprovado" de um ou mais JSONs de
`ingerir_pdf.py`, geocodifica `local_nome_epoca` via Nominatim (passo 5,
`extracao.geocoding` — MVP do IA.md, aceita coordenada moderna) e funde no
`src/data/events.json` que o app React já lê, no formato de `HistoricalEvent`
(src/types/Event.ts).

Um aprovado só publica se tiver TODOS os campos obrigatórios (título,
categoria, local, data_inicio/fim/incerteza) E o Nominatim achar coordenada.
Faltando qualquer um, fica de fora — nunca inventa o que falta. Aparece no
relatório final como "não publicado", não desaparece silenciosamente. O
resultado do geocoding é salvo de volta no MESMO arquivo de entrada (cache:
rodar de novo não bate no Nominatim pra quem já foi resolvido).

Candidatos com o mesmo `grupo_correlacao` (confirmado por um humano em
`correlacionar.py` — ver `extracao/correlacao.py`) virem UM evento só,
corroborado por N fontes, em vez de N marcadores duplicados pro mesmo
acontecimento. Quando as fontes do grupo divergem em data ou local, isso
aparece como texto explícito no resumo publicado, não escondido.

Uso:
    ./.venv/Scripts/python.exe publicar.py amostras/saida_historia_antiga.json
    ./.venv/Scripts/python.exe publicar.py amostras/saida_historia_antiga.json amostras/saida_historia_moderna.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from extracao.geocoding import resolver as geocodificar

RAIZ = Path(__file__).resolve().parent.parent
EVENTS_JSON = RAIZ / "src" / "data" / "events.json"

# MEDIDO contra os 21 aprovados reais desta sessao: `confianca_local`
# (importance do Nominatim) separou limpo os acertos dos erros. Abaixo de
# 0.5 a busca resolveu pra um lugar homonimo sem relacao — "Reino Novo"
# (Egito) foi pro aeroporto de uma cidade chamada Reino no Brasil (0.38),
# "Quarta Cruzada"/Constantinopla foi pra uma RUA de mesmo nome em Buenos
# Aires (0.05), "Tratado descritivo do Brasil"/ABC foi pra sede da radio
# australiana ABC (nao tem confianca por sequer ter side chamado "ABC" ali),
# e "Bastilha" foi pra um vilarejo na Bretanha (0.11) em tres candidatos
# diferentes. Acima de 0.5 (Pantheon 0.58, Mapa-mundi da Babilonia 0.65,
# Basilica de Sao Pedro 0.66...) os resultados bateram com o lugar certo.
# Nao e' garantia — e' o unico sinal de confianca que a API gratuita da,
# ajustavel se a amostra futura mostrar que o corte esta' errado.
CONFIANCA_MINIMA = 0.5

# MEDIDO: "ABC" (sigla de 3 letras, extraida de "Tratado descritivo do
# Brasil") geocodificou pra sede da radio australiana ABC com confianca
# 0.66 — ACIMA do limiar, porque a Australian Broadcasting Corporation e'
# um lugar genuinamente proeminente, so' que errado pro nosso caso. Nome
# curto/sigla e' ambiguo mesmo quando o Nominatim "confia". Custo aceito:
# um nome de lugar historico curto mas legitimo (ex. "Ur", 2 letras) tambem
# cairia aqui — pior perder um acerto raro do que publicar um erro deste tipo.
TAMANHO_MINIMO_NOME_LUGAR = 4

# Espelha ERAS em src/utils/eras.ts. So' informativo no HistoricalEvent — o
# app filtra por ano numerico (data_inicio/data_fim), nao por este campo —
# mas mantido coerente com o resto do modelo de dados.
_ERAS = [
    ("pre_historia", -10000, -3300),
    ("idade_bronze", -3300, -1200),
    ("idade_ferro", -1200, 476),
    ("idade_media", 476, 1453),
    ("idade_moderna", 1453, 1789),
    ("idade_contemporanea", 1789, 2026),
]


def _era_do_ano(ano: int) -> str:
    for nome, inicio, fim in _ERAS:
        if inicio <= ano < fim:
            return nome
    return _ERAS[-1][0]


def _ano_de(data_iso: str) -> int:
    """Mesma logica de src/utils/date.ts:getYear — so' o ano, com sinal."""
    m = re.match(r"^(-?\d+)", data_iso)
    return int(m.group(1)) if m else 0


def _limpar(texto: str) -> str:
    """Colapsa espaco/quebra de linha interna num valor extraido.

    Achado numa ingestao real: span cruzando quebra de linha do PDF vira
    'Reino \\nNovo' no `valor` (ver IA.md). So' limpeza de EXIBICAO — nao
    mexe no dado extraido nem na proveniencia, que ficam intactos no JSON de
    origem.
    """
    return re.sub(r"\s+", " ", texto).strip()


def _importancia_por_mencao(titulo: str, todos: list[dict[str, Any]]) -> int:
    """Proxy auditavel que o IA.md sugeria e nunca tinha sido implementado
    ("numero de mencoes e paginas dedicadas") — nao e' medida rigorosa, mas
    e' melhor que um valor fixo, que seria pura invencao.
    """
    contagem = Counter(c["titulo"]["valor"].strip().lower() for c in todos if c["titulo"])
    n = contagem.get(titulo.strip().lower(), 1)
    if n >= 7:
        return 5
    if n >= 4:
        return 4
    if n >= 2:
        return 3
    return 2


def _id_estavel(candidato: dict[str, Any]) -> str:
    bruto = f"{candidato['fonte_id']}_{candidato['titulo']['proveniencia']['span_inicio']}"
    return "evt_" + re.sub(r"[^a-zA-Z0-9_]+", "-", bruto)


# Ordem de precisao — usada pra escolher, DENTRO de um grupo corroborado, qual
# data normalizada publicar quando as fontes nao concordam exatamente.
_PRECISAO_DATA = {"exata": 4, "ano": 3, "decada": 2, "seculo": 1, "aproximada": 0}


def converter_grupo(
    grupo: list[dict[str, Any]], todos_por_fonte: dict[str, list[dict[str, Any]]]
) -> tuple[dict[str, Any] | None, str]:
    """Converte um GRUPO de 1+ candidatos (aprovados, possivelmente de fontes
    diferentes — ver `grupo_correlacao` e `correlacionar.py`) num unico
    HistoricalEvent. Devolve (evento, motivo); `evento` e' None se nao
    publicar.

    Corroboracao (CLAUDE.md, "Validacao por consenso"): titulo/categoria/local
    vem do membro com titulo de maior confianca ("principal"); atores sao a
    UNIAO de todos os membros; a data e' a de maior precisao entre os que tem
    data normalizada. Quando as fontes DIVERGEM em data ou local, isso vira
    texto explicito no resumo em vez de escondido — mostrar a divergencia,
    nao forcar consenso, e' a regra que o CLAUDE.md ja' pedia.
    """
    principal = max(grupo, key=lambda c: (c["titulo"]["confianca"] if c["titulo"] else -1))

    faltando = [
        nome
        for nome, valor in (
            ("titulo", principal["titulo"]),
            ("categoria", principal["categoria"]),
            ("local_nome_epoca", principal["local_nome_epoca"]),
        )
        if valor is None
    ]
    if faltando:
        return None, f"faltam campos: {', '.join(faltando)}"

    com_data = [c for c in grupo if c["data_inicio"] and c["data_fim"] and c["incerteza_data"]]
    if not com_data:
        return None, "sem data normalizada em nenhum membro do grupo (passo 6 nao resolveu)"
    membro_data = max(com_data, key=lambda c: _PRECISAO_DATA.get(c["incerteza_data"], -1))

    nome_lugar = principal["local_nome_epoca"]["valor"].strip()
    if len(nome_lugar) < TAMANHO_MINIMO_NOME_LUGAR:
        return None, f"nome de local muito curto/sigla ({nome_lugar!r}) — ambiguo demais pra geocodificar com seguranca"

    if principal["lat"] is None:
        try:
            resultado = geocodificar(nome_lugar)
        except RuntimeError as erro:
            # Falha de rede (timeout, DNS, Nominatim fora do ar) NAO e' o
            # mesmo que "nao existe" — nao marca como resolvido, so' pula
            # esta rodada. Rodar de novo tenta de novo (lat ainda e' None).
            return None, f"falha de rede ao geocodificar — tentar de novo depois ({erro})"
        if resultado is None:
            return None, f"Nominatim nao achou {nome_lugar!r}"
        principal["lat"] = resultado.lat
        principal["lng"] = resultado.lng
        principal["geocoding_fonte"] = resultado.fonte
        principal["confianca_local"] = resultado.confianca
        principal["_nome_atual_geocodificado"] = resultado.nome_atual

    # Confianca baixa acontece tanto em resultado novo quanto em cache de
    # uma rodada anterior — checar aqui, nao so' no momento da busca, pra
    # nao publicar um lugar homonimo so' porque ja' tinha sido "resolvido"
    # antes deste limiar existir.
    if principal["confianca_local"] is not None and principal["confianca_local"] < CONFIANCA_MINIMA:
        return None, (
            f"geocoding de baixa confianca ({principal['confianca_local']:.2f} < {CONFIANCA_MINIMA}) "
            f"para {nome_lugar!r} -> {principal.get('_nome_atual_geocodificado', '?')!r} — "
            "provavelmente lugar homonimo errado"
        )

    fontes = sorted({c["fonte_id"] for c in grupo})
    corroborado = len(fontes) > 1

    resumo = principal["resumo"] or _limpar(principal["titulo"]["valor"])
    if corroborado:
        resumo += f" (corroborado por {len(fontes)} fontes: {', '.join(fontes)}.)"

    datas_distintas = {(c["data_inicio"], c["data_fim"]) for c in com_data}
    if len(datas_distintas) > 1:
        outras = "; ".join(
            f"{c['fonte_id']}: {c['data_inicio']}..{c['data_fim']}"
            for c in com_data
            if (c["data_inicio"], c["data_fim"]) != (membro_data["data_inicio"], membro_data["data_fim"])
        )
        resumo += f" [Fontes divergem na data — {outras}.]"

    locais_distintos = {c["local_nome_epoca"]["valor"] for c in grupo if c["local_nome_epoca"]}
    if len(locais_distintos) > 1:
        outros = ", ".join(sorted(locais_distintos - {nome_lugar}))
        resumo += f" [Fontes divergem no local — outra(s) fonte(s) diz(em) {outros!r}.]"

    atores = sorted(
        {_limpar(a["valor"]) for c in grupo for a in c["atores"]},
        key=str.lower,
    )

    importancia = max(
        _importancia_por_mencao(c["titulo"]["valor"], todos_por_fonte.get(c["fonte_id"], []))
        for c in grupo
        if c["titulo"]
    )
    if corroborado:
        # Duas fontes independentes descreverem o mesmo acontecimento e' em
        # si um sinal de relevancia historica — nao e' o mesmo proxy de
        # "mencoes dentro de um livro", mas e' real, nao inventado.
        importancia = min(5, importancia + 1)

    evento = {
        "id": _id_estavel(principal),
        "titulo": _limpar(principal["titulo"]["valor"]),
        "resumo": resumo,
        "data_inicio": membro_data["data_inicio"],
        "data_fim": membro_data["data_fim"],
        "incerteza_data": membro_data["incerteza_data"],
        "lat": principal["lat"],
        "lng": principal["lng"],
        "local_nome_epoca": _limpar(nome_lugar),
        "local_nome_atual": principal.get("_nome_atual_geocodificado") or _limpar(nome_lugar),
        "geocoding_fonte": principal["geocoding_fonte"],
        "confianca_local": principal["confianca_local"],
        "nivel_importancia": importancia,
        "era": _era_do_ano(_ano_de(membro_data["data_inicio"])),
        "categoria": principal["categoria"]["valor"],
        "atores": atores,
        "tags": [],
    }
    return evento, "publicado"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("arquivos", type=Path, nargs="+")
    args = parser.parse_args()

    eventos_existentes: list[dict[str, Any]] = json.loads(EVENTS_JSON.read_text(encoding="utf-8"))
    ids_existentes = {e["id"] for e in eventos_existentes}

    dados: dict[Path, list[dict[str, Any]]] = {
        caminho: json.loads(caminho.read_text(encoding="utf-8")) for caminho in args.arquivos
    }
    todos_por_fonte: dict[str, list[dict[str, Any]]] = {}
    for lista in dados.values():
        if lista:
            todos_por_fonte[lista[0]["fonte_id"]] = lista

    # Agrupa aprovados por `grupo_correlacao` (ver correlacionar.py) — um
    # grupo de 2+ fontes vira UM evento corroborado, nao N marcadores
    # duplicados. Sem grupo, cada candidato e' seu proprio grupo de 1.
    grupos: dict[str, list[dict[str, Any]]] = {}
    soltos: list[list[dict[str, Any]]] = []
    for caminho, lista in dados.items():
        print(f"{caminho.name}: {sum(1 for c in lista if c['status'] == 'aprovado')} aprovado(s)")
        for c in lista:
            if c["status"] != "aprovado":
                continue
            if c.get("grupo_correlacao"):
                grupos.setdefault(c["grupo_correlacao"], []).append(c)
            else:
                soltos.append([c])

    novos: list[dict[str, Any]] = []
    nao_publicados: list[tuple[str, str]] = []
    ja_publicados = 0
    corroborados = 0

    for grupo in list(grupos.values()) + soltos:
        evento, motivo = converter_grupo(grupo, todos_por_fonte)
        if evento is None:
            principal = next((c for c in grupo if c["titulo"]), None)
            titulo = principal["titulo"]["valor"] if principal else "(sem titulo)"
            nao_publicados.append((titulo, motivo))
        elif evento["id"] in ids_existentes:
            ja_publicados += 1
        else:
            novos.append(evento)
            ids_existentes.add(evento["id"])
            if len(grupo) > 1:
                corroborados += 1

    for caminho, lista in dados.items():
        # Persiste o resultado do geocoding de volta no arquivo de origem —
        # e' o cache: rodar de novo nao bate no Nominatim pro que ja' foi
        # resolvido (ou descartado por falta de campo, que nao muda mesmo).
        caminho.write_text(json.dumps(lista, ensure_ascii=False, indent=2), encoding="utf-8")

    if novos:
        EVENTS_JSON.write_text(
            json.dumps(eventos_existentes + novos, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(f"\n{'=' * 72}")
    print(f"Publicados agora: {len(novos)} (dos quais corroborados por 2+ fontes: {corroborados})")
    print(f"Ja' publicados antes (id repetido, pulados): {ja_publicados}")
    print(f"Nao publicados: {len(nao_publicados)}")
    for titulo, motivo in nao_publicados:
        print(f"  {titulo!r}: {motivo}")
    if novos:
        print(f"\nAtualizado: {EVENTS_JSON.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
