"""Testes das invariantes do passo 1.

Os testes que importam aqui nao sao de acuracia (isso e' `spike_passo1.py`,
que mede contra gabarito) e sim das regras que, se quebrarem em silencio,
corrompem o banco: proveniencia que nao aponta pro texto, campo criado sem
span, e geocoding chutando coordenada.

Rodam sem carregar o modelo nem bater rede — sao rapidos de proposito, para
poderem rodar sempre. O teste de ponta a ponta com GLiNER (que baixa 1,2 GB)
fica atras de COM_MODELO=1; o de geocoding real (Nominatim, passo 5) fica
atras de COM_REDE=1.

Uso:
    ./.venv/bin/python -m unittest testes -v
    COM_MODELO=1 ./.venv/bin/python -m unittest testes -v
    COM_REDE=1 ./.venv/bin/python -m unittest testes -v
"""

from __future__ import annotations

import os
import unittest

from extracao.citacoes import esta_dentro_de_citacao, filtrar_citacoes, spans_de_citacao
from extracao.correlacao import candidatos_correlacionados, pontuar
from extracao.datas import ano_legivel, normalizar as normalizar_data, preencher_datas
from extracao.estrutura import detectar_secoes, secao_em
from extracao import gazetteer
from extracao.geocoding import resolver as resolver_geocoding
from extracao.modelo import CampoExtraido, EventoCandidato, Proveniencia
from extracao.resumo import gerar_resumo
from extracao.segmentacao import segmentar_frases

TEXTO = "Em 1453, Mehmed II conquistou Constantinopla."


class TesteProveniencia(unittest.TestCase):
    def test_span_valido_confere_com_o_texto(self) -> None:
        p = Proveniencia(
            fonte_id="f1", span_inicio=30, span_fim=44, trecho="Constantinopla"
        )
        self.assertTrue(p.confere_com(TEXTO))

    def test_span_deslocado_e_detectado(self) -> None:
        """A defesa contra proveniencia que 'parece' certa mas aponta errado."""
        p = Proveniencia(
            fonte_id="f1", span_inicio=0, span_fim=14, trecho="Constantinopla"
        )
        self.assertFalse(p.confere_com(TEXTO))

    def test_span_invertido_e_rejeitado(self) -> None:
        with self.assertRaises(ValueError):
            Proveniencia(fonte_id="f1", span_inicio=44, span_fim=30, trecho="x")

    def test_span_vazio_e_rejeitado(self) -> None:
        with self.assertRaises(ValueError):
            Proveniencia(fonte_id="f1", span_inicio=10, span_fim=10, trecho="x")

    def test_span_negativo_e_rejeitado(self) -> None:
        with self.assertRaises(ValueError):
            Proveniencia(fonte_id="f1", span_inicio=-1, span_fim=5, trecho="x")

    def test_trecho_vazio_e_rejeitado(self) -> None:
        with self.assertRaises(ValueError):
            Proveniencia(fonte_id="f1", span_inicio=0, span_fim=5, trecho="")


class TesteCampoExtraido(unittest.TestCase):
    def _prov(self) -> Proveniencia:
        return Proveniencia(
            fonte_id="f1", span_inicio=30, span_fim=44, trecho="Constantinopla"
        )

    def test_nao_existe_campo_sem_proveniencia(self) -> None:
        """A regra central do IA.md, garantida pela assinatura do construtor."""
        with self.assertRaises(TypeError):
            CampoExtraido(valor="Constantinopla", confianca=0.9)  # type: ignore[call-arg]

    def test_valor_vazio_e_rejeitado(self) -> None:
        with self.assertRaises(ValueError):
            CampoExtraido(valor="   ", confianca=0.9, proveniencia=self._prov())

    def test_confianca_fora_do_intervalo_e_rejeitada(self) -> None:
        for ruim in (-0.1, 1.5):
            with self.subTest(confianca=ruim):
                with self.assertRaises(ValueError):
                    CampoExtraido(
                        valor="x", confianca=ruim, proveniencia=self._prov()
                    )


