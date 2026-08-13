"""Leitura e validação de catálogos de preços do Carrinho."""

from dataclasses import dataclass
import json
import math
from pathlib import Path
import unicodedata


@dataclass(frozen=True)
class Produto:
    chave: str
    nome: str
    embalagem: str
    conteudo_embalagem: float
    preco_embalagem: float
    palavras_chave: tuple[str, ...]


@dataclass(frozen=True)
class CatalogoPrecos:
    moeda: str
    tipo: str
    descricao: str
    produtos: tuple[Produto, ...]


def _normalizar_texto(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto.strip().casefold())
    return "".join(
        letra for letra in normalizado if not unicodedata.combining(letra)
    )


def _validar_produto(dados: object, posicao: int) -> Produto:
    if not isinstance(dados, dict):
        raise ValueError(f"Produto {posicao} deve ser um objeto.")

    campos = {
        "chave",
        "nome",
        "embalagem",
        "conteudo_embalagem",
        "preco_embalagem",
        "palavras_chave",
    }
    ausentes = campos.difference(dados)
    if ausentes:
        raise ValueError(
            f"Produto {posicao} não possui: {', '.join(sorted(ausentes))}."
        )

    try:
        conteudo = float(dados["conteudo_embalagem"])
        preco = float(dados["preco_embalagem"])
    except (TypeError, ValueError) as erro:
        raise ValueError(
            f"Produto {posicao} possui quantidade ou preço inválido."
        ) from erro

    campos_texto = ("chave", "nome", "embalagem")
    if any(
        not isinstance(dados[campo], str) or not dados[campo].strip()
        for campo in campos_texto
    ):
        raise ValueError(f"Produto {posicao} possui texto obrigatório vazio.")

    palavras = dados["palavras_chave"]
    if not math.isfinite(conteudo) or not math.isfinite(preco):
        raise ValueError(f"Produto {posicao} possui quantidade ou preço inválido.")
    if conteudo <= 0 or preco < 0:
        raise ValueError(f"Produto {posicao} possui quantidade ou preço inválido.")
    if (
        not isinstance(palavras, list)
        or not palavras
        or any(not isinstance(palavra, str) or not palavra.strip() for palavra in palavras)
    ):
        raise ValueError(f"Produto {posicao} precisa de palavras-chave.")

    return Produto(
        chave=_normalizar_texto(dados["chave"]),
        nome=dados["nome"].strip(),
        embalagem=dados["embalagem"].strip(),
        conteudo_embalagem=conteudo,
        preco_embalagem=preco,
        palavras_chave=tuple(_normalizar_texto(palavra) for palavra in palavras),
    )


def carregar_catalogo(caminho: Path) -> CatalogoPrecos:
    """Carrega um catálogo JSON e falha cedo quando os dados são inválidos."""
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if not isinstance(dados, dict):
        raise ValueError("O catálogo deve ser um objeto JSON.")

    produtos_brutos = dados.get("produtos")
    if not isinstance(produtos_brutos, list) or not produtos_brutos:
        raise ValueError("O catálogo precisa conter produtos.")

    produtos = tuple(
        _validar_produto(produto, posicao)
        for posicao, produto in enumerate(produtos_brutos, start=1)
    )
    chaves = [produto.chave for produto in produtos]
    if len(chaves) != len(set(chaves)):
        raise ValueError("O catálogo contém chaves de produto repetidas.")

    moeda = str(dados.get("moeda", "")).strip().upper()
    tipo = str(dados.get("tipo", "")).strip().casefold()
    descricao = str(dados.get("descricao", "")).strip()
    if not moeda or not tipo or not descricao:
        raise ValueError("O catálogo precisa informar moeda, tipo e descrição.")

    return CatalogoPrecos(
        moeda=moeda,
        tipo=tipo,
        descricao=descricao,
        produtos=produtos,
    )


def carregar_catalogo_simulado() -> CatalogoPrecos:
    caminho = Path(__file__).resolve().parent / "dados" / "precos_simulados.json"
    return carregar_catalogo(caminho)
