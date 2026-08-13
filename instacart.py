"""Cria uma prévia local da futura lista de compras da Instacart."""

import json
import math
from pathlib import Path

from catalogo import UNIDADES_INSTACART
from planejamento import ItemCompra, Plano


def _texto_obrigatorio(valor: str, campo: str) -> str:
    texto = valor.strip()
    if not texto:
        raise ValueError(f"O item precisa informar {campo}.")
    return texto


def _numero_json(valor: float) -> int | float:
    if not math.isfinite(valor) or valor <= 0:
        raise ValueError("A quantidade Instacart deve ser finita e maior que zero.")
    if valor.is_integer():
        return int(valor)
    return valor


def _converter_item(item: ItemCompra) -> dict[str, object]:
    unidade = _texto_obrigatorio(item.unidade_instacart, "uma unidade")
    if unidade not in UNIDADES_INSTACART:
        raise ValueError(f"Unidade Instacart não suportada: {unidade}.")

    nome = _texto_obrigatorio(item.termo_busca_instacart, "um termo de busca")
    apresentacao = _texto_obrigatorio(
        f"{item.nome}: {item.quantidade}", "um texto de apresentação"
    )
    quantidade = _numero_json(float(item.quantidade_instacart))
    return {
        "name": nome,
        "display_text": apresentacao,
        "line_item_measurements": [
            {
                "quantity": quantidade,
                "unit": unidade,
            }
        ],
    }


def criar_payload_instacart(plano: Plano) -> dict[str, object]:
    """Converte um plano sem fazer chamadas externas nem incluir preços."""
    if not plano.compras:
        raise ValueError("Não há itens de compra para criar a lista Instacart.")

    pessoas = "pessoa" if plano.pessoas == 1 else "pessoas"
    dias = "dia" if plano.dias == 1 else "dias"
    return {
        "title": (
            f"Lista Carrinho — {plano.pessoas} {pessoas} "
            f"por {plano.dias} {dias}"
        ),
        "link_type": "shopping_list",
        "line_items": [_converter_item(item) for item in plano.compras],
    }


def serializar_payload_instacart(plano: Plano) -> str:
    """Serializa a prévia com acentos preservados e números JSON válidos."""
    return json.dumps(
        criar_payload_instacart(plano),
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )


def _proximo_caminho(diretorio: Path) -> Path:
    caminho = diretorio / "lista-instacart.json"
    numero = 2
    while caminho.exists():
        caminho = diretorio / f"lista-instacart-{numero}.json"
        numero += 1
    return caminho


def salvar_payload_instacart(
    plano: Plano, diretorio: Path | None = None
) -> Path:
    """Salva uma nova prévia JSON sem substituir arquivos anteriores."""
    pasta = diretorio or Path(__file__).resolve().parent / "resultados"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = _proximo_caminho(pasta)
    caminho.write_text(
        f"{serializar_payload_instacart(plano)}\n",
        encoding="utf-8",
    )
    return caminho