class TesteEventoCandidato(unittest.TestCase):
    def test_candidato_vazio_esta_incompleto(self) -> None:
        c = EventoCandidato(fonte_id="f1", texto_origem=TEXTO)
        self.assertFalse(c.esta_completo())
        self.assertEqual(
            sorted(c.campos_faltando()),
            ["categoria", "data_bruta", "local_nome_epoca", "titulo"],
        )

    def test_candidato_nasce_pendente_de_revisao(self) -> None:
        """Nada extraido pode chegar ao mapa sem passar por uma pessoa."""
        c = EventoCandidato(fonte_id="f1", texto_origem=TEXTO)
        self.assertEqual(c.status, "pendente")

    def test_proveniencia_mentirosa_e_detectada(self) -> None:
        c = EventoCandidato(fonte_id="f1", texto_origem=TEXTO)
        c.local_nome_epoca = CampoExtraido(
            valor="Constantinopla",
            confianca=0.9,
            proveniencia=Proveniencia(
                fonte_id="f1", span_inicio=0, span_fim=14, trecho="Constantinopla"
            ),
        )
        self.assertFalse(c.proveniencia_integra())


class TesteSegmentacao(unittest.TestCase):
    def test_offsets_indexam_o_texto_original(self) -> None:
        texto = "Em 1453 caiu Constantinopla. Em 1789 caiu a Bastilha."
        for frase in segmentar_frases(texto):
            self.assertEqual(texto[frase.inicio : frase.fim], frase.texto)

    def test_nao_quebra_frase_em_abreviacao_de_era(self) -> None:
        """'a.C.' tem ponto mas nao termina frase — quebrar aqui parte a data."""
        texto = "Por volta de 2560 a.C., os egipcios ergueram a piramide."
        self.assertEqual(len(segmentar_frases(texto)), 1)

    def test_separa_frases_de_verdade(self) -> None:
        texto = "Caiu Constantinopla. Caiu a Bastilha."
        self.assertEqual(len(segmentar_frases(texto)), 2)

    def test_texto_vazio_nao_quebra(self) -> None:
        self.assertEqual(segmentar_frases("   "), [])


@unittest.skipUnless(
    os.environ.get("COM_REDE") == "1",
    "define COM_REDE=1 para rodar (bate no Nominatim de verdade, rede externa)",
)
class TesteGeocodingComRede(unittest.TestCase):
    """Desde que o passo 5 deixou de ser stub, testar geocoding bate rede de
    verdade — por isso fica atras de COM_REDE=1, no mesmo espirito de
    COM_MODELO=1: a suite rapida nunca depende de servico externo."""

    def test_nome_sem_sentido_nao_inventa_coordenada(self) -> None:
        """Um lat/lng chutado seria pior que nenhum: cravaria ponto errado."""
        self.assertIsNone(
            resolver_geocoding("xyzxyzxyz-lugar-que-nao-existe-de-verdade-em-lugar-nenhum")
        )

    def test_resolve_lugar_conhecido(self) -> None:
        resultado = resolver_geocoding("Roma, Italia")
        self.assertIsNotNone(resultado)
        self.assertAlmostEqual(resultado.lat, 41.9, delta=1.0)
        self.assertAlmostEqual(resultado.lng, 12.5, delta=1.0)
        self.assertEqual(resultado.fonte, "Nominatim")


