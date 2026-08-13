"""Entrada inicial do Carrinho pelo terminal."""

import re

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

    if dados.itens_em_casa is None:
        itens = "não identificados"
    else:
        itens = ", ".join(dados.itens_em_casa) or "nenhum"

    if dados.restricoes is None:
        restricoes = "não identificadas"
    else:
        restricoes = ", ".join(dados.restricoes) or "nenhuma"

    print("\nO Carrinho entendeu:")
    print(f"- Orçamento: {orcamento}")
    print(f"- Pessoas: {_mostrar(dados.pessoas)}")
    print(f"- Dias: {_mostrar(dados.dias)}")
    print(f"- Disposição para cozinhar: {_mostrar(dados.disposicao)}")
    print(f"- Itens em casa: {itens}")
    print(f"- Restrições: {restricoes}")


def _ler_orcamento() -> tuple[float, str]:
    while True:
        resposta = input("\nQual é o orçamento em CAD? (ex.: 80)\n> ").strip()
        texto = resposta if re.search(r"[A-Za-z$]", resposta) else f"CAD${resposta}"
        parcial = entender_pedido(texto)
        if parcial.orcamento is not None and parcial.orcamento > 0:
            return parcial.orcamento, parcial.moeda or "CAD"
        print("Não consegui entender. Digite somente o valor, como 80.")


def _ler_quantidade(pergunta: str, unidade: str, atributo: str) -> int:
    while True:
        resposta = input(f"\n{pergunta}\n> ").strip()
        parcial = entender_pedido(f"{resposta} {unidade}")
        quantidade = getattr(parcial, atributo)
        if quantidade is not None and quantidade > 0:
            return quantidade
        print("Digite uma quantidade maior que zero.")


def _ler_disposicao() -> str:
    opcoes = {"1": "baixa", "2": "normal", "3": "alta"}
    while True:
        resposta = input(
            "\nQual é a disposição para cozinhar?\n"
            "1 - Baixa\n2 - Normal\n3 - Alta\n> "
        ).strip().casefold()
        disposicao = opcoes.get(resposta, resposta)
        if disposicao in opcoes.values():
            return disposicao
        print("Escolha 1, 2 ou 3.")


def _dividir_resposta(resposta: str) -> list[str]:
    return [
        item.strip().casefold()
        for item in re.split(r"\s*,\s*|\s+e\s+", resposta)
        if item.strip()
    ]


def _ler_itens() -> list[str]:
    while True:
        resposta = input(
            "\nO que você já tem em casa? "
            "Separe os itens com vírgulas; se não tiver nada, digite 'nada'.\n> "
        ).strip()
        if resposta.casefold() in {"nada", "nenhum", "nenhuma"}:
            return []
        itens = _dividir_resposta(resposta)
        if itens:
            return itens
        print("Informe os itens ou digite 'nada'.")


def _ler_restricoes() -> list[str]:
    while True:
        resposta = input(
            "\nExiste alguma restrição alimentar? "
            "Se não existir, digite 'nenhuma'.\n> "
        ).strip()
        if resposta.casefold() in {"não", "nao", "nenhuma", "nenhum"}:
            return []

        parcial = entender_pedido(resposta)
        restricoes = parcial.restricoes or _dividir_resposta(resposta)
        if restricoes:
            return restricoes
        print("Informe a restrição ou digite 'nenhuma'.")


def completar_dados(dados: PedidoEntendido) -> PedidoEntendido:
    """Pergunta somente os dados que não apareceram no texto inicial."""
    if dados.orcamento is None:
        dados.orcamento, dados.moeda = _ler_orcamento()
    if dados.pessoas is None:
        dados.pessoas = _ler_quantidade("Para quantas pessoas?", "pessoas", "pessoas")
    if dados.dias is None:
        dados.dias = _ler_quantidade("Por quantos dias?", "dias", "dias")
    if dados.disposicao is None:
        dados.disposicao = _ler_disposicao()
    if dados.itens_em_casa is None:
        dados.itens_em_casa = _ler_itens()
    if dados.restricoes is None:
        dados.restricoes = _ler_restricoes()
    return dados


def _confirmar_dados() -> bool:
    while True:
        resposta = input("\nEsses dados estão corretos? (s/n)\n> ").strip().casefold()
        if resposta in {"s", "sim"}:
            return True
        if resposta in {"n", "não", "nao"}:
            return False
        print("Responda com 's' para sim ou 'n' para não.")


def main() -> None:
    """Recebe um pedido e mostra os dados básicos identificados."""
    print("\nCARRINHO")
    print("Planejamento simples de refeições e compras.")

    pedido = input("\nConte sua situação:\n> ").strip()

    if not pedido:
        print("\nNenhum pedido foi informado.")
        return

    dados = completar_dados(entender_pedido(pedido))
    mostrar_resumo(dados)

    if _confirmar_dados():
        print("\nDados confirmados.")
    else:
        print("\nTudo bem. Execute novamente e descreva os dados corrigidos.")

    print("Nenhum plano de refeições foi criado ainda.")


if __name__ == "__main__":
    main()
