from dataclasses import replace
import json
import math
from pathlib import Path
import tempfile
import unittest

from instacart import (
    criar_payload_instacart,
    salvar_payload_instacart,
    serializar_payload_instacart,
)
from pedido import PedidoEntendido
from planejamento import gerar_plano


def _plano_base(itens_em_casa: list[str] | None = None):
    pedido = PedidoEntendido(
        orcamento=100,
        moeda="CAD",
        pessoas=2,
        dias=4,
        disposicao="baixa",
        itens_em_casa=itens_em_casa if itens_em_casa is not None else [],
        restricoes=[],
        localizacao="Toronto",
        loja_preferida="No Frills",
    )
    plano = gerar_plano(pedido)
    assert plano is not None
    return plano


class TestInstacart(unittest.TestCase):
    def test_cria_payload_minimo_com_medidas_estruturadas(self) -> None:
        plano = _plano_base(["arroz", "7 ovos"])

        payload = criar_payload_instacart(plano)

        self.assertEqual(payload["link_type"], "shopping_list")
        self.assertEqual(len(payload["line_items"]), len(plano.compras))
        itens = {item["name"]: item for item in payload["line_items"]}
        self.assertEqual(
            itens["chicken thighs"]["line_item_measurements"],
            [{"quantity": 1.2, "unit": "kg"}],
        )
        self.assertEqual(
            itens["tomato sauce"]["line_item_measurements"],
            [{"quantity": 2, "unit": "can"}],
        )
        self.assertEqual(
            itens["canned beans"]["line_item_measurements"],
            [{"quantity": 3, "unit": "can"}],
        )
        self.assertEqual(
            itens["vegetable oil"]["line_item_measurements"],
            [{"quantity": 946, "unit": "ml"}],
        )

    def test_converte_ovos_em_unidades_e_arroz_em_quilos(self) -> None:
        payload = criar_payload_instacart(_plano_base([]))
        itens = {item["name"]: item for item in payload["line_items"]}

        self.assertEqual(
            itens["large eggs"]["line_item_measurements"],
            [{"quantity": 12, "unit": "each"}],
        )
        self.assertEqual(
            itens["rice"]["line_item_measurements"],
            [{"quantity": 2, "unit": "kg"}],
        )

    def test_omite_campos_depreciados_precos_loja_e_segredos(self) -> None:
        payload = criar_payload_instacart(_plano_base(["arroz", "7 ovos"]))
        serializado = json.dumps(payload, ensure_ascii=False)

        for item in payload["line_items"]:
            self.assertNotIn("quantity", item)
            self.assertNotIn("unit", item)
        for texto_proibido in (
            "preco",
            "preço",
            "orcamento",
            "orçamento",
            "CAD$",
            "Toronto",
            "No Frills",
            "Authorization",
            "api_key",
            "country_code",
        ):
            self.assertNotIn(texto_proibido, serializado)

    def test_rejeita_lista_vazia_e_medidas_invalidas(self) -> None:
        plano = _plano_base(["arroz", "7 ovos"])
        with self.assertRaisesRegex(ValueError, "Não há itens"):
            criar_payload_instacart(replace(plano, compras=()))

        item = plano.compras[0]
        casos = (
            (replace(item, quantidade_instacart=0), "maior que zero"),
            (replace(item, quantidade_instacart=math.nan), "finita"),
            (replace(item, unidade_instacart="dúzia"), "não suportada"),
            (replace(item, termo_busca_instacart=""), "termo de busca"),
        )
        for item_invalido, mensagem in casos:
            with self.subTest(mensagem=mensagem):
                plano_invalido = replace(plano, compras=(item_invalido,))
                with self.assertRaisesRegex(ValueError, mensagem):
                    criar_payload_instacart(plano_invalido)

    def test_serializa_utf8_e_salva_sem_sobrescrever(self) -> None:
        plano = _plano_base(["arroz", "7 ovos"])
        serializado = serializar_payload_instacart(plano)

        self.assertIn("Lista Carrinho — 2 pessoas por 4 dias", serializado)
        self.assertEqual(json.loads(serializado)["link_type"], "shopping_list")

        with tempfile.TemporaryDirectory() as pasta:
            primeiro = salvar_payload_instacart(plano, Path(pasta))
            segundo = salvar_payload_instacart(plano, Path(pasta))

            self.assertEqual(primeiro.name, "lista-instacart.json")
            self.assertEqual(segundo.name, "lista-instacart-2.json")
            self.assertEqual(
                json.loads(primeiro.read_text(encoding="utf-8")),
                json.loads(segundo.read_text(encoding="utf-8")),
            )


if __name__ == "__main__":
    unittest.main()
