import unittest

from pedido import entender_pedido
from planejamento import gerar_plano_caso_base


CASO_BASE = (
    "Tenho CAD$80 para alimentar 2 pessoas por 4 dias. "
    "Estamos com pouca disposição para cozinhar, já temos arroz e 7 ovos, "
    "e pelo menos uma pessoa tem intolerância à lactose."
)


class TestPlanejamento(unittest.TestCase):
    def test_gera_oito_refeicoes_dentro_do_orcamento(self) -> None:
        plano = gerar_plano_caso_base(entender_pedido(CASO_BASE))

        self.assertIsNotNone(plano)
        assert plano is not None
        self.assertEqual(len(plano.refeicoes), 8)
        self.assertEqual(
            [refeicao.momento for refeicao in plano.refeicoes].count("Almoço"), 4
        )
        self.assertEqual(
            [refeicao.momento for refeicao in plano.refeicoes].count("Jantar"), 4
        )
        self.assertEqual(plano.total_estimado, 58.25)
        self.assertEqual(plano.margem, 21.75)

    def test_usa_exatamente_os_sete_ovos(self) -> None:
        plano = gerar_plano_caso_base(entender_pedido(CASO_BASE))

        assert plano is not None
        uso_dos_ovos = " ".join(plano.uso_itens_casa)
        self.assertIn("quatro", uso_dos_ovos)
        self.assertIn("três", uso_dos_ovos)

    def test_nao_inclui_laticinios_no_plano(self) -> None:
        plano = gerar_plano_caso_base(entender_pedido(CASO_BASE))

        assert plano is not None
        conteudo = " ".join(
            [refeicao.prato for refeicao in plano.refeicoes]
            + [item.nome for item in plano.compras]
        ).casefold()
        for laticinio in ("leite", "queijo", "manteiga", "creme"):
            self.assertNotIn(laticinio, conteudo)

    def test_nao_aplica_o_plano_fixo_a_outro_cenario(self) -> None:
        outro_pedido = entender_pedido(
            "Tenho CAD$80 para 1 pessoa por 2 dias, muita disposição, "
            "já tenho arroz e 7 ovos e intolerância à lactose."
        )

        self.assertIsNone(gerar_plano_caso_base(outro_pedido))


if __name__ == "__main__":
    unittest.main()

