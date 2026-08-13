"""Primeiro planejamento previsível do Carrinho, sem serviços externos."""

from dataclasses import dataclass
import math
import re
import unicodedata

from catalogo import CatalogoPrecos, Produto, carregar_catalogo_simulado
from pedido import PedidoEntendido


@dataclass(frozen=True)
class Refeicao:
    dia: int
    momento: str
    prato: str


@dataclass(frozen=True)
class ItemCompra:
    nome: str
    quantidade: str
    preco_estimado: float


@dataclass(frozen=True)
class ModeloRefeicao:
    prato: str
    ingredientes_por_pessoa: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class Plano:
    refeicoes: tuple[Refeicao, ...]
    reaproveitamento: tuple[str, ...]
    compras: tuple[ItemCompra, ...]
    uso_itens_casa: tuple[str, ...]
    orcamento: float
    pessoas: int
    dias: int
    moeda: str
    tipo_precos: str
    descricao_precos: str
    localizacao: str | None = None
    loja_preferida: str | None = None
    economico: bool = False
    total_plano_normal: float | None = None

    @property
    def total_estimado(self) -> float:
        return round(sum(item.preco_estimado for item in self.compras), 2)

    @property
    def margem(self) -> float:
        return round(self.orcamento - self.total_estimado, 2)


MODELOS_REFEICOES = (
    ModeloRefeicao(
        "Frango assado, arroz e legumes",
        (
            ("frango", 0.30),
            ("arroz", 0.10),
            ("legumes", 0.15),
            ("cebolas", 0.05),
            ("oleo", 0.01),
            ("temperos", 0.01),
        ),
    ),
    ModeloRefeicao(
        "Arroz com ovos e legumes na frigideira",
        (
            ("ovos", 2.00),
            ("arroz", 0.10),
            ("legumes", 0.15),
            ("cebolas", 0.05),
            ("oleo", 0.01),
            ("temperos", 0.01),
        ),
    ),
    ModeloRefeicao(
        "Frango, arroz e legumes preparados anteriormente",
        (
            ("frango", 0.30),
            ("arroz", 0.10),
            ("legumes", 0.15),
            ("cebolas", 0.05),
            ("oleo", 0.01),
            ("temperos", 0.01),
        ),
    ),
    ModeloRefeicao(
        "Macarrão com carne moída e molho de tomate",
        (
            ("carne", 0.125),
            ("macarrao", 0.125),
            ("tomate", 0.25),
            ("cebolas", 0.05),
            ("alho", 0.02),
            ("oleo", 0.01),
            ("temperos", 0.01),
        ),
    ),
    ModeloRefeicao(
        "Macarrão com carne e molho preparado anteriormente",
        (
            ("carne", 0.125),
            ("macarrao", 0.125),
            ("tomate", 0.25),
            ("cebolas", 0.05),
            ("alho", 0.02),
            ("oleo", 0.01),
            ("temperos", 0.01),
        ),
    ),
    ModeloRefeicao(
        "Ensopado rápido de feijão e tomate com arroz",
        (
            ("feijao", 0.625),
            ("tomate", 0.25),
            ("arroz", 0.10),
            ("cebolas", 0.05),
            ("alho", 0.02),
            ("oleo", 0.01),
            ("temperos", 0.01),
        ),
    ),
    ModeloRefeicao(
        "Ensopado de feijão preparado anteriormente com arroz",
        (
            ("feijao", 0.625),
            ("tomate", 0.25),
            ("arroz", 0.10),
            ("cebolas", 0.05),
            ("alho", 0.02),
            ("oleo", 0.01),
            ("temperos", 0.01),
        ),
    ),
    ModeloRefeicao(
        "Omelete com batatas, cebola e legumes",
        (
            ("ovos", 1.50),
            ("batatas", 0.30),
            ("legumes", 0.10),
            ("cebolas", 0.05),
            ("oleo", 0.01),
            ("temperos", 0.01),
        ),
    ),
)

MODELOS_ECONOMICOS = (
    ModeloRefeicao(
        "Arroz, feijão e legumes",
        (("arroz", 0.10), ("feijao", 0.25), ("legumes", 0.10)),
    ),
    ModeloRefeicao(
        "Arroz com ovos e legumes",
        (("arroz", 0.10), ("ovos", 2.00), ("legumes", 0.10)),
    ),
    ModeloRefeicao(
        "Arroz, feijão e legumes preparados anteriormente",
        (("arroz", 0.10), ("feijao", 0.25), ("legumes", 0.10)),
    ),
    ModeloRefeicao(
        "Macarrão com feijão e molho de tomate",
        (("macarrao", 0.125), ("feijao", 0.15), ("tomate", 0.125)),
    ),
    ModeloRefeicao(
        "Macarrão com feijão e molho preparado anteriormente",
        (("macarrao", 0.125), ("feijao", 0.15), ("tomate", 0.125)),
    ),
    ModeloRefeicao(
        "Arroz, feijão e legumes",
        (("arroz", 0.10), ("feijao", 0.25), ("legumes", 0.10)),
    ),
    ModeloRefeicao(
        "Arroz, feijão e tomate",
        (("arroz", 0.10), ("feijao", 0.25), ("tomate", 0.125)),
    ),
    ModeloRefeicao(
        "Arroz com omelete simples e legumes",
        (("arroz", 0.10), ("ovos", 1.50), ("legumes", 0.10)),
    ),
)