class TesteGazetteerLocal(unittest.TestCase):
    """Sem rede: resolver_local so' faz exact-match (normalizado) contra os
    dois CSVs curados. resolver_geocoding (geocoding.resolver) tenta essa
    camada primeiro — confirmado aqui indiretamente pela fonte devolvida."""

    def test_municipio_brasileiro_resolve_via_ibge(self) -> None:
        resultado = gazetteer.resolver_local("Manaus")
        self.assertIsNotNone(resultado)
        self.assertAlmostEqual(resultado.lat, -3.134691, delta=0.01)
        self.assertAlmostEqual(resultado.lng, -60.023335, delta=0.01)
        self.assertEqual(resultado.fonte, "IBGE (municipios)")
        self.assertEqual(resultado.confianca, 0.9)

    def test_municipio_brasileiro_ignora_caixa_e_acento(self) -> None:
        self.assertIsNotNone(gazetteer.resolver_local("porto velho"))
        self.assertIsNotNone(gazetteer.resolver_local("PORTO VELHO"))

    def test_cidade_mundial_curada_resolve(self) -> None:
        resultado = gazetteer.resolver_local("Kabul")
        self.assertIsNotNone(resultado)
        self.assertAlmostEqual(resultado.lat, 34.52813, delta=0.01)
        self.assertEqual(resultado.fonte, "gazetteer mundial (curado)")
        self.assertEqual(resultado.confianca, 0.85)  # historical/curated

    def test_alias_pt_para_planilha_mundial_resolve(self) -> None:
        """"Atenas" -> "athens" via alias, batendo na planilha mundial completa."""
        resultado = gazetteer.resolver_local("Atenas")
        self.assertIsNotNone(resultado)
        self.assertAlmostEqual(resultado.lat, 37.98376, delta=0.01)
        self.assertEqual(resultado.fonte, "gazetteer mundial (curado)")

    def test_nome_desconhecido_devolve_none_sem_fuzzy_match(self) -> None:
        self.assertIsNone(gazetteer.resolver_local("lugar-que-nao-existe-em-nenhum-csv"))

    def test_mundo_tem_prioridade_sobre_brasil_quando_ambiguo(self) -> None:
        """"Braga" existe como municipio brasileiro E como cidade em Portugal
        (colisao real medida contra os dois CSVs completos) — pro corpus de
        historia antiga/moderna, a cidade mundial e' a resposta certa."""
        resultado = gazetteer.resolver_local("Braga")
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado.fonte, "gazetteer mundial (curado)")
        self.assertAlmostEqual(resultado.lat, 41.5514, delta=0.01)

    def test_municipio_sem_colisao_ainda_resolve_pro_brasil(self) -> None:
        """Belem (Para) nao colide com nenhuma cidade da planilha mundial —
        Bethlehem la' esta' em ingles, nao "Belem" — entao a ordem nao muda
        o resultado: ainda resolve pro Brasil, so' porque e' o unico lado
        que tem esse nome."""
        resultado = gazetteer.resolver_local("Belem")
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado.fonte, "IBGE (municipios)")

    def test_resolver_geocoding_usa_gazetteer_antes_de_nominatim(self) -> None:
        """geocoding.resolver() tem que devolver o resultado do gazetteer sem
        bater rede — testavel indiretamente pela fonte, sem precisar de
        COM_REDE=1 porque o gazetteer resolve antes de qualquer rede entrar
        em jogo."""
        resultado = resolver_geocoding("Kabul")
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado.fonte, "gazetteer mundial (curado)")


