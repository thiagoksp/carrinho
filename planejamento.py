"""Primeiro planejamento previsível do Carrinho, sem serviços externos."""

from dataclasses import dataclass

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
class Plano:
    refeicoes: tuple[Refeicao, ...]
    reaproveitamento: tuple[str, ...]
    compras: tuple[ItemCompra, ...]
    uso_itens_casa: tuple[str, ...]
    orcamento: float

    @property
    def total_estimado(self) -> float:
        return round(sum(item.preco_estimado for item in self.compras), 2)

    @property
    def margem(self) -> float:
        return round(self.orcamento - self.total_estimado, 2)


REFEICOES_CASO_BASE = (
    Refeicao(1, "Almoço", "Frango assado, arroz e legumes"),
    Refeicao(1, "Jantar", "Arroz com 4 ovos e legumes na frigideira"),
    Refeicao(2, "Almoço", "Frango, arroz e legumes reservados do dia 1"),
    Refeicao(2, "Jantar", "Macarrão com carne moída e molho de tomate"),
    Refeicao(3, "Almoço", "Macarrão com carne e molho reservado do dia 2"),
    Refeicao(3, "Jantar", "Ensopado rápido de feijão e tomate com arroz"),
    Refeicao(4, "Almoço", "Ensopado de feijão reservado do dia 3 com arroz"),
    Refeicao(4, "Jantar", "Omelete de 3 ovos com batatas, cebola e legumes"),
)

COMPRAS_CASO_BASE = (
    ItemCompra("Coxas ou sobrecoxas de frango", "1,2 kg", 13.00),
    ItemCompra("Carne moída", "500 g", 7.00),
    ItemCompra("Macarrão seco", "1 pacote de 900 g", 2.50),
    ItemCompra("Tomate em lata ou molho de tomate", "2 latas", 5.00),
    ItemCompra("Feijão em lata", "3 latas", 5.25),
    ItemCompra("Legumes congelados", "1 pacote de 1,5 kg", 6.00),
    ItemCompra("Batatas", "1 saco de 5 lb", 5.00),
    ItemCompra("Cebolas", "1 saco de 3 lb", 4.00),
    ItemCompra("Alho", "1 unidade ou pacote", 1.50),
    ItemCompra("Óleo vegetal", "1 frasco", 5.00),
    ItemCompra("Sal, pimenta e páprica", "quantidade básica", 4.00),
)


def _contem_item(itens: list[str] | None, nome: str) -> bool:
    return bool(itens and any(nome in item.casefold() for item in itens))


def _tem_restricao_lactose(restricoes: list[str] | None) -> bool:
    return bool(
        restricoes
        and any("lactose" in restricao.casefold() for restricao in restricoes)
    )


def corresponde_ao_caso_base(pedido: PedidoEntendido) -> bool:
    """Confere se o pedido pode usar com segurança o primeiro plano fixo."""
    return bool(
        pedido.orcamento is not None
        and pedido.orcamento >= 58.25
        and pedido.moeda == "CAD"
        and pedido.pessoas == 2
        and pedido.dias == 4
        and pedido.disposicao == "baixa"
        and _contem_item(pedido.itens_em_casa, "arroz")
        and _contem_item(pedido.itens_em_casa, "7 ovos")
        and _tem_restricao_lactose(pedido.restricoes)
    )


def gerar_plano_caso_base(pedido: PedidoEntendido) -> Plano | None:
    """Retorna o plano fixo somente quando os dados correspondem ao caso-base."""
    if not corresponde_ao_caso_base(pedido):
        return None

    return Plano(
        refeicoes=REFEICOES_CASO_BASE,
        reaproveitamento=(
            "No dia 1, prepare quatro porções de frango para dois almoços.",
            "No dia 2, prepare quatro porções de macarrão para o jantar e o almoço seguinte.",
            "No dia 3, prepare quatro porções de ensopado para o jantar e o almoço seguinte.",
            "Cozinhe uma quantidade maior de arroz no início e refrigere rapidamente as sobras.",
        ),
        compras=COMPRAS_CASO_BASE,
        uso_itens_casa=(
            "Arroz: acompanhamento e base de cinco refeições.",
            "7 ovos: quatro no jantar do dia 1 e três no jantar do dia 4.",
        ),
        orcamento=pedido.orcamento or 0,
    )
