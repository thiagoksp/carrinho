"""Interpretação inicial de pedidos escritos em linguagem comum."""

from dataclasses import dataclass
import re
import unicodedata


@dataclass
class PedidoEntendido:
    """Dados que o Carrinho conseguiu encontrar no texto."""

    orcamento: float | None = None
    moeda: str | None = None
    pessoas: int | None = None
    dias: int | None = None
    disposicao: str | None = None
    itens_em_casa: list[str] | None = None
    restricoes: list[str] | None = None


NUMEROS = {
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
}

NUMERO_TEXTO = r"\d+|um|uma|dois|duas|tr[eê]s|quatro|cinco|seis|sete|oito|nove|dez"


def _sem_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(letra for letra in normalizado if not unicodedata.combining(letra))


def _converter_numero(valor: str) -> int:
    if valor.isdigit():
        return int(valor)
    return NUMEROS[_sem_acentos(valor)]


def _encontrar_orcamento(texto: str) -> tuple[float | None, str | None]:
    resultado = re.search(
        r"(?P<moeda>CAD|BRL|USD|R\$|US\$|\$)\s*\$?\s*"
        r"(?P<valor>\d+(?:[.,]\d{1,2})?)",
        texto,
        re.IGNORECASE,
    )
    if not resultado:
        return None, None

    moeda_original = resultado.group("moeda").upper()
    moedas = {"R$": "BRL", "US$": "USD"}
    moeda = moedas.get(moeda_original, moeda_original)
    valor = float(resultado.group("valor").replace(",", "."))
    return valor, moeda


def _encontrar_quantidade(texto: str, unidade: str) -> int | None:
    resultado = re.search(
        rf"\b(?P<numero>{NUMERO_TEXTO})\s+{unidade}",
        texto,
        re.IGNORECASE,
    )
    if not resultado:
        return None
    return _converter_numero(resultado.group("numero"))


def _encontrar_disposicao(texto: str) -> str | None:
    texto_normalizado = _sem_acentos(texto)

    baixa = (
        "pouca disposicao",
        "baixa disposicao",
        "sem disposicao",
        "pouca energia",
        "sem energia",
        "nao quero cozinhar",
    )
    alta = ("muita disposicao", "alta disposicao", "muita energia")

    if any(expressao in texto_normalizado for expressao in baixa):
        return "baixa"
    if any(expressao in texto_normalizado for expressao in alta):
        return "alta"
    if "disposicao normal" in texto_normalizado:
        return "normal"
    return None


def _encontrar_itens(texto: str) -> list[str] | None:
    texto_normalizado = _sem_acentos(texto)
    sem_itens = (
        "nao tenho nada em casa",
        "nao temos nada em casa",
        "nenhum item em casa",
    )
    if any(expressao in texto_normalizado for expressao in sem_itens):
        return []

    resultado = re.search(
        r"(?:j[aá]\s+(?:tenho|temos)|(?:tenho|temos)\s+em\s+casa)\s+"
        r"(?P<itens>.+?)"
        r"(?=,\s*e\s+(?:pelo\s+menos|algu[eé]m|uma?\s+pessoa)|[.;]|$)",
        texto,
        re.IGNORECASE,
    )
    if not resultado:
        return None

    itens = re.split(r"\s*,\s*|\s+e\s+", resultado.group("itens"))
    return [item.strip().casefold() for item in itens if item.strip()]


def _encontrar_restricoes(texto: str) -> list[str] | None:
    texto_normalizado = _sem_acentos(texto)

    sem_restricoes = (
        "sem restricao",
        "sem restricoes",
        "nenhuma restricao",
        "nenhuma restricao alimentar",
    )
    if any(expressao in texto_normalizado for expressao in sem_restricoes):
        return []

    if "lactose" in texto_normalizado:
        return ["intolerância à lactose"]

    return None


def entender_pedido(texto: str) -> PedidoEntendido:
    """Extrai os dados básicos que estiverem explícitos no pedido."""
    orcamento, moeda = _encontrar_orcamento(texto)

    return PedidoEntendido(
        orcamento=orcamento,
        moeda=moeda,
        pessoas=_encontrar_quantidade(texto, r"pessoas?"),
        dias=_encontrar_quantidade(texto, r"dias?"),
        disposicao=_encontrar_disposicao(texto),
        itens_em_casa=_encontrar_itens(texto),
        restricoes=_encontrar_restricoes(texto),
    )
