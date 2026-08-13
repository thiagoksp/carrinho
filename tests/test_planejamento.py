import unittest

from pedido import PedidoEntendido, entender_pedido
from planejamento import gerar_plano


CASO_BASE = (
    "Tenho CAD$80 para alimentar 2 pessoas por 4 dias. "
    "Estamos com pouca disposição para cozinhar, já temos arroz e 7 ovos, "
    "e pelo menos uma pessoa tem intolerância à lactose."
)


class TestPlanejamento(unittest.TestCase):
    def test_gera_oito_refeicoes_dentro_do_orcamento(self) -> None:
        plano = gerar_plano(entender_pedido(CASO_BASE))

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
        plano = gerar_plano(entender_pedido(CASO_BASE))

        assert plano is not None
        uso_dos_ovos = " ".join(plano.uso_itens_casa)
        self.assertIn("7 serão usados", uso_dos_ovos)
        self.assertNotIn("Ovos", [item.nome for item in plano.compras])

    def test_nao_inclui_laticinios_no_plano(self) -> None:
        plano = gerar_plano(entender_pedido(CASO_BASE))

        assert plano is not None
        conteudo = " ".join(
            [refeicao.prato for refeicao in plano.refeicoes]
            + [item.nome for item in plano.compras]
        ).casefold()
        for laticinio in ("leite", "queijo", "manteiga", "creme"):
            self.assertNotIn(laticinio, conteudo)

    def test_adapta_dias_pessoas_e_embalagens(self) -> None:
        pedido = PedidoEntendido(
            orcamento=200,
            moeda="CAD",
            pessoas=3,
            dias=6,
            disposicao="normal",
            itens_em_casa=["arroz", "5 ovos"],
            restricoes=[],
        )
        plano = gerar_plano(pedido)

        assert plano is not None
        self.assertEqual(len(plano.refeicoes), 12)
        self.assertEqual(plano.pessoas, 3)
        self.assertEqual(plano.dias, 6)
        self.assertIn("Ovos", [item.nome for item in plano.compras])
        self.assertGreater(plano.total_estimado, 58.25)

    def test_mostra_quando_o_orcamento_nao_e_suficiente(self) -> None:
        pedido = entender_pedido(CASO_BASE.replace("CAD$80", "CAD$20"))
        plano = gerar_plano(pedido)

        assert plano is not None
        self.assertEqual(plano.total_estimado, 58.25)
        self.assertEqual(plano.margem, -38.25)

    def test_compra_arroz_e_ovos_quando_nao_estao_em_casa(self) -> None:
        pedido = PedidoEntendido(
            orcamento=100,
            moeda="CAD",
            pessoas=2,
            dias=4,
            disposicao="baixa",
            itens_em_casa=[],
            restricoes=[],
        )
        plano = gerar_plano(pedido)

        assert plano is not None
        compras = [item.nome for item in plano.compras]
        self.assertIn("Arroz", compras)
        self.assertIn("Ovos", compras)
        self.assertEqual(plano.total_estimado, 68.75)

    def test_nao_planeja_restricao_ainda_nao_suportada(self) -> None:
        pedido = PedidoEntendido(
            orcamento=100,
            moeda="CAD",
            pessoas=2,
            dias=4,
            disposicao="baixa",
            itens_em_casa=[],
            restricoes=["intolerância ao glúten"],
        )

        self.assertIsNone(gerar_plano(pedido))


if __name__ == "__main__":
    unittest.main()
