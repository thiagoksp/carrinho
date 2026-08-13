from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from catalogo import CatalogoPrecos, carregar_catalogo, carregar_catalogo_simulado
from app import formatar_plano
from pedido import PedidoEntendido
from planejamento import gerar_plano


class TestCatalogo(unittest.TestCase):
    def test_carrega_catalogo_simulado_com_metadados(self) -> None:
        catalogo = carregar_catalogo_simulado()

        self.assertEqual(catalogo.moeda, "CAD")
        self.assertEqual(catalogo.tipo, "simulados")
        self.assertIn("não representam ofertas atuais", catalogo.descricao)
        self.assertEqual(len(catalogo.produtos), 13)
        self.assertTrue(
            all(produto.preco_embalagem >= 0 for produto in catalogo.produtos)
        )

    def test_rejeita_chaves_de_produto_repetidas(self) -> None:
        dados = {
            "moeda": "CAD",
            "tipo": "teste",
            "descricao": "Catálogo inválido de teste.",
            "produtos": [
                {
                    "chave": "arroz",
                    "nome": "Arroz",
                    "embalagem": "1 kg",
                    "conteudo_embalagem": 1,
                    "preco_embalagem": 5,
                    "palavras_chave": ["arroz"],
                },
                {
                    "chave": "arroz",
                    "nome": "Outro arroz",
                    "embalagem": "2 kg",
                    "conteudo_embalagem": 2,
                    "preco_embalagem": 8,
                    "palavras_chave": ["arroz"],
                },
            ],
        }

        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "catalogo.json"
            caminho.write_text(json.dumps(dados), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "chaves de produto repetidas"):
                carregar_catalogo(caminho)

    def test_gerador_aceita_outro_catalogo_sem_mudar_as_regras(self) -> None:
        original = carregar_catalogo_simulado()
        produtos_mais_caros = tuple(
            replace(
                produto,
                preco_embalagem=produto.preco_embalagem * 2,
            )
            for produto in original.produtos
        )
        catalogo = CatalogoPrecos(
            moeda="CAD",
            tipo="teste",
            descricao="Preços duplicados para teste.",
            produtos=produtos_mais_caros,
        )
        pedido = PedidoEntendido(
            orcamento=1000,
            moeda="CAD",
            pessoas=2,
            dias=4,
            disposicao="baixa",
            itens_em_casa=["arroz", "7 ovos"],
            restricoes=[],
        )

        plano = gerar_plano(pedido, catalogo)

        assert plano is not None
        self.assertEqual(plano.total_estimado, 116.50)
        self.assertEqual(plano.tipo_precos, "teste")
        self.assertEqual(plano.descricao_precos, "Preços duplicados para teste.")

    def test_rejeita_catalogo_sem_produto_necessario(self) -> None:
        original = carregar_catalogo_simulado()
        catalogo_incompleto = replace(
            original,
            produtos=tuple(
                produto for produto in original.produtos if produto.chave != "arroz"
            ),
        )
        pedido = PedidoEntendido(
            orcamento=1000,
            moeda="CAD",
            pessoas=2,
            dias=4,
            disposicao="baixa",
            itens_em_casa=["7 ovos"],
            restricoes=[],
        )

        with self.assertRaisesRegex(ValueError, "não contém preços para: arroz"):
            gerar_plano(pedido, catalogo_incompleto)

    def test_formata_valores_na_moeda_do_catalogo(self) -> None:
        original = carregar_catalogo_simulado()
        catalogo_usd = replace(original, moeda="USD")
        pedido = PedidoEntendido(
            orcamento=1000,
            moeda="USD",
            pessoas=2,
            dias=4,
            disposicao="baixa",
            itens_em_casa=["arroz", "7 ovos"],
            restricoes=[],
        )

        plano = gerar_plano(pedido, catalogo_usd)

        assert plano is not None
        self.assertIn("Total estimado: US$58.25", formatar_plano(plano))

    def test_rejeita_numero_nao_finito_e_palavra_vazia(self) -> None:
        casos = (
            ("conteudo_embalagem", float("nan"), "quantidade ou preço inválido"),
            ("preco_embalagem", float("inf"), "quantidade ou preço inválido"),
            ("palavras_chave", [""], "precisa de palavras-chave"),
        )
        for campo, valor, mensagem in casos:
            with self.subTest(campo=campo, valor=valor):
                dados = {
                    "moeda": "CAD",
                    "tipo": "teste",
                    "descricao": "Catálogo inválido de teste.",
                    "produtos": [
                        {
                            "chave": "arroz",
                            "nome": "Arroz",
                            "embalagem": "1 kg",
                            "conteudo_embalagem": 1,
                            "preco_embalagem": 5,
                            "palavras_chave": ["arroz"],
                            campo: valor,
                        }
                    ],
                }

                with tempfile.TemporaryDirectory() as pasta:
                    caminho = Path(pasta) / "catalogo.json"
                    caminho.write_text(json.dumps(dados), encoding="utf-8")

                    with self.assertRaisesRegex(ValueError, mensagem):
                        carregar_catalogo(caminho)


if __name__ == "__main__":
    unittest.main()
