"""Passos 1, 6 e 7 do IA.md: texto -> entidades tipadas com span ->
EventoCandidato, com data normalizada e resumo por template.

O que este modulo NAO faz, de proposito:
  - nao gera texto (GLiNER so' marca spans que existem no original; o resumo
    e' slot-filling por template, nunca geracao livre — ver extracao.resumo);
  - nao resolve coordenada (geocoding e' stub — passo 5);
  - nao decide o que entra no mapa (passo 8, revisao humana).

Agrupamento em eventos: uma frase => um candidato. E' uma heuristica explicita,
nao uma solucao do passo 4 ("ligar num evento estruturado"), que o proprio
IA.md classifica como o elo mais fraco do pipeline.

Estrutura do livro (extracao.estrutura) marca cada candidato com a secao
onde apareceu (narrativa ou nao — "Objetivos"/"Resposta Comentada" nao sao
relato historico). So' marca, nao filtra aqui — quem decide o que fazer com
isso e' revisar.py (ou o humano, olhando o campo).
"""

from __future__ import annotations

from typing import Any

from .citacoes import filtrar_citacoes
from .datas import preencher_datas
from .estrutura import detectar_secoes, secao_em
from .modelo import CampoExtraido, EventoCandidato, Proveniencia
from .resumo import preencher_resumo
from .rotulos import categoria_de, e_ator, e_data, e_local, grupos_de_rotulos
from .segmentacao import Frase, segmentar_frases

MODELO_PADRAO = "urchade/gliner_multi-v2.1"

# Chaves que a sondagem (sondar_api.py) confirmou existirem na saida real do
# GLiNER 0.2.28 — o README oficial documenta apenas `text` e `label`.
_CHAVES_ESPERADAS = {"start", "end", "text", "label", "score"}

# Chamar o GLiNER com uma PAGINA INTEIRA de uma vez (~400+ tokens) dilui o
# score do mesmo jeito que rotulos demais numa chamada so' (rotulos.py) —
# so' que aqui e' texto demais, nao rotulo demais. MEDIDO numa frase real
# (Historia Antiga, pag. 50, "Dion Cassio... 229 d.C."): 5 entidades boas
# (0.30-0.97) rodando ISOLADA, ZERO rodando junto com o resto da pagina —
# mesmo span, mesmo texto, so' o tamanho da chamada mudou. Pagina inteira
# tambem estoura o teto de 384 tokens do GLiNER e trunca em silencio; o
# limite abaixo evita as duas coisas de uma vez. ~800 chars fica bem abaixo
# de 384 tokens mesmo no pior caso medido (2015 chars ~ 423 tokens, ~4.76
# chars/token) — margem generosa de proposito, nao o limite exato.
_LIMITE_CHARS_POR_BLOCO = 800


def _agrupar_em_blocos(frases: list[Frase]) -> list[tuple[int, int]]:
    """Agrupa frases consecutivas em blocos de offset absoluto (inicio, fim)
    com no maximo `_LIMITE_CHARS_POR_BLOCO` chars cada — nunca quebra uma
    frase no meio. `segmentar_frases` cobre a pagina inteira sem buraco
    (ver docstring de `Frase.contem`), entao encadear os pares inicio/fim
    aqui preserva essa cobertura, so' em pedacos menores.
    """
    if not frases:
        return []
    blocos: list[tuple[int, int]] = []
    inicio_bloco = frases[0].inicio
    fim_bloco = frases[0].fim
    for frase in frases[1:]:
        if frase.fim - inicio_bloco > _LIMITE_CHARS_POR_BLOCO:
            blocos.append((inicio_bloco, fim_bloco))
            inicio_bloco = frase.inicio
        fim_bloco = frase.fim
    blocos.append((inicio_bloco, fim_bloco))
    return blocos


