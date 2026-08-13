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
        self.assertFalse(plano.economico)

    def test_usa_exatamente_os_sete_ovos(self) -> None:
        plano = gerar_plano(entender_pedido(CASO_BASE))

        assert plano is not None
        uso_dos_ovos = " ".join(plano.uso_itens_casa)
        self.assertIn("7 unidades do estoque", uso_dos_ovos)
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

    def test_cria_alternativa_economica_quando_o_plano_normal_nao_cabe(self) -> None:
        pedido = entender_pedido(CASO_BASE.replace("CAD$80", "CAD$20"))
        plano = gerar_plano(pedido)

        assert plano is not None
        self.assertTrue(plano.economico)
        self.assertEqual(plano.total_plano_normal, 58.25)
        self.assertEqual(plano.total_estimado, 16.25)
        self.assertEqual(plano.margem, 3.75)
        self.assertNotIn(
            "Carne moída", [item.nome for item in plano.compras]
        )
        self.assertNotIn(
            "Coxas ou sobrecoxas de frango",
            [item.nome for item in plano.compras],
        )

    def test_informa_falta_quando_nem_a_alternativa_cabe(self) -> None:
        pedido = entender_pedido(CASO_BASE.replace("CAD$80", "CAD$10"))
        plano = gerar_plano(pedido)

        assert plano is not None
        self.assertTrue(plano.economico)
        self.assertEqual(plano.total_estimado, 16.25)
        self.assertEqual(plano.margem, -6.25)

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

    def test_desconta_um_quilo_de_arroz_sem_comprar_outro_saco(self) -> None:
        pedido = PedidoEntendido(
            orcamento=100,
            moeda="CAD",
            pessoas=2,
            dias=4,
            disposicao="baixa",
            itens_em_casa=["1 kg de arroz", "7 ovos"],
            restricoes=[],
        )
        plano = gerar_plano(pedido)

        assert plano is not None
        self.assertNotIn("Arroz", [item.nome for item in plano.compras])
        self.assertIn("1 kg", " ".join(plano.uso_itens_casa))

    def test_compra_arroz_quando_meio_quilo_nao_e_suficiente(self) -> None:
        pedido = PedidoEntendido(
            orcamento=100,
            moeda="CAD",
            pessoas=2,
            dias=4,
            disposicao="baixa",
            itens_em_casa=["500 g de arroz", "7 ovos"],
            restricoes=[],
        )
        plano = gerar_plano(pedido)

        assert plano is not None
        self.assertIn("Arroz", [item.nome for item in plano.compras])
        self.assertIn("0,5 kg", " ".join(plano.uso_itens_casa))

    def test_entende_meio_pacote_de_macarrao(self) -> None:
        pedido = PedidoEntendido(
            orcamento=100,
            moeda="CAD",
            pessoas=2,
            dias=2,
            disposicao="baixa",
            itens_em_casa=["arroz", "meio pacote de macarrão", "4 ovos"],
            restricoes=[],
        )
        plano = gerar_plano(pedido)

        assert plano is not None
        self.assertNotIn("Macarrão seco", [item.nome for item in plano.compras])
        self.assertIn("0,25 kg", " ".join(plano.uso_itens_casa))

    def test_soma_latas_e_meia_duzia_de_ovos(self) -> None:
        pedido = PedidoEntendido(
            orcamento=100,
            moeda="CAD",
            pessoas=2,
            dias=4,
            disposicao="baixa",
            itens_em_casa=["arroz", "2 latas de feijão", "meia dúzia de ovos"],
            restricoes=[],
        )
        plano = gerar_plano(pedido)

        assert plano is not None
        compras = {item.nome: item.quantidade for item in plano.compras}
        self.assertEqual(compras["Feijão em lata"], "1 lata")
        self.assertEqual(compras["Ovos"], "dúzia")


if __name__ == "__main__":
    unittest.main()