class TesteNormalizacaoData(unittest.TestCase):
    def test_ano_isolado(self) -> None:
        r = normalizar_data("1453")
        self.assertEqual((r.data_inicio, r.data_fim, r.incerteza_data), ("1453-01-01", "1453-12-31", "ano"))

    def test_ano_isolado_antes_de_cristo(self) -> None:
        """2560 a.C. -> ano astronomico -2559 (ano 1 a.C. = astronomico 0)."""
        r = normalizar_data("2560 a.C.")
        self.assertEqual((r.data_inicio, r.data_fim, r.incerteza_data), ("-2559-01-01", "-2559-12-31", "ano"))

    def test_data_completa_dia_mes_ano(self) -> None:
        r = normalizar_data("29 de maio de 1453")
        self.assertEqual((r.data_inicio, r.data_fim, r.incerteza_data), ("1453-05-29", "1453-05-29", "exata"))

    def test_mes_e_ano_sem_dia(self) -> None:
        """Sem nivel 'mes' no modelo de dados: rotula 'ano', mas o intervalo
        reflete o mes conhecido (mais estreito que o ano inteiro)."""
        r = normalizar_data("outubro de 1347")
        self.assertEqual((r.data_inicio, r.data_fim, r.incerteza_data), ("1347-10-01", "1347-10-31", "ano"))

    def test_decada(self) -> None:
        r = normalizar_data("década de 1980")
        self.assertEqual((r.data_inicio, r.data_fim, r.incerteza_data), ("1980-01-01", "1989-12-31", "decada"))

    def test_seculo_romano(self) -> None:
        r = normalizar_data("século XV")
        self.assertEqual((r.data_inicio, r.data_fim, r.incerteza_data), ("1401-01-01", "1500-12-31", "seculo"))

    def test_seculo_antes_de_cristo(self) -> None:
        r = normalizar_data("século XV a.C.")
        self.assertEqual((r.data_inicio, r.data_fim, r.incerteza_data), ("-1499-01-01", "-1400-12-31", "seculo"))

    def test_marcador_de_aproximacao_no_contexto_sobrepoe_incerteza(self) -> None:
        """'por volta de' raramente entra no span da entidade — por isso o
        marcador e' buscado na janela de contexto, nao so' no valor bruto."""
        r = normalizar_data("2560 a.C.", contexto="por volta de 2560 a.C.")
        self.assertEqual(r.incerteza_data, "aproximada")

    def test_texto_sem_data_reconhecivel_nao_inventa(self) -> None:
        self.assertIsNone(normalizar_data("em algum momento"))

    def test_ano_legivel_e_o_inverso_de_iso(self) -> None:
        self.assertEqual(ano_legivel("1453-01-01"), "1453")
        self.assertEqual(ano_legivel("-2559-01-01"), "2560 a.C.")

    def test_preencher_datas_usa_janela_de_contexto_do_span(self) -> None:
        """Fim a fim (sem GLiNER): a proveniencia real do span e' o que
        localiza a janela onde 'por volta de' e' procurado."""
        texto = "Por volta de 2560 a.C., os egípcios ergueram a pirâmide."
        raw = "2560 a.C."
        inicio = texto.index(raw)
        candidato = EventoCandidato(fonte_id="f1", texto_origem=texto)
        candidato.datas_brutas.append(
            CampoExtraido(
                valor=raw,
                confianca=0.5,
                proveniencia=Proveniencia(
                    fonte_id="f1",
                    span_inicio=inicio,
                    span_fim=inicio + len(raw),
                    trecho=raw,
                ),
                rotulo_origem="período",
            )
        )
        preencher_datas(candidato)
        self.assertEqual(candidato.data_inicio, "-2559-01-01")
        self.assertEqual(candidato.incerteza_data, "aproximada")

    def test_preencher_datas_sem_datas_brutas_nao_faz_nada(self) -> None:
        candidato = EventoCandidato(fonte_id="f1", texto_origem="sem data aqui")
        preencher_datas(candidato)
        self.assertIsNone(candidato.data_inicio)


