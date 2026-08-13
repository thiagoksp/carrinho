# Carrinho

Carrinho será um agente de mercado que reduz o número de decisões entre “preciso me alimentar” e “minhas compras estão prontas”.

## Visão do produto

O usuário informa, em linguagem normal:

- orçamento disponível;
- quantidade de dias;
- energia ou disposição para cozinhar;
- alimentos que já tem em casa.

O sistema deverá gerar um plano de refeições e uma lista de compras. Em versões futuras, poderá pesquisar preços reais, comparar lojas e montar o carrinho de compras.

## Estado atual

O projeto possui uma entrada pelo terminal. Ela identifica, completa e confirma os dados. O planejamento por regras atende de 1 a 12 pessoas por 1 a 14 dias, ajusta quantidades por embalagem e aproveita itens existentes. Quando o plano normal ultrapassa o orçamento em CAD, tenta automaticamente uma alternativa econômica e informa com honestidade se ainda faltar dinheiro. Nesta etapa, aceita somente ausência de restrições ou restrição à lactose.

O cenário de referência aprovado está documentado em [`docs/caso-base.md`](docs/caso-base.md).

## Próxima etapa

Melhorar a leitura das quantidades dos itens que já existem em casa.

## Ambiente local

O projeto usa Python 3.12 e não possui dependências externas nesta etapa.

Para abrir o Carrinho no Windows:

```powershell
.\.venv\Scripts\python.exe app.py
```