UNIDADES_BASE = {
    "tomate": "latas",
    "feijao": "latas",
    "ovos": "unidades",
    "oleo": "litros",
    "temperos": "embalagens",
}

NUMEROS_POR_EXTENSO = {
    "um": 1.0,
    "uma": 1.0,
    "dois": 2.0,
    "duas": 2.0,
    "tres": 3.0,
    "quatro": 4.0,
    "cinco": 5.0,
    "seis": 6.0,
    "sete": 7.0,
    "oito": 8.0,
    "nove": 9.0,
    "dez": 10.0,
    "meio": 0.5,
    "meia": 0.5,
}


def _sem_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(letra for letra in normalizado if not unicodedata.combining(letra))


def _restricoes_suportadas(restricoes: list[str] | None) -> bool:
    if restricoes is None:
        return False
    return all("lactose" in _sem_acentos(restricao) for restricao in restricoes)


def _montar_refeicoes(
    dias: int, modelos: tuple[ModeloRefeicao, ...] = MODELOS_REFEICOES
) -> tuple[tuple[Refeicao, ModeloRefeicao], ...]:
    refeicoes: list[tuple[Refeicao, ModeloRefeicao]] = []
    momentos = ("Almoço", "Jantar")

    for dia in range(1, dias + 1):
        for indice_momento, momento in enumerate(momentos):
            indice = ((dia - 1) * 2 + indice_momento) % len(modelos)
            modelo = modelos[indice]
            refeicoes.append((Refeicao(dia, momento, modelo.prato), modelo))

    return tuple(refeicoes)


def _calcular_necessidades(
    refeicoes: tuple[tuple[Refeicao, ModeloRefeicao], ...], pessoas: int
) -> dict[str, float]:
    necessidades: dict[str, float] = {}
    for _, modelo in refeicoes:
        for chave, quantidade_por_pessoa in modelo.ingredientes_por_pessoa:
            necessidades[chave] = necessidades.get(chave, 0) + (
                quantidade_por_pessoa * pessoas
            )
    return necessidades


def _item_corresponde(item: str, produto: Produto) -> bool:
    item_normalizado = _sem_acentos(item)
    return any(palavra in item_normalizado for palavra in produto.palavras_chave)


def _extrair_numero(texto: str) -> float | None:
    fracao = re.search(r"\b(\d+)\s*/\s*(\d+)\b", texto)
    if fracao and int(fracao.group(2)) != 0:
        return int(fracao.group(1)) / int(fracao.group(2))

    numero = re.search(r"\b\d+(?:[.,]\d+)?\b", texto)
    if numero:
        return float(numero.group().replace(",", "."))

    for palavra, valor in NUMEROS_POR_EXTENSO.items():
        if re.search(rf"\b{palavra}\b", texto):
            return valor
    return None


def _quantidade_do_item(item: str, produto: Produto) -> float | None:
    texto = _sem_acentos(item)
    numero = _extrair_numero(texto)
    if numero is None:
        return None

    if produto.chave == "ovos":
        if "duzia" in texto:
            return numero * 12
        return numero

    if produto.chave in {"tomate", "feijao"}:
        if re.search(r"\blatas?\b", texto):
            return numero
        if re.search(r"\b(?:pacotes?|embalagens?)\b", texto):
            return numero * produto.conteudo_embalagem
        return None

    if produto.chave == "oleo":
        if re.search(r"\b(?:ml|mililitros?)\b", texto):
            return numero / 1000
        if re.search(r"\b(?:l|litros?)\b", texto):
            return numero
        if re.search(r"\b(?:frascos?|garrafas?)\b", texto):
            return numero * produto.conteudo_embalagem
        return None

    if produto.chave == "temperos":
        if re.search(r"\b(?:pacotes?|embalagens?|potes?)\b", texto):
            return numero * produto.conteudo_embalagem
        return None

    if re.search(r"\b(?:kg|quilos?|quilogramas?)\b", texto):
        return numero
    if re.search(r"\b(?:g|gramas?)\b", texto):
        return numero / 1000
    if re.search(
        r"\b(?:pacotes?|embalagens?|sacos?|unidades?)\b", texto
    ):
        return numero * produto.conteudo_embalagem
    return None


def _quantidade_disponivel(
    produto: Produto, itens_em_casa: list[str] | None
) -> float:
    correspondentes = [
        item for item in (itens_em_casa or []) if _item_corresponde(item, produto)
    ]
    if not correspondentes:
        return 0

    quantidades = [
        _quantidade_do_item(item, produto) for item in correspondentes
    ]
    if any(quantidade is None for quantidade in quantidades):
        return math.inf
    return sum(quantidade or 0 for quantidade in quantidades)


