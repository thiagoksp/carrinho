# Caso-base do Carrinho

Este é o primeiro cenário de referência aprovado para orientar o desenvolvimento e os testes do projeto.

## Entrada

> Tenho CAD$80 para alimentar 2 pessoas por 4 dias. Estamos com pouca disposição para cozinhar, já temos arroz e 7 ovos, e pelo menos uma pessoa tem intolerância à lactose. Precisamos de almoço e jantar. Estou em Toronto e não tenho preferência de loja.

## Interpretação esperada

- Orçamento máximo: CAD$80.
- Pessoas: 2.
- Período: 4 dias.
- Refeições: almoço e jantar.
- Total: 8 refeições para o grupo, equivalentes a 16 porções individuais.
- Disposição para cozinhar: baixa.
- Itens disponíveis: arroz em quantidade suficiente e 7 ovos.
- Restrição: todo o plano deve ser seguro sem lactose.
- Localização das compras: Toronto.
- Loja preferida: qualquer loja.

## Formato esperado da resposta

1. Resumo do pedido entendido.
2. Plano de almoço e jantar para os 4 dias.
3. Reaproveitamento de sobras para reduzir o trabalho.
4. Lista de compras com quantidades.
5. Preços estimados e total previsto.
6. Margem restante do orçamento.
7. Indicação de como o arroz e os 7 ovos serão aproveitados.

## Critérios de aceitação

- O plano contém exatamente 4 almoços e 4 jantares para 2 pessoas.
- Nenhum item com lactose é necessário.
- As refeições priorizam preparos simples e reaproveitamento.
- A lista considera o arroz e os ovos já disponíveis.
- O custo total estimado não ultrapassa CAD$80.
- A localização e a preferência de loja aparecem no resumo e no plano salvo.
- Preços reais, comparação de lojas e montagem de carrinho não fazem parte desta primeira versão.
