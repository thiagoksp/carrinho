# Preparação local da lista Instacart

Data: 13 de agosto de 2026.

## O que foi preparado

Ao salvar um resultado, o Carrinho cria três arquivos locais:

- `plano-carrinho.txt`, legível para o usuário;
- `lista-instacart.json`, uma prévia do futuro corpo da requisição.
- `lista-instacart-colar.txt`, com um produto por linha para colagem manual.

Nenhuma chamada de rede é feita. A prévia não contém preços, orçamento, localização,
loja, credenciais, cabeçalhos ou endereço do serviço.

## Caminho disponível sem chave

Em 13 de agosto de 2026, a página oficial da Developer Platform informa que não
está aceitando novas inscrições e que não há lista de espera. A integração automática
continua desativada.

O aplicativo da Instacart oferece uma ponte manual oficial no iPhone:

1. Abra **Shopping List**.
2. Toque em **Paste items**.
3. Cole o conteúdo de `lista-instacart-colar.txt`.
4. Revise as correspondências e quantidades.
5. Use **Add all items to cart** somente depois da revisão.

A ajuda oficial aceita até 200 itens por colagem e informa que linhas ou vírgulas são
separadores aceitos. O Carrinho usa uma linha por produto e termos em inglês, por exemplo:

```text
chicken thighs (1.2 kg)
tomato sauce (2 cans)
vegetable oil (946 ml)
```

A Instacart decide quais produtos correspondem ao texto, e a ajuda oficial não garante
que as medidas entre parênteses sejam entendidas como quantidades. O arquivo é uma
preparação para teste: não garante marca, loja, preço, quantidade final nem ausência de
lactose. O usuário deve revisar produtos, medidas, ingredientes e rótulos antes de seguir
para o carrinho.

O Carrinho não transmite o arquivo. Quando o usuário copia e cola o conteúdo no
aplicativo, esse conteúdo passa a ser enviado à Instacart.

Fontes oficiais:

- [Status das inscrições](https://company.instacart.com/business/developers)
- [Copiar e colar uma Shopping List](https://www.instacart.ca/help/section/2893565984/3344870287)

## Formato adotado

O JSON usa somente os campos atuais necessários para uma lista de compras:

```json
{
  "title": "Lista Carrinho — 2 pessoas por 4 dias",
  "link_type": "shopping_list",
  "line_items": [
    {
      "name": "chicken thighs",
      "display_text": "Coxas ou sobrecoxas de frango: 1,2 kg",
      "line_item_measurements": [
        {
          "quantity": 1.2,
          "unit": "kg"
        }
      ]
    }
  ]
}
```

`name` é um termo genérico usado na busca. `display_text` preserva a apresentação
amigável. As medidas usam somente unidades documentadas pela Instacart.

Os campos `quantity` e `unit` diretamente dentro do item não são usados, pois foram
marcados como obsoletos. As medidas ficam em `line_item_measurements`.

Fontes oficiais:

- [Criar uma lista de compras](https://docs.instacart.com/developer_platform_api/api/products/create_shopping_list_page/)
- [Conceitos da lista](https://docs.instacart.com/developer_platform_api/guide/concepts/shopping_list/)
- [Unidades aceitas](https://docs.instacart.com/developer_platform_api/api/units_of_measurement/)
- [Erros e recomendações de nomes](https://docs.instacart.com/developer_platform_api/errors/)

## Canadá

O piloto continua sendo canadense. O código do país não foi colocado no corpo da
requisição porque a referência atual do endpoint não documenta esse campo, embora um
changelog anterior o mencione. A localização permanece no plano em texto.

Antes da primeira chamada, o comportamento para o Canadá deverá ser verificado no
servidor de desenvolvimento com uma chave própria da Instacart. Até lá, o JSON é apenas
uma prévia local e nunca deve ser enviado automaticamente.

## Próxima etapa

Validar uma lista no fluxo manual do iPhone. Quando as inscrições reabrirem, solicitar
acesso de desenvolvimento e fazer um único teste de contrato, sem checkout, para
confirmar o formato e o tratamento do Canadá antes de integrar qualquer chamada.
