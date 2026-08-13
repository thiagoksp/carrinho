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

O projeto possui uma entrada pelo terminal. Ela identifica e completa os dados, incluindo localização das compras e loja preferida; durante a confirmação, permite corrigir um campo por vez sem reiniciar. O planejamento por regras atende de 1 a 12 pessoas por 1 a 14 dias, ajusta quantidades por embalagem e desconta o estoque informado em kg, g, litros, latas, dúzias, unidades e frações de pacotes. Quando o plano normal ultrapassa o orçamento em CAD, tenta automaticamente uma alternativa econômica e informa com honestidade se ainda faltar dinheiro. Os valores vêm de um catálogo JSON claramente identificado como simulado, que pode ser substituído por outra fonte. No Frills em Toronto foi registrada como a primeira loja piloto; a futura entrega da lista será estudada pela integração oficial da Instacart, sem tratar essa integração como fonte de preços e sem garantir a seleção da loja. Ao final, o programa pode salvar o plano e a lista em um novo arquivo dentro de `resultados/`. Nesta etapa, aceita somente ausência de restrições ou restrição à lactose.

O cenário de referência aprovado está documentado em [`docs/caso-base.md`](docs/caso-base.md). A escolha da primeira loja, seus limites e as fontes oficiais estão em [`docs/decisao-primeira-integracao.md`](docs/decisao-primeira-integracao.md).

## Próxima etapa

Converter localmente a lista para o formato aceito pela Instacart, ainda sem enviar dados nem exigir uma chave.

## Ambiente local

O projeto usa Python 3.12 e não possui dependências externas nesta etapa.

Para abrir o Carrinho no Windows:

```powershell
.\.venv\Scripts\python.exe app.py
```
