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

from extracao.geocoding import resolver as resolver_geocoding
from extracao.modelo import CampoExtraido, EventoCandidato, Proveniencia
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