class TesteEstruturaDoLivro(unittest.TestCase):
    def test_reconhece_marcador_de_licao_real(self) -> None:
        texto = "Aula 3 – O trabalho com modelos: o Mediterrâneo\nTexto qualquer da aula aqui."
        secoes = detectar_secoes(texto)
        self.assertEqual(len(secoes), 1)
        self.assertTrue(secoes[0].titulo.startswith("Aula 3"))
        self.assertTrue(secoes[0].narrativa)

    def test_reconhece_rotulo_nao_narrativo_isolado(self) -> None:
        """Achado numa ingestao real (ver IA.md): candidatos sob 'Objetivos'
        e 'Resposta Comentada' nao eram evento, eram aparato didatico."""
        texto = "Algum texto antes.\nObjetivos\nEsperamos que você aprenda X."
        secoes = detectar_secoes(texto)
        self.assertEqual(len(secoes), 1)
        self.assertEqual(secoes[0].titulo, "Objetivos")
        self.assertFalse(secoes[0].narrativa)

    def test_palavra_do_rotulo_dentro_de_frase_nao_dispara(self) -> None:
        """So' conta quando a linha INTEIRA e' o rotulo — nao uma palavra
        qualquer dentro de uma frase de narrativa comum."""
        texto = "Os objetivos desta pesquisa incluem a análise de fontes."
        self.assertEqual(detectar_secoes(texto), [])

    def test_secao_em_acha_a_mais_proxima_antes_da_posicao(self) -> None:
        texto = "Objetivos\nFrase 1.\nAula 4 – Roma\nFrase 2."
        secoes = detectar_secoes(texto)
        pos_frase1 = texto.index("Frase 1")
        pos_frase2 = texto.index("Frase 2")

        secao1 = secao_em(pos_frase1, secoes)
        self.assertEqual(secao1.titulo, "Objetivos")
        self.assertFalse(secao1.narrativa)

        secao2 = secao_em(pos_frase2, secoes)
        self.assertTrue(secao2.titulo.startswith("Aula 4"))
        self.assertTrue(secao2.narrativa)

    def test_posicao_antes_de_qualquer_cabecalho_e_none(self) -> None:
        texto = "Frase antes de qualquer cabecalho.\nObjetivos\nFrase depois."
        secoes = detectar_secoes(texto)
        self.assertIsNone(secao_em(0, secoes))

    def test_sem_cabecalho_nenhum_devolve_lista_vazia(self) -> None:
        self.assertEqual(detectar_secoes("So' narrativa comum, sem secao nenhuma aqui."), [])

    def test_bloco_sem_pontuacao_interna_precisa_de_ancora_no_campo_certo(self) -> None:
        """Achado numa ingestao real (Historia Antiga, pag. 267): um bloco de
        exercicio sem ponto interno ("Atividade Final\\nLeia o fragmento...")
        vira UMA frase so' pra segmentar_frases, cujo INICIO fica antes do
        cabeçalho. Usar o inicio da frase (em vez da posicao da entidade que
        vira titulo) fazia a secao "Atividade Final" nao ser detectada —
        corrigido em extrator.py usando a posicao do campo ancora, nao da
        frase. Este teste fixa esse comportamento no nivel de secao_em."""
        texto = (
            "Aula 10 – Monarquia divina\n"
            "Módulo 3\n"
            "Atividade Final\n"
            "Leia o fragmento: pirâmides, riqueza evidente (KEMP, 1987).\n"
        )
        secoes = detectar_secoes(texto)
        pos_inicio_do_bloco = 0  # onde `frase.inicio` cairia (bug antigo)
        pos_da_entidade_titulo = texto.index("pirâmides")  # onde o campo ancora fica

        # No inicio do bloco (posicao 0), a secao vigente ainda e' o titulo da
        # aula (narrativo) — o bug antigo pegava exatamente essa secao ERRADA
        # pra um candidato que na verdade esta' dentro de "Atividade Final".
        secao_no_inicio = secao_em(pos_inicio_do_bloco, secoes)
        self.assertTrue(secao_no_inicio.narrativa)

        secao_correta = secao_em(pos_da_entidade_titulo, secoes)
        self.assertEqual(secao_correta.titulo, "Atividade Final")
        self.assertFalse(secao_correta.narrativa)


def _cand(titulo=None, local=None, data_inicio=None, data_fim=None):
    """Dict minimo no formato que correlacao.py espera (o mesmo shape do JSON
    de ingerir_pdf.py) — nao precisa da dataclass EventoCandidato inteira
    pra testar so' a logica de pontuacao."""
    return {
        "titulo": {"valor": titulo} if titulo else None,
        "local_nome_epoca": {"valor": local} if local else None,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
    }


