"""Entrada inicial do Carrinho pelo terminal."""


def main() -> None:
    """Recebe um pedido em texto sem processá-lo ainda."""
    print("\nCARRINHO")
    print("Planejamento simples de refeições e compras.")

    pedido = input("\nConte sua situação:\n> ").strip()

    if not pedido:
        print("\nNenhum pedido foi informado.")
        return

    print("\nPedido recebido:")
    print(pedido)
    print("\nO planejamento será adicionado na próxima etapa.")


if __name__ == "__main__":
    main()

