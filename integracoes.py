"""Registro das integrações de loja planejadas para o Carrinho."""

from dataclasses import dataclass
import json
from pathlib import Path
import re

from catalogo import carregar_catalogo


FONTES_PRECOS = {"simulada", "licenciada"}
ENTREGAS_LISTA = {"nenhuma", "instacart"}
STATUS = {"planejada", "desenvolvimento", "disponivel"}
INTEGRACAO_PILOTO_ID = "no-frills-toronto"


@dataclass(frozen=True)
class IntegracaoLoja:
    id: str
    loja_piloto: str
    localizacao_piloto: str
    pais: str
    moeda: str
    fonte_precos: str
    status_precos: str
    catalogo_local: Path
    entrega_lista: str
    status_entrega: str
    permite_fixar_loja: bool
    precos_reais_disponiveis: bool
    aviso: str

    @property
    def pode_usar_precos_reais(self) -> bool:
        return (
            self.fonte_precos == "licenciada"
            and self.status_precos == "disponivel"
            and self.precos_reais_disponiveis
        )

    @property
    def pode_entregar_lista(self) -> bool:
        return (
            self.entrega_lista != "nenhuma"
            and self.status_entrega == "disponivel"
        )


def _texto_obrigatorio(dados: dict[str, object], campo: str, posicao: int) -> str:
    valor = dados.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(
            f"Integração {posicao} precisa informar o campo {campo}."
        )
    return valor.strip()


def _validar_catalogo_local(
    caminho_informado: str,
    diretorio_dados: Path,
    fonte_precos: str,
    moeda: str,
    posicao: int,
) -> Path:
    caminho_relativo = Path(caminho_informado)
    if caminho_relativo.is_absolute():
        raise ValueError(f"Integração {posicao} possui catálogo fora de dados.")

    diretorio_resolvido = diretorio_dados.resolve()
    caminho_resolvido = (diretorio_resolvido / caminho_relativo).resolve()
    if not caminho_resolvido.is_relative_to(diretorio_resolvido):
        raise ValueError(f"Integração {posicao} possui catálogo fora de dados.")
    if not caminho_resolvido.is_file():
        raise ValueError(f"Integração {posicao} aponta para catálogo inexistente.")

    catalogo = carregar_catalogo(caminho_resolvido)
    if catalogo.moeda != moeda:
        raise ValueError(f"Integração {posicao} possui catálogo em outra moeda.")
    if fonte_precos == "simulada" and catalogo.tipo != "simulados":
        raise ValueError(
            f"Integração {posicao} precisa usar catálogo rotulado como simulado."
        )
    if fonte_precos == "licenciada" and catalogo.tipo != "licenciados":
        raise ValueError(
            f"Integração {posicao} precisa usar catálogo rotulado como licenciado."
        )
    return caminho_resolvido


def _validar_integracao(
    dados: object, posicao: int, diretorio_dados: Path
) -> IntegracaoLoja:
    if not isinstance(dados, dict):
        raise ValueError(f"Integração {posicao} deve ser um objeto.")

    identificador = _texto_obrigatorio(dados, "id", posicao)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identificador):
        raise ValueError(f"Integração {posicao} possui id inválido.")

    pais = _texto_obrigatorio(dados, "pais", posicao).upper()
    moeda = _texto_obrigatorio(dados, "moeda", posicao).upper()
    if not re.fullmatch(r"[A-Z]{2}", pais):
        raise ValueError(f"Integração {posicao} possui país inválido.")
    if not re.fullmatch(r"[A-Z]{3}", moeda):
        raise ValueError(f"Integração {posicao} possui moeda inválida.")

    fonte_precos = _texto_obrigatorio(dados, "fonte_precos", posicao)
    entrega_lista = _texto_obrigatorio(dados, "entrega_lista", posicao)
    status_precos = _texto_obrigatorio(dados, "status_precos", posicao)
    status_entrega = _texto_obrigatorio(dados, "status_entrega", posicao)
    if fonte_precos not in FONTES_PRECOS:
        raise ValueError(f"Integração {posicao} possui fonte de preços inválida.")
    if entrega_lista not in ENTREGAS_LISTA:
        raise ValueError(f"Integração {posicao} possui entrega de lista inválida.")
    if status_precos not in STATUS:
        raise ValueError(f"Integração {posicao} possui status de preços inválido.")
    if status_entrega not in STATUS:
        raise ValueError(f"Integração {posicao} possui status de entrega inválido.")

    precos_reais = dados.get("precos_reais_disponiveis")
    if not isinstance(precos_reais, bool):
        raise ValueError(
            f"Integração {posicao} precisa informar se há preços reais."
        )
    if precos_reais and fonte_precos != "licenciada":
        raise ValueError(
            "Preços reais só podem ser ativados com uma fonte licenciada."
        )
    if precos_reais and status_precos != "disponivel":
        raise ValueError("Preços reais só podem usar uma fonte disponível.")

    permite_fixar_loja = dados.get("permite_fixar_loja")
    if not isinstance(permite_fixar_loja, bool):
        raise ValueError(
            f"Integração {posicao} precisa informar se pode fixar a loja."
        )
    if entrega_lista == "instacart" and permite_fixar_loja:
        raise ValueError("A integração Instacart não pode garantir uma loja fixa.")
    if status_entrega == "disponivel" and entrega_lista == "nenhuma":
        raise ValueError(
            "Uma integração disponível precisa definir a entrega da lista."
        )

    caminho_catalogo = _validar_catalogo_local(
        _texto_obrigatorio(dados, "catalogo_local", posicao),
        diretorio_dados,
        fonte_precos,
        moeda,
        posicao,
    )

    return IntegracaoLoja(
        id=identificador,
        loja_piloto=_texto_obrigatorio(dados, "loja_piloto", posicao),
        localizacao_piloto=_texto_obrigatorio(
            dados, "localizacao_piloto", posicao
        ),
        pais=pais,
        moeda=moeda,
        fonte_precos=fonte_precos,
        status_precos=status_precos,
        catalogo_local=caminho_catalogo,
        entrega_lista=entrega_lista,
        status_entrega=status_entrega,
        permite_fixar_loja=permite_fixar_loja,
        precos_reais_disponiveis=precos_reais,
        aviso=_texto_obrigatorio(dados, "aviso", posicao),
    )


def carregar_integracoes(caminho: Path) -> tuple[IntegracaoLoja, ...]:
    """Carrega e valida o registro local de estratégias por loja."""
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if not isinstance(dados, dict):
        raise ValueError("O registro de integrações deve ser um objeto JSON.")

    registros = dados.get("integracoes")
    if not isinstance(registros, list) or not registros:
        raise ValueError("O registro precisa conter integrações.")

    integracoes = tuple(
        _validar_integracao(registro, posicao, caminho.resolve().parent)
        for posicao, registro in enumerate(registros, start=1)
    )
    identificadores = [integracao.id for integracao in integracoes]
    if len(identificadores) != len(set(identificadores)):
        raise ValueError("O registro contém ids de integração repetidos.")
    return integracoes


def carregar_integracao_piloto() -> IntegracaoLoja:
    caminho = Path(__file__).resolve().parent / "dados" / "integracoes_lojas.json"
    integracoes = carregar_integracoes(caminho)
    for integracao in integracoes:
        if integracao.id == INTEGRACAO_PILOTO_ID:
            return integracao
    raise ValueError("A integração piloto não foi encontrada.")
