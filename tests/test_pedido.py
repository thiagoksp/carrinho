import unittest

from pedido import entender_pedido


CASO_BASE = (
    "Tenho CAD$80 para alimentar 2 pessoas por 4 dias. "
    "Estamos com pouca disposição para cozinhar, já temos arroz e 7 ovos, "
    "e pelo menos uma pessoa tem intolerância à lactose. "
    "Precisamos de almoço e jantar. Estou em Toronto. "
    "Estou sem preferência de loja."
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
        self.assertEqual(pedido.localizacao, "Toronto")
        self.assertEqual(pedido.loja_preferida, "qualquer loja")

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
        self.assertIsNone(pedido.itens_em_casa)
        self.assertIsNone(pedido.restricoes)
        self.assertIsNone(pedido.localizacao)
        self.assertIsNone(pedido.loja_preferida)

    def test_identifica_regiao_e_loja_especifica(self) -> None:
        pedido = entender_pedido("Moro em North York e prefiro a loja No Frills.")

        self.assertEqual(pedido.localizacao, "North York")
        self.assertEqual(pedido.loja_preferida, "No Frills")

    def test_separa_estoque_localizacao_e_loja(self) -> None:
        pedido = entender_pedido(
            "Já tenho arroz e 7 ovos; moro em Toronto, ON; "
            "prefiro a loja No Frills."
        )

        self.assertEqual(pedido.itens_em_casa, ["arroz", "7 ovos"])
        self.assertEqual(pedido.localizacao, "Toronto, ON")
        self.assertEqual(pedido.loja_preferida, "No Frills")

    def test_nao_confunde_momento_da_compra_com_loja(self) -> None:
        pedido = entender_pedido(
            "Tenho orçamento em CAD e quero comprar no fim de semana."
        )

        self.assertIsNone(pedido.localizacao)
        self.assertIsNone(pedido.loja_preferida)

    def test_nao_confunde_preferencia_de_cozinhar_com_loja(self) -> None:
        pedido = entender_pedido("Tenho pouca energia e prefiro não cozinhar.")

        self.assertIsNone(pedido.loja_preferida)

    def test_separa_campos_sem_virgulas(self) -> None:
        pedido = entender_pedido(
            "Já tenho arroz e 7 ovos e moro em Toronto "
            "e prefiro a loja No Frills."
        )

        self.assertEqual(pedido.itens_em_casa, ["arroz", "7 ovos"])
        self.assertEqual(pedido.localizacao, "Toronto")
        self.assertEqual(pedido.loja_preferida, "No Frills")

    def test_entende_o_caso_documentado_sem_contaminar_localizacao(self) -> None:
        pedido = entender_pedido(
            "Estou em Toronto e não tenho preferência de loja."
        )

        self.assertEqual(pedido.localizacao, "Toronto")
        self.assertEqual(pedido.loja_preferida, "qualquer loja")

    def test_nao_trata_estou_em_casa_como_localizacao(self) -> None:
        pedido = entender_pedido("Estou em casa, sem energia para cozinhar.")

        self.assertIsNone(pedido.localizacao)

    def test_distingue_nenhum_item_de_informacao_ausente(self) -> None:
        pedido = entender_pedido(
            "Não tenho nada em casa e não possuo nenhuma restrição alimentar."
        )

        self.assertEqual(pedido.itens_em_casa, [])
        self.assertEqual(pedido.restricoes, [])

    def test_preserva_as_quantidades_informadas_no_estoque(self) -> None:
        pedido = entender_pedido(
            "Já tenho 1 kg de arroz, meio pacote de macarrão e 7 ovos."
        )

        self.assertEqual(
            pedido.itens_em_casa,
            ["1 kg de arroz", "meio pacote de macarrão", "7 ovos"],
        )


if __name__ == "__main__":
    unittest.main()
