import unittest

from pedido import entender_pedido


CASO_BASE = (
    "Tenho CAD$80 para alimentar 2 pessoas por 4 dias. "
    "Estamos com pouca disposição para cozinhar, já temos arroz e 7 ovos, "
    "e pelo menos uma pessoa tem intolerância à lactose. "
    "Precisamos de almoço e jantar."
)


class TestEntenderPedido(unittest.TestCase):
    def test_identifica_os_dados_do_caso_base(self) -> None:
        pedido = entender_pedido(CASO_BASE)

        self.assertEqual(pedido.orcamento, 80)
        self.assertEqual(pedido.moeda, "CAD")
        self.assertEqual(pedido.pessoas, 2)
        self.assertEqual(pedido.dias, 4)
        self.assertEqual(pedido.disposicao, "baixa")
        self.assertEqual(pedido.itens_em_casa, ["arroz", "7 ovos"])
        self.assertEqual(pedido.restricoes, ["intolerância à lactose"])

    def test_aceita_quantidades_por_extenso(self) -> None:
        pedido = entender_pedido("Tenho CAD$50 para duas pessoas por três dias.")

        self.assertEqual(pedido.pessoas, 2)
        self.assertEqual(pedido.dias, 3)

    def test_deixa_ausentes_os_dados_nao_informados(self) -> None:
        pedido = entender_pedido("Preciso organizar minha alimentação.")

        self.assertIsNone(pedido.orcamento)
        self.assertIsNone(pedido.pessoas)
        self.assertIsNone(pedido.dias)
        self.assertIsNone(pedido.disposicao)
        self.assertEqual(pedido.itens_em_casa, [])
        self.assertEqual(pedido.restricoes, [])


if __name__ == "__main__":
    unittest.main()

