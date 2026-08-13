"""Entrada inicial do Carrinho pelo terminal."""

import re

from pedido import PedidoEntendido, entender_pedido
from planejamento import Plano, gerar_plano


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


def _corrigir_um_dado(dados: PedidoEntendido) -> None:
    opcoes = {
        "1": "orcamento",
        "2": "pessoas",
        "3": "dias",
        "4": "disposicao",
        "5": "itens",
        "6": "restricoes",
    }

    while True:
        resposta = input(
            "\nQual dado você quer corrigir?\n"
            "1 - Orçamento\n"
            "2 - Pessoas\n"
            "3 - Dias\n"
            "4 - Disposição para cozinhar\n"
            "5 - Itens em casa\n"
            "6 - Restrições alimentares\n> "
        ).strip()
        escolha = opcoes.get(resposta)
        if escolha is not None:
            break
        print("Escolha um número de 1 a 6.")

    if escolha == "orcamento":
        dados.orcamento, dados.moeda = _ler_orcamento()
    elif escolha == "pessoas":
        dados.pessoas = _ler_quantidade(
            "Para quantas pessoas?", "pessoas", "pessoas"
        )
    elif escolha == "dias":
        dados.dias = _ler_quantidade("Por quantos dias?", "dias", "dias")
    elif escolha == "disposicao":
        dados.disposicao = _ler_disposicao()
    elif escolha == "itens":
        dados.itens_em_casa = _ler_itens()
    else:
        dados.restricoes = _ler_restricoes()


def revisar_dados(dados: PedidoEntendido) -> PedidoEntendido:
    """Permite corrigir um campo por vez até o usuário confirmar o resumo."""
    while True:
        mostrar_resumo(dados)
        if _confirmar_dados():
            return dados
        _corrigir_um_dado(dados)


def mostrar_plano(plano: Plano) -> None:
    """Apresenta o primeiro plano e seus custos simulados."""
    if plano.economico:
        print("\nALTERNATIVA ECONÔMICA")
        print("O plano inicial ultrapassou o orçamento e foi simplificado.")
        if plano.total_plano_normal is not None:
            economia = plano.total_plano_normal - plano.total_estimado
            print(f"Economia estimada: CAD${economia:.2f}")

    print("\nPLANO DE REFEIÇÕES")
    print(f"Para {plano.pessoas} pessoa(s) durante {plano.dias} dia(s).")
    for refeicao in plano.refeicoes:
        print(f"- Dia {refeicao.dia} — {refeicao.momento}: {refeicao.prato}")

    print("\nCOMO REDUZIR O TRABALHO")
    for orientacao in plano.reaproveitamento:
        print(f"- {orientacao}")

    print("\nLISTA DE COMPRAS — PREÇOS SIMULADOS")
    for item in plano.compras:
        print(
            f"- {item.nome}: {item.quantidade} "
            f"— CAD${item.preco_estimado:.2f}"
        )

    print(f"\nTotal estimado: CAD${plano.total_estimado:.2f}")
    if plano.margem >= 0:
        print(f"Margem do orçamento: CAD${plano.margem:.2f}")
    else:
        print(f"Valor acima do orçamento: CAD${abs(plano.margem):.2f}")

    print("\nITENS QUE JÁ ESTÃO EM CASA")
    if plano.uso_itens_casa:
        for uso in plano.uso_itens_casa:
            print(f"- {uso}")
    else:
        print("- Nenhum ingrediente principal do plano foi identificado em casa.")

    print(
        "\nAtenção: o plano não usa ingredientes lácteos intencionalmente, "
        "mas os rótulos dos produtos devem ser conferidos."
    )


def main() -> None:
    """Recebe um pedido e mostra os dados básicos identificados."""
    print("\nCARRINHO")
    print("Planejamento simples de refeições e compras.")

    pedido = input("\nConte sua situação:\n> ").strip()

    if not pedido:
        print("\nNenhum pedido foi informado.")
        return

    dados = revisar_dados(completar_dados(entender_pedido(pedido)))
    print("\nDados confirmados.")

    plano = gerar_plano(dados)
    if plano is None:
        print(
            "\nEsta versão planeja de 1 a 12 pessoas por 1 a 14 dias, "
            "em CAD, sem restrições ou somente com restrição à lactose."
        )
    else:
        mostrar_plano(plano)


if __name__ == "__main__":
    main()