class TesteCorrelacaoEntreFontes(unittest.TestCase):
    """CLAUDE.md, secao 'Validacao por consenso': nao guardar 'a verdade',
    corroborar quando fontes independentes concordam. Nunca testado antes
    porque nunca tinha sido implementado."""

    def test_titulos_parecidos_e_mesma_data_corroboram(self) -> None:
        a = _cand("Queda de Constantinopla", "Constantinopla", "1453-05-29", "1453-05-29")
        b = _cand("A queda de Constantinopla", "Istambul", "1453-01-01", "1453-12-31")
        self.assertGreaterEqual(pontuar(a, b), 0.5)

    def test_titulos_sem_nada_em_comum_nao_corroboram(self) -> None:
        a = _cand("Revolução Francesa", "Bastilha", "1789-01-01", "1789-12-31")
        b = _cand("Invenção da escrita", "Baixa Mesopotâmia", "-2999-01-01", "-2999-12-31")
        self.assertLess(pontuar(a, b), 0.5)

    def test_datas_que_nao_se_cruzam_zera_a_pontuacao(self) -> None:
        """Mesmo titulo identico nao basta se as datas normalizadas nao se
        cruzam de jeito nenhum — sao candidatos claramente diferentes."""
        a = _cand("Concílio", "Roma", "1414-01-01", "1414-12-31")
        b = _cand("Concílio", "Roma", "1517-01-01", "1517-12-31")
        self.assertEqual(pontuar(a, b), 0.0)

    def test_duas_datas_a_c_de_magnitude_diferente_comparam_certo(self) -> None:
        """Bug real achado escrevendo este teste: comparar as strings ISO
        direto ('-2998-01-01' vs '-0499-01-01') dava overlap errado, porque
        '0' < '2' no segundo digito inverte a ordem cronologica entre dois
        anos a.C. de magnitude diferente. 2999 a.C. e 500 a.C. nao se cruzam
        — tem que dar False, nao True por acidente de comparacao de string."""
        ano_2999_ac = _cand("X", "Y", "-2998-01-01", "-2998-12-31")
        ano_500_ac = _cand("X", "Y", "-0499-01-01", "-0499-12-31")
        self.assertEqual(pontuar(ano_2999_ac, ano_500_ac), 0.0)

    def test_falta_de_data_normalizada_e_permissivo(self) -> None:
        """Um candidato sem data_inicio (passo 6 nao resolveu ainda) nao deve
        ser descartado so' por isso — titulo/local seguem valendo."""
        a = _cand("Quarta Cruzada", "Constantinopla", "1202-01-01", "1202-12-31")
        b = _cand("Quarta Cruzada", "Constantinopla", None, None)
        self.assertGreaterEqual(pontuar(a, b), 0.5)

    def test_sem_titulo_em_algum_lado_nunca_corrobora(self) -> None:
        a = _cand(None, "Roma", "1414-01-01", "1414-12-31")
        b = _cand("Concílio de Constança", "Roma", "1414-01-01", "1414-12-31")
        self.assertEqual(pontuar(a, b), 0.0)

    def test_candidatos_correlacionados_filtra_e_ordena(self) -> None:
        lista_a = [
            _cand("Queda de Constantinopla", "Constantinopla", "1453-01-01", "1453-12-31"),
            _cand("Invenção da escrita", "Mesopotâmia", "-2999-01-01", "-2999-12-31"),
        ]
        lista_b = [
            _cand("A queda de Constantinopla", "Constantinopla", "1453-01-01", "1453-12-31"),
            _cand("Bastilha", "Paris", "1789-01-01", "1789-12-31"),
        ]
        resultado = candidatos_correlacionados(lista_a, lista_b)
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0].candidato_a["titulo"]["valor"], "Queda de Constantinopla")
        self.assertEqual(resultado[0].candidato_b["titulo"]["valor"], "A queda de Constantinopla")


class TesteFiltroDeCitacao(unittest.TestCase):
    def test_reconhece_citacao_real_do_livro(self) -> None:
        """Os tres exemplos que realmente apareceram numa ingestao real e
        viraram data/ator errados (ver IA.md)."""
        for texto in (
            "cenas de adoração ligadas a símbolos divinos e aos zigurates (CARDOSO, 1999).",
            "administração de recursos (KEMP, 1987).",
            "o suor do rosto do camponês (DONADONI, 1990, p.15).",
        ):
            with self.subTest(texto=texto):
                self.assertEqual(len(spans_de_citacao(texto)), 1)

    def test_ano_dentro_da_citacao_e_marcado(self) -> None:
        texto = "aos zigurates (CARDOSO, 1999)."
        citacoes = spans_de_citacao(texto)
        inicio_ano = texto.index("1999")
        self.assertTrue(esta_dentro_de_citacao(inicio_ano, inicio_ano + 4, citacoes))

    def test_ano_fora_da_citacao_nao_e_marcado(self) -> None:
        texto = "Em 1453 caiu Constantinopla, muito antes de (CARDOSO, 1999)."
        citacoes = spans_de_citacao(texto)
        inicio_ano = texto.index("1453")
        self.assertFalse(esta_dentro_de_citacao(inicio_ano, inicio_ano + 4, citacoes))

    def test_filtrar_citacoes_remove_so_a_entidade_dentro_da_citacao(self) -> None:
        texto = "Em 1453 caiu Constantinopla. Ver (KEMP, 1987) para mais detalhes."
        entidades = [
            {"start": texto.index("1453"), "end": texto.index("1453") + 4, "text": "1453", "label": "ano", "score": 0.8},
            {"start": texto.index("1987"), "end": texto.index("1987") + 4, "text": "1987", "label": "ano", "score": 0.8},
        ]
        restantes = filtrar_citacoes(entidades, texto)
        self.assertEqual([e["text"] for e in restantes], ["1453"])

    def test_sem_citacao_no_texto_nao_filtra_nada(self) -> None:
        texto = "Em 1453 caiu Constantinopla."
        entidades = [{"start": 3, "end": 7, "text": "1453", "label": "ano", "score": 0.8}]
        self.assertEqual(filtrar_citacoes(entidades, texto), entidades)


