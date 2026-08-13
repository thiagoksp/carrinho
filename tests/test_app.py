import io
import unittest
from unittest.mock import patch

from app import main


class TestTerminal(unittest.TestCase):
    def test_confirma_o_pedido_recebido(self) -> None:
        pedido = "Tenho CAD$80 para duas pessoas."

        with (
            patch("builtins.input", return_value=pedido),
            patch("sys.stdout", new_callable=io.StringIO) as saida,
        ):
            main()

        self.assertIn("Pedido recebido", saida.getvalue())
        self.assertIn(pedido, saida.getvalue())


if __name__ == "__main__":
    unittest.main()

