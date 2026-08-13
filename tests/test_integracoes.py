import json
from pathlib import Path
import tempfile
import unittest

from integracoes import carregar_integracao_piloto, carregar_integracoes


def _registro_valido() -> dict[str, object]:
    return {
        "id": "no-frills-toronto",
        "loja_piloto": "No Frills",
        "localizacao_piloto": "Toronto, ON",
        "pais": "CA",
        "moeda": "CAD",
        "fonte_precos": "simulada",
        "status_precos": "disponivel",
        "catalogo_local": "precos_simulados.json",
        "entrega_lista": "instacart",
        "status_entrega": "planejada",
        "permite_fixar_loja": False,
        "precos_reais_disponiveis": False,
        "aviso": "Ainda não há preços reais.",
    }


def _catalogo_valido(
    moeda: str = "CAD", tipo: str = "simulados"
) -> dict[str, object]:
    return {
        "moeda": moeda,
        "tipo": tipo,
        "descricao": "Catálogo temporário para testes.",
        "produtos": [
            {
                "chave": "arroz",
                "nome": "Arroz",
                "embalagem": "1 kg",
                "conteudo_embalagem": 1,
                "preco_embalagem": 5,
                "palavras_chave": ["arroz"],
            }
        ],
    }


def _salvar_temporario(
    registros: list[dict[str, object]],
    pasta: str,
    catalogo: dict[str, object] | None = None,
) -> Path:
    caminho_catalogo = Path(pasta) / "precos_simulados.json"
    caminho_catalogo.write_text(
        json.dumps(catalogo or _catalogo_valido()),
        encoding="utf-8",
    )
    caminho = Path(pasta) / "integracoes.json"
    caminho.write_text(
        json.dumps({"integracoes": registros}),
        encoding="utf-8",
    )
    return caminho


class TestIntegracoes(unittest.TestCase):
    def test_carrega_no_frills_como_piloto_planejado(self) -> None:
        piloto = carregar_integracao_piloto()

        self.assertEqual(piloto.loja_piloto, "No Frills")
        self.assertEqual(piloto.localizacao_piloto, "Toronto, ON")
        self.assertEqual(piloto.entrega_lista, "instacart")
        self.assertEqual(piloto.status_precos, "disponivel")
        self.assertEqual(piloto.status_entrega, "planejada")
        self.assertFalse(piloto.permite_fixar_loja)
        self.assertEqual(piloto.catalogo_local.name, "precos_simulados.json")
        self.assertFalse(piloto.pode_entregar_lista)
        self.assertFalse(piloto.pode_usar_precos_reais)

    def test_rejeita_ids_repetidos(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            caminho = _salvar_temporario(
                [_registro_valido(), _registro_valido()], pasta
            )

            with self.assertRaisesRegex(ValueError, "ids de integração repetidos"):
                carregar_integracoes(caminho)

    def test_rejeita_valores_de_controle_invalidos(self) -> None:
        casos = (
            ("fonte_precos", "site-escondido", "fonte de preços inválida"),
            ("entrega_lista", "scraping", "entrega de lista inválida"),
            ("status_precos", "pronta", "status de preços inválido"),
            ("status_entrega", "pronta", "status de entrega inválido"),
        )
        for campo, valor, mensagem in casos:
            with self.subTest(campo=campo):
                registro = _registro_valido()
                registro[campo] = valor
                with tempfile.TemporaryDirectory() as pasta:
                    caminho = _salvar_temporario([registro], pasta)
                    with self.assertRaisesRegex(ValueError, mensagem):
                        carregar_integracoes(caminho)

    def test_nao_aceita_preco_real_sem_fonte_licenciada(self) -> None:
        registro = _registro_valido()
        registro["precos_reais_disponiveis"] = True

        with tempfile.TemporaryDirectory() as pasta:
            caminho = _salvar_temporario([registro], pasta)

            with self.assertRaisesRegex(ValueError, "fonte licenciada"):
                carregar_integracoes(caminho)

    def test_nao_aceita_preco_real_com_fonte_ainda_planejada(self) -> None:
        registro = _registro_valido()
        registro["fonte_precos"] = "licenciada"
        registro["status_precos"] = "planejada"
        registro["precos_reais_disponiveis"] = True

        with tempfile.TemporaryDirectory() as pasta:
            caminho = _salvar_temporario([registro], pasta)

            with self.assertRaisesRegex(ValueError, "fonte disponível"):
                carregar_integracoes(caminho)

    def test_nao_aceita_catalogo_simulado_como_fonte_licenciada(self) -> None:
        registro = _registro_valido()
        registro["fonte_precos"] = "licenciada"
        registro["status_precos"] = "disponivel"
        registro["precos_reais_disponiveis"] = True

        with tempfile.TemporaryDirectory() as pasta:
            caminho = _salvar_temporario([registro], pasta)

            with self.assertRaisesRegex(ValueError, "rotulado como licenciado"):
                carregar_integracoes(caminho)

    def test_instacart_nao_pode_prometir_loja_fixa(self) -> None:
        registro = _registro_valido()
        registro["permite_fixar_loja"] = True

        with tempfile.TemporaryDirectory() as pasta:
            caminho = _salvar_temporario([registro], pasta)

            with self.assertRaisesRegex(ValueError, "não pode garantir"):
                carregar_integracoes(caminho)

    def test_valida_a_fronteira_do_catalogo_local(self) -> None:
        casos = (
            ("ausente.json", _catalogo_valido(), "catálogo inexistente"),
            ("../precos.json", _catalogo_valido(), "catálogo fora de dados"),
            (
                "precos_simulados.json",
                _catalogo_valido(tipo="reais"),
                "rotulado como simulado",
            ),
            (
                "precos_simulados.json",
                _catalogo_valido(moeda="USD"),
                "catálogo em outra moeda",
            ),
        )
        for caminho_catalogo, catalogo, mensagem in casos:
            with self.subTest(caminho=caminho_catalogo, mensagem=mensagem):
                registro = _registro_valido()
                registro["catalogo_local"] = caminho_catalogo
                with tempfile.TemporaryDirectory() as pasta:
                    caminho = _salvar_temporario([registro], pasta, catalogo)
                    with self.assertRaisesRegex(ValueError, mensagem):
                        carregar_integracoes(caminho)


if __name__ == "__main__":
    unittest.main()
