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

O projeto possui uma entrada pelo terminal. Ela identifica e completa os dados, incluindo localização das compras e loja preferida; durante a confirmação, permite corrigir um campo por vez sem reiniciar. O planejamento por regras atende de 1 a 12 pessoas por 1 a 14 dias, ajusta quantidades por embalagem e desconta o estoque informado em kg, g, litros, latas, dúzias, unidades e frações de pacotes. Quando o plano normal ultrapassa o orçamento em CAD, tenta automaticamente uma alternativa econômica e informa com honestidade se ainda faltar dinheiro. Os valores vêm de um catálogo JSON claramente identificado como simulado, que pode ser substituído por outra fonte. No Frills em Toronto foi registrada como a primeira loja piloto; a futura entrega automática será estudada pela integração oficial da Instacart, sem tratar essa integração como fonte de preços e sem garantir a seleção da loja. Ao salvar, o programa cria o plano, uma prévia JSON e uma lista de texto formatada para testar manualmente o recurso **Paste items** da Shopping List no iPhone. Nada é enviado automaticamente e nenhuma chave é exigida. Nesta etapa, aceita somente ausência de restrições ou restrição à lactose.

Em 13 de agosto de 2026, a página oficial da Instacart informa que novas inscrições na Developer Platform estão fechadas e não há lista de espera. Por isso, a integração de rede permanece desligada; o caminho disponível é copiar a lista de texto, colá-la no aplicativo e revisar os produtos antes de adicioná-los ao carrinho.

O cenário de referência aprovado está documentado em [`docs/caso-base.md`](docs/caso-base.md). A escolha da primeira loja e seus limites estão em [`docs/decisao-primeira-integracao.md`](docs/decisao-primeira-integracao.md). O formato da prévia local está em [`docs/preparacao-instacart.md`](docs/preparacao-instacart.md).

## Próxima etapa

Validar a lista de texto uma vez no recurso **Shopping List → Paste items** do iPhone. Quando a Instacart reabrir as inscrições, solicitar uma chave de desenvolvimento e testar uma única prévia no ambiente oficial antes de adicionar rede ao aplicativo.

## Ambiente local

O projeto usa Python 3.12 e não possui dependências externas nesta etapa.

Para abrir o Carrinho no Windows:

```powershell
.\.venv\Scripts\python.exe app.py
```
