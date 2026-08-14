"""Cria uma prévia local da futura lista de compras da Instacart."""

import json
import math
from pathlib import Path
import unicodedata

from catalogo import UNIDADES_INSTACART
from planejamento import ItemCompra, Plano


LIMITE_ITENS_COLAR = 200


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


def _formatar_medida_para_colar(item: ItemCompra) -> str:
    quantidade = _numero_json(float(item.quantidade_instacart))
    unidade = _texto_obrigatorio(item.unidade_instacart, "uma unidade")

    if unidade == "each":
        return str(quantidade)
    if unidade == "can":
        rotulo = "can" if quantidade == 1 else "cans"
        return f"{quantidade} {rotulo}"
    if unidade == "package":
        rotulo = "package" if quantidade == 1 else "packages"
        return f"{quantidade} {rotulo}"
    if unidade in UNIDADES_INSTACART:
        return f"{quantidade} {unidade}"
    raise ValueError(f"Unidade Instacart não suportada: {unidade}.")


def _termo_seguro_para_colar(valor: str) -> str:
    nome = _texto_obrigatorio(valor, "um termo de busca")
    separadores = {",", "\r", "\n", "\u2028", "\u2029"}
    if any(
        caractere in separadores
        or unicodedata.category(caractere).startswith("C")
        for caractere in nome
    ):
        raise ValueError(
            "O termo de busca não pode conter separadores ou controles."
        )
    return nome


def criar_lista_colar_instacart(plano: Plano) -> str:
    """Cria texto local, com um produto por linha, para colagem manual."""
    if not plano.compras:
        raise ValueError("Não há itens de compra para criar a lista Instacart.")
    if len(plano.compras) > LIMITE_ITENS_COLAR:
        raise ValueError(
            f"A lista para colar aceita no máximo {LIMITE_ITENS_COLAR} itens."
        )

    linhas = []
    for item in plano.compras:
        nome = _termo_seguro_para_colar(item.termo_busca_instacart)
        medida = _formatar_medida_para_colar(item)
        linhas.append(f"{nome} ({medida})")

    lista = "\n".join(linhas)
    if len(lista.splitlines()) != len(plano.compras):
        raise ValueError("A lista para colar contém separadores inesperados.")
    return lista


def _proximo_caminho(
    diretorio: Path, nome_base: str, extensao: str
) -> Path:
    caminho = diretorio / f"{nome_base}.{extensao}"
    numero = 2
    while caminho.exists():
        caminho = diretorio / f"{nome_base}-{numero}.{extensao}"
        numero += 1
    return caminho


def salvar_payload_instacart(
    plano: Plano, diretorio: Path | None = None
) -> Path:
    """Salva uma nova prévia JSON sem substituir arquivos anteriores."""
    pasta = diretorio or Path(__file__).resolve().parent / "resultados"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = _proximo_caminho(pasta, "lista-instacart", "json")
    caminho.write_text(
        f"{serializar_payload_instacart(plano)}\n",
        encoding="utf-8",
    )
    return caminho


def salvar_lista_colar_instacart(
    plano: Plano, diretorio: Path | None = None
) -> Path:
    """Salva texto para o usuário colar manualmente na Shopping List."""
    pasta = diretorio or Path(__file__).resolve().parent / "resultados"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = _proximo_caminho(pasta, "lista-instacart-colar", "txt")
    caminho.write_text(
        f"{criar_lista_colar_instacart(plano)}\n",
        encoding="utf-8",
    )
    return caminho
