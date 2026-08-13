import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import formatar_plano, main, revisar_dados, salvar_plano
from pedido import PedidoEntendido
from planejamento import gerar_plano


class TestTerminal(unittest.TestCase):
    def test_mostra_os_dados_identificados(self) -> None:
        pedido = (
            "Tenho CAD$80 para alimentar 2 pessoas por 4 dias. "
            "Estamos com pouca disposição para cozinhar, já temos arroz e 7 ovos, "
            "e pelo menos uma pessoa tem intolerância à lactose. "
            "Estou em Toronto e prefiro a loja Walmart."
        )

        with (
            patch("builtins.input", side_effect=[pedido, "s", "n"]),
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
        self.assertIn("Localização das compras: Toronto", saida.getvalue())
        self.assertIn("Loja preferida: Walmart", saida.getvalue())
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
            "Toronto",
            "qualquer",
            "s",
            "n",
        ]

        with (
            patch("builtins.input", side_effect=respostas) as entrada,
            patch("sys.stdout", new_callable=io.StringIO) as saida,
        ):
            main()

        self.assertEqual(entrada.call_count, 11)
        self.assertIn("Orçamento: CAD$80", saida.getvalue())
        self.assertIn("Pessoas: 2", saida.getvalue())
        self.assertIn("Dias: 4", saida.getvalue())
        self.assertIn("Disposição para cozinhar: baixa", saida.getvalue())
        self.assertIn("Itens em casa: arroz, 7 ovos", saida.getvalue())
        self.assertIn("Restrições: intolerância à lactose", saida.getvalue())
        self.assertIn("Localização das compras: Toronto", saida.getvalue())
        self.assertIn("Loja preferida: qualquer loja", saida.getvalue())
        self.assertIn("PLANO DE REFEIÇÕES", saida.getvalue())

    def test_corrige_orcamento_e_dias_sem_reiniciar(self) -> None:
        dados = PedidoEntendido(
            orcamento=80,
            moeda="CAD",
            pessoas=2,
            dias=4,
            disposicao="baixa",
            itens_em_casa=["arroz", "7 ovos"],
            restricoes=["intolerância à lactose"],
        )

        with (
            patch(
                "builtins.input",
                side_effect=["n", "1", "60", "n", "3", "5", "s"],
            ),
            patch("sys.stdout", new_callable=io.StringIO) as saida,
        ):
            resultado = revisar_dados(dados)

        self.assertEqual(resultado.orcamento, 60)
        self.assertEqual(resultado.dias, 5)
        self.assertIn("Orçamento: CAD$60", saida.getvalue())
        self.assertIn("Dias: 5", saida.getvalue())

    def test_corrige_estoque_e_restricoes_sem_reiniciar(self) -> None:
        dados = PedidoEntendido(
            orcamento=80,
            moeda="CAD",
            pessoas=2,
            dias=4,
            disposicao="baixa",
            itens_em_casa=["arroz"],
            restricoes=["intolerância à lactose"],
        )

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "n",
                    "5",
                    "1 kg de arroz, meia dúzia de ovos",
                    "n",
                    "6",
                    "nenhuma",
                    "s",
                ],
            ),
            patch("sys.stdout", new_callable=io.StringIO),
        ):
            resultado = revisar_dados(dados)

        self.assertEqual(
            resultado.itens_em_casa,
            ["1 kg de arroz", "meia dúzia de ovos"],
        )
        self.assertEqual(resultado.restricoes, [])

    def test_corrige_localizacao_e_loja_sem_reiniciar(self) -> None:
        dados = PedidoEntendido(
            orcamento=80,
            moeda="CAD",
            pessoas=2,
            dias=4,
            disposicao="baixa",
            itens_em_casa=["arroz", "7 ovos"],
            restricoes=[],
            localizacao="Toronto",
            loja_preferida="qualquer loja",
        )

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "n",
                    "7",
                    "North York",
                    "n",
                    "8",
                    "No Frills",
                    "s",
                ],
            ),
            patch("sys.stdout", new_callable=io.StringIO),
        ):
            resultado = revisar_dados(dados)

        self.assertEqual(resultado.localizacao, "North York")
        self.assertEqual(resultado.loja_preferida, "No Frills")

    def test_formata_todas_as_secoes_do_plano(self) -> None:
        dados = PedidoEntendido(
            orcamento=80,
            moeda="CAD",
            pessoas=2,
            dias=4,
            disposicao="baixa",
            itens_em_casa=["arroz", "7 ovos"],
            restricoes=["intolerância à lactose"],
            localizacao="Toronto",
            loja_preferida="No Frills",
        )
        plano = gerar_plano(dados)

        assert plano is not None
        conteudo = formatar_plano(plano)
        self.assertIn("PLANO DE REFEIÇÕES", conteudo)
        self.assertIn("COMO REDUZIR O TRABALHO", conteudo)
        self.assertIn("LISTA DE COMPRAS", conteudo)
        self.assertIn("Total estimado: CAD$58.25", conteudo)
        self.assertIn("Fonte dos preços:", conteudo)
        self.assertIn("Localização das compras: Toronto", conteudo)
        self.assertIn("Loja preferida: No Frills", conteudo)
        self.assertIn("ainda não alteram os preços simulados", conteudo)
        self.assertIn("ITENS QUE JÁ ESTÃO EM CASA", conteudo)

    def test_salva_novos_arquivos_sem_sobrescrever(self) -> None:
        dados = PedidoEntendido(
            orcamento=80,
            moeda="CAD",
            pessoas=2,
            dias=4,
            disposicao="baixa",
            itens_em_casa=["arroz", "7 ovos"],
            restricoes=["intolerância à lactose"],
            localizacao="Toronto",
            loja_preferida="No Frills",
        )
        plano = gerar_plano(dados)

        assert plano is not None
        with tempfile.TemporaryDirectory() as pasta:
            primeiro = salvar_plano(plano, Path(pasta))
            segundo = salvar_plano(plano, Path(pasta))

            self.assertEqual(primeiro.name, "plano-carrinho.txt")
            self.assertEqual(segundo.name, "plano-carrinho-2.txt")
            self.assertEqual(
                primeiro.read_text(encoding="utf-8"),
                segundo.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "LISTA DE COMPRAS",
                primeiro.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "Localização das compras: Toronto",
                primeiro.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "Loja preferida: No Frills",
                primeiro.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
