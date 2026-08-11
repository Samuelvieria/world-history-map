"""Testes das invariantes do passo 1.

Os testes que importam aqui nao sao de acuracia (isso e' `spike_passo1.py`,
que mede contra gabarito) e sim das regras que, se quebrarem em silencio,
corrompem o banco: proveniencia que nao aponta pro texto, campo criado sem
span, e geocoding chutando coordenada.

Rodam sem carregar o modelo — sao rapidos de proposito, para poderem rodar
sempre. O teste de ponta a ponta (que baixa 1,2 GB) fica separado atras da
variavel de ambiente COM_MODELO=1.

Uso:
    ./.venv/bin/python -m unittest testes -v
    COM_MODELO=1 ./.venv/bin/python -m unittest testes -v
"""

from __future__ import annotations

import os
import unittest

from extracao.citacoes import esta_dentro_de_citacao, filtrar_citacoes, spans_de_citacao
from extracao.datas import ano_legivel, normalizar as normalizar_data, preencher_datas
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


class TesteGeocodingStub(unittest.TestCase):
    def test_stub_nao_inventa_coordenada(self) -> None:
        """Um lat/lng chutado seria pior que nenhum: cravaria ponto errado."""
        self.assertIsNone(resolver_geocoding("Constantinopla"))


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
