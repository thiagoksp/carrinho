"""Primeiro planejamento previsível do Carrinho, sem serviços externos."""

from dataclasses import dataclass
import math
import re
import unicodedata

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
class Produto:
    chave: str
    nome: str
    embalagem: str
    conteudo_embalagem: float
    preco_embalagem: float
    palavras_chave: tuple[str, ...]


@dataclass(frozen=True)
class Plano:
    refeicoes: tuple[Refeicao, ...]
    reaproveitamento: tuple[str, ...]
    compras: tuple[ItemCompra, ...]
    uso_itens_casa: tuple[str, ...]
    orcamento: float
    pessoas: int
    dias: int

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

PRODUTOS = (
    Produto("frango", "Coxas ou sobrecoxas de frango", "1,2 kg", 1.20, 13.00, ("frango",)),
    Produto("carne", "Carne moída", "500 g", 0.50, 7.00, ("carne moida",)),
    Produto("macarrao", "Macarrão seco", "pacote de 900 g", 0.90, 2.50, ("macarrao",)),
    Produto(
        "tomate",
        "Tomate em lata ou molho de tomate",
        "1 lata",
        1.00,
        2.50,
        ("tomate", "molho de tomate"),
    ),
    Produto("feijao", "Feijão em lata", "1 lata", 1.00, 1.75, ("feijao",)),
    Produto("legumes", "Legumes congelados", "pacote de 1,5 kg", 1.50, 6.00, ("legumes",)),
    Produto("batatas", "Batatas", "saco de 5 lb", 2.27, 5.00, ("batata", "batatas")),
    Produto("cebolas", "Cebolas", "saco de 3 lb", 1.36, 4.00, ("cebola", "cebolas")),
    Produto("alho", "Alho", "unidade ou pacote", 0.20, 1.50, ("alho",)),
    Produto("oleo", "Óleo vegetal", "1 frasco", 0.946, 5.00, ("oleo", "azeite")),
    Produto(
        "temperos",
        "Sal, pimenta e páprica",
        "quantidade básica",
        1.00,
        4.00,
        ("sal", "pimenta", "paprica", "temperos"),
    ),
    Produto("arroz", "Arroz", "saco de 2 kg", 2.00, 6.00, ("arroz",)),
    Produto("ovos", "Ovos", "dúzia", 12.00, 4.50, ("ovo", "ovos")),
)


def _sem_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(letra for letra in normalizado if not unicodedata.combining(letra))


def _restricoes_suportadas(restricoes: list[str] | None) -> bool:
    if restricoes is None:
        return False
    return all("lactose" in _sem_acentos(restricao) for restricao in restricoes)


def _montar_refeicoes(dias: int) -> tuple[tuple[Refeicao, ModeloRefeicao], ...]:
    refeicoes: list[tuple[Refeicao, ModeloRefeicao]] = []
    momentos = ("Almoço", "Jantar")

    for dia in range(1, dias + 1):
        for indice_momento, momento in enumerate(momentos):
            indice = ((dia - 1) * 2 + indice_momento) % len(MODELOS_REFEICOES)
            modelo = MODELOS_REFEICOES[indice]
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


def _quantidade_disponivel(
    produto: Produto, itens_em_casa: list[str] | None
) -> float:
    correspondentes = [
        item for item in (itens_em_casa or []) if _item_corresponde(item, produto)
    ]
    if not correspondentes:
        return 0

    if produto.chave == "ovos":
        quantidade = 0
        for item in correspondentes:
            resultado = re.search(r"\d+", item)
            if resultado:
                quantidade += int(resultado.group())
            elif "duzia" in _sem_acentos(item):
                quantidade += 12
        return float(quantidade)

    return math.inf


def _calcular_compras(
    necessidades: dict[str, float], itens_em_casa: list[str] | None
) -> tuple[ItemCompra, ...]:
    compras: list[ItemCompra] = []
    for produto in PRODUTOS:
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


def _descrever_uso_da_casa(
    necessidades: dict[str, float], itens_em_casa: list[str] | None
) -> tuple[str, ...]:
    usos: list[str] = []
    for produto in PRODUTOS:
        necessario = necessidades.get(produto.chave, 0)
        disponivel = _quantidade_disponivel(produto, itens_em_casa)
        if necessario <= 0 or disponivel <= 0:
            continue

        if produto.chave == "ovos" and not math.isinf(disponivel):
            usados = min(math.ceil(necessario), int(disponivel))
            usos.append(f"Ovos disponíveis: {usados} serão usados no plano.")
        else:
            usos.append(f"{produto.nome}: será aproveitado do que já está em casa.")
    return tuple(usos)


def gerar_plano(pedido: PedidoEntendido) -> Plano | None:
    """Gera um plano adaptado dentro dos limites seguros desta primeira regra."""
    if not (
        pedido.orcamento is not None
        and pedido.moeda == "CAD"
        and pedido.pessoas is not None
        and 1 <= pedido.pessoas <= 12
        and pedido.dias is not None
        and 1 <= pedido.dias <= 14
        and _restricoes_suportadas(pedido.restricoes)
    ):
        return None

    refeicoes_com_modelos = _montar_refeicoes(pedido.dias)
    necessidades = _calcular_necessidades(refeicoes_com_modelos, pedido.pessoas)

    return Plano(
        refeicoes=tuple(refeicao for refeicao, _ in refeicoes_com_modelos),
        reaproveitamento=(
            "Prepare porções extras quando a refeição seguinte indicar "
            "comida preparada anteriormente.",
            "Cozinhe arroz para até dois dias por vez e refrigere rapidamente as sobras.",
            "Separe as porções futuras antes de servir para facilitar o reaproveitamento.",
        ),
        compras=_calcular_compras(necessidades, pedido.itens_em_casa),
        uso_itens_casa=_descrever_uso_da_casa(
            necessidades, pedido.itens_em_casa
        ),
        orcamento=pedido.orcamento or 0,
        pessoas=pedido.pessoas,
        dias=pedido.dias,
    )


def gerar_plano_caso_base(pedido: PedidoEntendido) -> Plano | None:
    """Mantém o nome anterior enquanto o projeto evolui para regras adaptáveis."""
    return gerar_plano(pedido)
