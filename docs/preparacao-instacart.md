# Preparação local da lista Instacart

Data: 13 de agosto de 2026.

## O que foi preparado

Ao salvar um resultado, o Carrinho cria dois arquivos locais:

- `plano-carrinho.txt`, legível para o usuário;
- `lista-instacart.json`, uma prévia do futuro corpo da requisição.

Nenhuma chamada de rede é feita. A prévia não contém preços, orçamento, localização,
loja, credenciais, cabeçalhos ou endereço do serviço.

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

Solicitar acesso de desenvolvimento à Instacart. Depois, fazer um único teste de
contrato no ambiente de desenvolvimento, sem checkout, para confirmar o formato e o
tratamento do Canadá antes de integrar qualquer chamada ao aplicativo.
