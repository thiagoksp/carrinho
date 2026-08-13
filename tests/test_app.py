import io
import unittest
from unittest.mock import patch

from app import main


class TestTerminal(unittest.TestCase):
    def test_mostra_os_dados_identificados(self) -> None:
        pedido = (
            "Tenho CAD$80 para alimentar 2 pessoas por 4 dias. "
            "Estamos com pouca disposição para cozinhar, já temos arroz e 7 ovos, "
            "e pelo menos uma pessoa tem intolerância à lactose."
        )

        with (
            patch("builtins.input", side_effect=[pedido, "s"]),
            patch("sys.stdout", new_callable=io.StringIO) as saida,
        ):
            main()

        self.assertIn("O Carrinho entendeu", saida.getvalue())
        self.assertIn("Orçamento: CAD$80", saida.getvalue())
        self.assertIn("Pessoas: 2", saida.getvalue())
        self.assertIn("Dias: 4", saida.getvalue())
        self.assertIn("Disposição para cozinhar: baixa", saida.getvalue())
        self.assertIn("Itens em casa: arroz, 7 ovos", saida.getvalue())
        self.assertIn("Restrições: intolerância à lactose", saida.getvalue())
        self.assertIn("Dados confirmados", saida.getvalue())
        self.assertIn("PLANO DE REFEIÇÕES", saida.getvalue())
        self.assertIn("Total estimado: CAD$58.25", saida.getvalue())
        self.assertIn("Margem do orçamento: CAD$21.75", saida.getvalue())

    def test_pergunta_somente_os_dados_ausentes(self) -> None:
        respostas = [
            "Preciso organizar minha alimentação.",
            "80",
            "2",
            "4",
            "1",
            "arroz, 7 ovos",
            "intolerância à lactose",
            "s",
        ]

        with (
            patch("builtins.input", side_effect=respostas) as entrada,
            patch("sys.stdout", new_callable=io.StringIO) as saida,
        ):
            main()

        self.assertEqual(entrada.call_count, 8)
        self.assertIn("Orçamento: CAD$80", saida.getvalue())
        self.assertIn("Pessoas: 2", saida.getvalue())
        self.assertIn("Dias: 4", saida.getvalue())
        self.assertIn("Disposição para cozinhar: baixa", saida.getvalue())
        self.assertIn("Itens em casa: arroz, 7 ovos", saida.getvalue())
        self.assertIn("Restrições: intolerância à lactose", saida.getvalue())
        self.assertIn("PLANO DE REFEIÇÕES", saida.getvalue())


if __name__ == "__main__":
    unittest.main()
