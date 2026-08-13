# Decisão: primeira loja e integração externa

Data: 13 de agosto de 2026.

## Decisão

O primeiro piloto e preferência de loja do Carrinho será **No Frills em Toronto, ON**.

O orçamento continuará usando o catálogo local claramente rotulado como simulado. A
**Instacart Developer Platform** será avaliada futuramente apenas para entregar a lista
ao usuário, que poderá revisar os produtos, selecionar No Frills quando estiver
disponível e seguir para o carrinho. A integração não garante uma loja específica.

Nenhum preço real está sendo coletado nesta etapa e nenhuma requisição externa foi
adicionada ao programa.

## Motivo

- Na pesquisa realizada em 13 de agosto de 2026, não foi localizada uma API pública de
  preços locais para consumidores da No Frills ou do Walmart Canada.
- A Instacart possui integração oficial para aplicativos de planejamento de refeições,
  aceita Canadá e oferece páginas de lista de compras.
- O endpoint público de criação da lista escolhido para este piloto recebe nomes e
  quantidades e devolve um link; sua resposta não entrega preços ao Carrinho.
- A própria documentação informa que o usuário controla a escolha da loja; No Frills é
  uma preferência do piloto, não uma seleção garantida pelo Carrinho.
- A integração exige chave de desenvolvimento e aprovação para produção.

Fontes oficiais consultadas:

- [Instacart Developer Platform](https://docs.instacart.com/developer_platform_api/)
- [Varejistas próximos no Canadá](https://docs.instacart.com/developer_platform_api/api/retailers/get_nearby_retailers/)
- [Criação de lista de compras](https://docs.instacart.com/developer_platform_api/api/products/create_shopping_list_page)
- [No Frills na Instacart Canadá](https://www.instacart.ca/store/no-frills-can/storefront)
- [FAQ e limitações da integração](https://docs.instacart.com/developer_platform_api/faq/)
- [Termos da Developer Platform](https://docs.instacart.com/developer_platform_api/guide/terms_and_policies/developer_terms/)
- [Termos de uso da No Frills](https://www.nofrills.ca/en/termsofuse)
- [APIs do Marketplace Walmart Canada](https://developer.walmart.com/ca-marketplace/docs/introduction-to-marketplace-apis)

## Limites de segurança

O projeto não usará scraping, endpoints privados, sessão do usuário, automação de login,
contorno de CAPTCHA ou checkout automático. Preços só poderão ser marcados como reais
quando vierem de uma fonte autorizada e licenciada.

A Instacart não será usada como mecanismo de comparação de preços entre lojas nem como
garantia de seleção da No Frills. Caso a comparação continue necessária, o Carrinho
precisará de outra fonte licenciada.

## Próxima etapa

Preparar, sem enviar nada pela internet, a conversão da lista atual para o formato de
itens e quantidades aceito pela Instacart. A chave de desenvolvimento só será necessária
quando essa conversão local estiver pronta e testada.