def _calcular_compras(
    necessidades: dict[str, float],
    itens_em_casa: list[str] | None,
    produtos: tuple[Produto, ...],
) -> tuple[ItemCompra, ...]:
    compras: list[ItemCompra] = []
    for produto in produtos:
        necessario = necessidades.get(produto.chave, 0)
        disponivel = _quantidade_disponivel(produto, itens_em_casa)
        falta = max(0, necessario - disponivel)
        if falta <= 0:
            continue

        embalagens = math.ceil(falta / produto.conteudo_embalagem)
        quantidade = (
            produto.embalagem
            if embalagens == 1
            else f"{embalagens} × {produto.embalagem}"
        )
        compras.append(
            ItemCompra(
                produto.nome,
                quantidade,
                round(embalagens * produto.preco_embalagem, 2),
            )
        )
    return tuple(compras)


def _validar_cobertura_catalogo(
    necessidades: dict[str, float], produtos: tuple[Produto, ...]
) -> None:
    chaves_disponiveis = {produto.chave for produto in produtos}
    chaves_ausentes = sorted(
        chave
        for chave, quantidade in necessidades.items()
        if quantidade > 0 and chave not in chaves_disponiveis
    )
    if chaves_ausentes:
        raise ValueError(
            "O catálogo não contém preços para: " + ", ".join(chaves_ausentes) + "."
        )


def _descrever_uso_da_casa(
    necessidades: dict[str, float],
    itens_em_casa: list[str] | None,
    produtos: tuple[Produto, ...],
) -> tuple[str, ...]:
    usos: list[str] = []
    for produto in produtos:
        necessario = necessidades.get(produto.chave, 0)
        disponivel = _quantidade_disponivel(produto, itens_em_casa)
        if necessario <= 0 or disponivel <= 0:
            continue

        if not math.isinf(disponivel):
            usados = min(necessario, disponivel)
            unidade = UNIDADES_BASE.get(produto.chave, "kg")
            quantidade = f"{usados:g}".replace(".", ",")
            usos.append(
                f"{produto.nome}: o plano aproveitará "
                f"{quantidade} {unidade} do estoque."
            )
        else:
            usos.append(f"{produto.nome}: será aproveitado do que já está em casa.")
    return tuple(usos)


def _criar_plano(
    pedido: PedidoEntendido,
    modelos: tuple[ModeloRefeicao, ...],
    catalogo: CatalogoPrecos,
    economico: bool = False,
    total_plano_normal: float | None = None,
) -> Plano:
    assert pedido.orcamento is not None
    assert pedido.pessoas is not None
    assert pedido.dias is not None

    refeicoes_com_modelos = _montar_refeicoes(pedido.dias, modelos)
    necessidades = _calcular_necessidades(refeicoes_com_modelos, pedido.pessoas)
    _validar_cobertura_catalogo(necessidades, catalogo.produtos)

    return Plano(
        refeicoes=tuple(refeicao for refeicao, _ in refeicoes_com_modelos),
        reaproveitamento=(
            "Prepare porções extras quando a refeição seguinte indicar "
            "comida preparada anteriormente.",
            "Cozinhe arroz para até dois dias por vez e refrigere rapidamente as sobras.",
            "Separe as porções futuras antes de servir para facilitar o reaproveitamento.",
        ),
        compras=_calcular_compras(
            necessidades, pedido.itens_em_casa, catalogo.produtos
        ),
        uso_itens_casa=_descrever_uso_da_casa(
            necessidades, pedido.itens_em_casa, catalogo.produtos
        ),
        orcamento=pedido.orcamento or 0,
        pessoas=pedido.pessoas,
        dias=pedido.dias,
        moeda=catalogo.moeda,
        tipo_precos=catalogo.tipo,
        descricao_precos=catalogo.descricao,
        localizacao=pedido.localizacao,
        loja_preferida=pedido.loja_preferida,
        economico=economico,
        total_plano_normal=total_plano_normal,
    )


def gerar_plano(
    pedido: PedidoEntendido, catalogo: CatalogoPrecos | None = None
) -> Plano | None:
    """Gera o plano normal ou uma alternativa econômica quando necessário."""
    catalogo_escolhido = catalogo or carregar_catalogo_simulado()
    if not (
        pedido.orcamento is not None
        and pedido.moeda == catalogo_escolhido.moeda
        and pedido.pessoas is not None
        and 1 <= pedido.pessoas <= 12
        and pedido.dias is not None
        and 1 <= pedido.dias <= 14
        and _restricoes_suportadas(pedido.restricoes)
    ):
        return None

    plano_normal = _criar_plano(
        pedido, MODELOS_REFEICOES, catalogo_escolhido
    )
    if plano_normal.margem >= 0:
        return plano_normal

    plano_economico = _criar_plano(
        pedido,
        MODELOS_ECONOMICOS,
        catalogo_escolhido,
        economico=True,
        total_plano_normal=plano_normal.total_estimado,
    )
    if plano_economico.total_estimado < plano_normal.total_estimado:
        return plano_economico
    return plano_normal


def gerar_plano_caso_base(pedido: PedidoEntendido) -> Plano | None:
    """Mantém o nome anterior enquanto o projeto evolui para regras adaptáveis."""
    return gerar_plano(pedido)
