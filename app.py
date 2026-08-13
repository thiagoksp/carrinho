"""Entrada inicial do Carrinho pelo terminal."""

from pedido import PedidoEntendido, entender_pedido


def _mostrar(valor: object | None) -> str:
    return str(valor) if valor is not None else "não identificado"


def mostrar_resumo(dados: PedidoEntendido) -> None:
    """Exibe somente os dados identificados, sem criar um plano ainda."""
    if dados.orcamento is None:
        orcamento = "não identificado"
    else:
        moeda = dados.moeda or ""
        valor = f"{dados.orcamento:g}"
        orcamento = f"{moeda}${valor}" if moeda == "CAD" else f"{moeda} {valor}".strip()

    itens = ", ".join(dados.itens_em_casa) or "não identificados"
    restricoes = ", ".join(dados.restricoes) or "não identificadas"

    print("\nO Carrinho entendeu:")
    print(f"- Orçamento: {orcamento}")
    print(f"- Pessoas: {_mostrar(dados.pessoas)}")
    print(f"- Dias: {_mostrar(dados.dias)}")
    print(f"- Disposição para cozinhar: {_mostrar(dados.disposicao)}")
    print(f"- Itens em casa: {itens}")
    print(f"- Restrições: {restricoes}")


def main() -> None:
    """Recebe um pedido e mostra os dados básicos identificados."""
    print("\nCARRINHO")
    print("Planejamento simples de refeições e compras.")

    pedido = input("\nConte sua situação:\n> ").strip()

    if not pedido:
        print("\nNenhum pedido foi informado.")
        return

    mostrar_resumo(entender_pedido(pedido))
    print("\nNenhum plano de refeições foi criado ainda.")


if __name__ == "__main__":
    main()