class TesteResumo(unittest.TestCase):
    def _campo(self, valor: str) -> CampoExtraido:
        return CampoExtraido(
            valor=valor,
            confianca=0.8,
            proveniencia=Proveniencia(fonte_id="f1", span_inicio=0, span_fim=1, trecho="x"),
        )

    def test_resumo_usa_so_campos_ja_extraidos(self) -> None:
        c = EventoCandidato(fonte_id="f1", texto_origem="qualquer")
        c.titulo = self._campo("conquistou Constantinopla")
        c.categoria = self._campo("batalha")
        c.local_nome_epoca = self._campo("Constantinopla")
        c.atores.append(self._campo("Mehmed II"))
        c.data_inicio = "1453-01-01"
        self.assertEqual(
            gerar_resumo(c),
            "Em 1453, em Constantinopla: conquistou Constantinopla, envolvendo Mehmed II.",
        )

    def test_resumo_omite_slots_ausentes_em_vez_de_inventar(self) -> None:
        c = EventoCandidato(fonte_id="f1", texto_origem="qualquer")
        c.categoria = self._campo("construcao")
        self.assertEqual(gerar_resumo(c), "Uma construção.")

    def test_resumo_nao_maiusculiza_nome_proprio_no_meio(self) -> None:
        """str.capitalize() minusculizaria 'Waterloo' — regressao a evitar."""
        c = EventoCandidato(fonte_id="f1", texto_origem="qualquer")
        c.titulo = self._campo("Batalha de Waterloo")
        c.categoria = self._campo("batalha")
        self.assertEqual(gerar_resumo(c), "Batalha de Waterloo.")

    def test_sem_titulo_e_sem_categoria_nao_ha_o_que_templatizar(self) -> None:
        c = EventoCandidato(fonte_id="f1", texto_origem="qualquer")
        self.assertIsNone(gerar_resumo(c))

    def test_resumo_com_local_mas_sem_data_comeca_com_maiuscula(self) -> None:
        """Achado numa ingestao real (Historia Moderna, pag. 27): 'em Europa:
        RENASCIMENTO.' saia com 'e' minusculo — o ramo com prefixo (local sem
        data) nao passava pela mesma maiusculizacao do ramo sem prefixo."""
        c = EventoCandidato(fonte_id="f1", texto_origem="qualquer")
        c.titulo = self._campo("RENASCIMENTO")
        c.categoria = self._campo("politico")
        c.local_nome_epoca = self._campo("Europa")
        self.assertEqual(gerar_resumo(c), "Em Europa: RENASCIMENTO.")


@unittest.skipUnless(
    os.environ.get("COM_MODELO") == "1",
    "define COM_MODELO=1 para rodar (carrega o modelo de 1,2 GB)",
)
class TesteIntegracaoModelo(unittest.TestCase):
    def test_toda_proveniencia_extraida_aponta_pro_texto(self) -> None:
        from extracao import ExtratorGLiNER

        texto = (
            "Em 29 de maio de 1453, Mehmed II conquistou Constantinopla "
            "após um cerco."
        )
        candidatos = ExtratorGLiNER().extrair(texto, fonte_id="teste")
        self.assertTrue(candidatos, "esperava ao menos um candidato")
        for c in candidatos:
            self.assertTrue(c.proveniencia_integra())

    def test_nada_extraido_ja_nasce_aprovado(self) -> None:
        from extracao import ExtratorGLiNER

        candidatos = ExtratorGLiNER().extrair(
            "Em 1453 caiu Constantinopla.", fonte_id="teste"
        )
        for c in candidatos:
            self.assertEqual(c.status, "pendente")


if __name__ == "__main__":
    unittest.main()
