"""Entrada inicial do Carrinho pelo terminal."""

from pathlib import Path
import re

from instacart import salvar_payload_instacart
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
    print(f"- Localização das compras: {_mostrar(dados.localizacao)}")
    print(f"- Loja preferida: {_mostrar(dados.loja_preferida)}")


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


def _ler_localizacao() -> str:
    while True:
        resposta = input(
            "\nEm qual cidade ou região você fará as compras? "
            "(ex.: Toronto ou M5V 2T6)\n> "
        ).strip()
        if resposta:
            return resposta
        print("Informe uma cidade, região ou código postal.")


def _ler_loja() -> str:
    respostas_livres = {
        "qualquer",
        "qualquer loja",
        "sem preferencia",
        "sem preferência",
        "tanto faz",
        "nenhuma",
        "nenhum",
        "não",
        "nao",
    }
    while True:
        resposta = input(
            "\nTem alguma loja preferida? "
            "Digite o nome ou 'qualquer'.\n> "
        ).strip()
        if resposta.casefold() in respostas_livres:
            return "qualquer loja"
        if resposta:
            return resposta
        print("Informe uma loja ou digite 'qualquer'.")


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
    if dados.localizacao is None:
        dados.localizacao = _ler_localizacao()
    if dados.loja_preferida is None:
        dados.loja_preferida = _ler_loja()
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
        "7": "localizacao",
        "8": "loja",
    }

    while True:
        resposta = input(
            "\nQual dado você quer corrigir?\n"
            "1 - Orçamento\n"
            "2 - Pessoas\n"
            "3 - Dias\n"
            "4 - Disposição para cozinhar\n"
            "5 - Itens em casa\n"
            "6 - Restrições alimentares\n"
            "7 - Localização das compras\n"
            "8 - Loja preferida\n> "
        ).strip()
        escolha = opcoes.get(resposta)
        if escolha is not None:
            break
        print("Escolha um número de 1 a 8.")

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
    elif escolha == "restricoes":
        dados.restricoes = _ler_restricoes()
    elif escolha == "localizacao":
        dados.localizacao = _ler_localizacao()
    else:
        dados.loja_preferida = _ler_loja()


def revisar_dados(dados: PedidoEntendido) -> PedidoEntendido:
    """Permite corrigir um campo por vez até o usuário confirmar o resumo."""
    while True:
        mostrar_resumo(dados)
        if _confirmar_dados():
            return dados
        _corrigir_um_dado(dados)


def _formatar_dinheiro(moeda: str, valor: float) -> str:
    prefixos = {"CAD": "CAD$", "USD": "US$", "BRL": "R$"}
    prefixo = prefixos.get(moeda, f"{moeda} ")
    return f"{prefixo}{valor:.2f}"


def formatar_plano(plano: Plano) -> str:
    """Produz o mesmo conteúdo para o terminal e para o arquivo salvo."""
    linhas: list[str] = []

    if plano.economico:
        linhas.append("ALTERNATIVA ECONÔMICA")
        linhas.append("O plano inicial ultrapassou o orçamento e foi simplificado.")
        if plano.total_plano_normal is not None:
            economia = plano.total_plano_normal - plano.total_estimado
            linhas.append(
                f"Economia estimada: {_formatar_dinheiro(plano.moeda, economia)}"
            )
        linhas.append("")

    linhas.append("PLANO DE REFEIÇÕES")
    linhas.append(f"Para {plano.pessoas} pessoa(s) durante {plano.dias} dia(s).")
    linhas.append(f"Localização das compras: {_mostrar(plano.localizacao)}.")
    linhas.append(f"Loja preferida: {_mostrar(plano.loja_preferida)}.")
    linhas.append(
        "Nesta etapa, localização e loja ainda não alteram os preços simulados."
    )
    for refeicao in plano.refeicoes:
        linhas.append(
            f"- Dia {refeicao.dia} — {refeicao.momento}: {refeicao.prato}"
        )

    linhas.extend(("", "COMO REDUZIR O TRABALHO"))
    for orientacao in plano.reaproveitamento:
        linhas.append(f"- {orientacao}")

    linhas.extend(("", f"LISTA DE COMPRAS — PREÇOS {plano.tipo_precos.upper()}"))
    for item in plano.compras:
        linhas.append(
            f"- {item.nome}: {item.quantidade} "
            f"— {_formatar_dinheiro(plano.moeda, item.preco_estimado)}"
        )

    total = _formatar_dinheiro(plano.moeda, plano.total_estimado)
    linhas.extend(("", f"Total estimado: {total}"))
    if plano.margem >= 0:
        margem = _formatar_dinheiro(plano.moeda, plano.margem)
        linhas.append(f"Margem do orçamento: {margem}")
    else:
        excesso = _formatar_dinheiro(plano.moeda, abs(plano.margem))
        linhas.append(f"Valor acima do orçamento: {excesso}")

    linhas.append(f"Fonte dos preços: {plano.descricao_precos}")

    linhas.extend(("", "ITENS QUE JÁ ESTÃO EM CASA"))
    if plano.uso_itens_casa:
        for uso in plano.uso_itens_casa:
            linhas.append(f"- {uso}")
    else:
        linhas.append(
            "- Nenhum ingrediente principal do plano foi identificado em casa."
        )

    linhas.extend((
        "",
        "Atenção: o plano não usa ingredientes lácteos intencionalmente, "
        "mas os rótulos dos produtos devem ser conferidos."
    ))
    return "\n".join(linhas)


def mostrar_plano(plano: Plano) -> None:
    """Apresenta o plano e seus custos simulados."""
    print(f"\n{formatar_plano(plano)}")


def _proximo_caminho(diretorio: Path) -> Path:
    caminho = diretorio / "plano-carrinho.txt"
    numero = 2
    while caminho.exists():
        caminho = diretorio / f"plano-carrinho-{numero}.txt"
        numero += 1
    return caminho


def salvar_plano(plano: Plano, diretorio: Path | None = None) -> Path:
    """Salva um novo arquivo sem substituir resultados anteriores."""
    pasta = diretorio or Path(__file__).resolve().parent / "resultados"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = _proximo_caminho(pasta)
    caminho.write_text(f"{formatar_plano(plano)}\n", encoding="utf-8")
    return caminho


def _quer_salvar_plano() -> bool:
    while True:
        resposta = input(
            "\nDeseja salvar o plano e a prévia local da Instacart? (s/n)\n> "
        ).strip()
        resposta = resposta.casefold()
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
        if _quer_salvar_plano():
            caminho_plano = salvar_plano(plano)
            caminho_instacart = salvar_payload_instacart(plano)
            print(f"\nPlano salvo em:\n{caminho_plano}")
            print(
                "\nPrévia Instacart salva localmente — nenhum dado foi enviado:\n"
                f"{caminho_instacart}"
            )


if __name__ == "__main__":
    main()