class ExtratorGLiNER:
    def __init__(self, nome_modelo: str = MODELO_PADRAO) -> None:
        self.nome_modelo = nome_modelo
        self._modelo: Any | None = None

    def _carregar(self) -> Any:
        if self._modelo is None:
            import torch
            from gliner import GLiNER  # import tardio: carregar torch custa segundos

            # `from_pretrained` carrega em CPU por padrao (map_location='cpu'
            # e' o default do proprio gliner) mesmo com GPU disponivel — nao
            # e' automatico. MEDIDO: 4 chamadas predict_entities (uma pagina)
            # ~40s em CPU, ~3s numa RTX 3060 — a diferenca importa demais pra
            # deixar no default. Custo unico por processo: carregar na GPU
            # leva mais tempo (~180s medido) que na CPU, mas isso e' pago uma
            # vez, nao por pagina — compensa a partir da segunda pagina.
            dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
            self._modelo = GLiNER.from_pretrained(self.nome_modelo, map_location=dispositivo)
        return self._modelo

    def entidades_cruas(self, texto: str) -> list[dict[str, Any]]:
        """Saida do GLiNER: uma chamada por grupo de rotulos, nao uma so'.

        Ver `grupos_de_rotulos` — juntar todos os rotulos numa chamada derruba
        o score cerca de 3x por competicao entre rotulos.
        """
        modelo = self._carregar()

        entidades: list[dict[str, Any]] = []
        for rotulos, limiar in grupos_de_rotulos().values():
            entidades.extend(modelo.predict_entities(texto, rotulos, threshold=limiar))

        # MEDIDO numa revisao real: "(CARDOSO, 1999)" virava data de zigurate,
        # "(KEMP, 1987)" virava data de piramide — ano de citacao bibliografica
        # lido como ano do evento. Ver extracao/citacoes.py.
        entidades = filtrar_citacoes(entidades, texto)

        for ent in entidades:
            faltando = _CHAVES_ESPERADAS - set(ent)
            if faltando:
                # Falha ruidosa: sem span nao ha proveniencia, e sem
                # proveniencia este pipeline inteiro perde a razao de existir.
                raise RuntimeError(
                    f"GLiNER retornou entidade sem as chaves {sorted(faltando)}: {ent}. "
                    "A versao instalada mudou o formato — rode sondar_api.py."
                )
        return entidades

    def _entidades_em_blocos(self, texto: str, frases: list[Frase]) -> list[dict[str, Any]]:
        """Chama `entidades_cruas` uma vez por BLOCO de frases consecutivas
        (nunca a pagina inteira), depois desloca `start`/`end` de volta pro
        offset absoluto da pagina — e' esse deslocamento que preserva a
        proveniencia (span tem que continuar indexando `texto`, nao o bloco).
        Ver `_LIMITE_CHARS_POR_BLOCO` pro porque disso existir.
        """
        entidades: list[dict[str, Any]] = []
        for inicio_bloco, fim_bloco in _agrupar_em_blocos(frases):
            bloco = texto[inicio_bloco:fim_bloco]
            for ent in self.entidades_cruas(bloco):
                entidades.append(
                    {**ent, "start": ent["start"] + inicio_bloco, "end": ent["end"] + inicio_bloco}
                )
        return entidades

    def extrair(
        self,
        texto: str,
        fonte_id: str,
        pagina: int | None = None,
    ) -> list[EventoCandidato]:
        frases = segmentar_frases(texto)
        entidades = self._entidades_em_blocos(texto, frases)
        secoes = detectar_secoes(texto)

        candidatos: list[EventoCandidato] = []
        for frase in frases:
            do_trecho = [
                e for e in entidades if frase.contem(e["start"], e["end"])
            ]
            if not do_trecho:
                continue

            candidato = EventoCandidato(fonte_id=fonte_id, texto_origem=texto)
            melhor_score_evento = 0.0
            melhor_score_local = 0.0

            for ent in do_trecho:
                campo = _para_campo(ent, texto, fonte_id, pagina)
                rotulo = ent["label"]

                categoria = categoria_de(rotulo)
                if categoria is not None:
                    # Varios rotulos de evento podem bater na mesma frase; fica
                    # o de maior score. O valor guardado e' a categoria do
                    # modelo de dados, mas a proveniencia aponta pro trecho
                    # que justificou a classificacao.
                    if ent["score"] > melhor_score_evento:
                        melhor_score_evento = ent["score"]
                        candidato.titulo = campo
                        candidato.categoria = CampoExtraido(
                            valor=categoria,
                            confianca=float(ent["score"]),
                            proveniencia=campo.proveniencia,
                            rotulo_origem=rotulo,
                        )
                elif e_ator(rotulo):
                    candidato.atores.append(campo)
                elif e_local(rotulo):
                    # "lugar" e "monumento" costumam marcar o mesmo trecho com
                    # scores diferentes; fica o mais confiante.
                    if ent["score"] > melhor_score_local:
                        melhor_score_local = ent["score"]
                        candidato.local_nome_epoca = campo
                elif e_data(rotulo):
                    candidato.datas_brutas.append(campo)

            # A secao e' calculada pela posicao do campo ANCORA (titulo, ou
            # o proximo disponivel), nao pelo inicio da frase inteira.
            # MEDIDO: blocos de exercicio sem pontuacao interna (ex.
            # "Atividade Final\nLeia o fragmento...") virjam UMA frase so'
            # pra segmentar_frases, cujo inicio fica antes do proprio
            # cabecalho — usar frase.inicio la' perdia 2 dos 3 casos reais
            # que a revisao manual (ver IA.md) tinha identificado.
            ancora = candidato.titulo or candidato.categoria or candidato.local_nome_epoca
            if ancora is not None:
                secao = secao_em(ancora.proveniencia.span_inicio, secoes)
                if secao is not None:
                    candidato.secao_titulo = secao.titulo
                    candidato.secao_narrativa = secao.narrativa

            candidatos.append(candidato)

        for candidato in candidatos:
            preencher_datas(candidato)
            preencher_resumo(candidato)

        return candidatos


def _para_campo(
    ent: dict[str, Any],
    texto: str,
    fonte_id: str,
    pagina: int | None,
) -> CampoExtraido:
    trecho = texto[ent["start"] : ent["end"]]
    if trecho != ent["text"]:
        raise RuntimeError(
            f"span nao indexa o texto original: {ent!r} -> {trecho!r}. "
            "Proveniencia seria ficticia."
        )
    return CampoExtraido(
        valor=ent["text"],
        confianca=float(ent["score"]),
        proveniencia=Proveniencia(
            fonte_id=fonte_id,
            span_inicio=int(ent["start"]),
            span_fim=int(ent["end"]),
            trecho=trecho,
            pagina=pagina,
        ),
        rotulo_origem=ent["label"],
    )
