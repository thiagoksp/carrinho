# Local Instacart list preparation

Date: August 13, 2026. Updated August 14, 2026.

## What is prepared

When a result is saved, Carrinho creates three local files:

- `meal-plan.txt`, readable by the user;
- `instacart-list.json`, a preview of a future approved request body;
- `instacart-paste-list.txt`, one product per line for manual pasting.

The local browser can also download these same portable artifacts directly from the
generated plan page. The browser page can copy the readable plan and print a clean plan
view without creating an account, sending a request, or opening Instacart.

No network call is made. The preview does not contain prices, budget, shopping location,
selected store, credentials, headers, or a service endpoint.

Omitting store and location is the approved direction, not a limitation of the preview.
Carrinho delegates address, retailer selection, product matching, availability, and
actual prices to Instacart after the handoff.

## Available path without an API key

Carrinho submitted the Canadian Developer Platform interest form on August 13, 2026.
Applications are subject to Instacart review and approval. Submission did not provide
access or a key, so automatic integration remains disabled.

Instacart documents the following iPhone manual handoff, but it was not available in
the project's Canadian account on August 14, 2026:

1. Open **Shopping List**.
2. Select **Paste items**.
3. Paste the contents of `instacart-paste-list.txt`.
4. Review every product match and quantity.
5. Use **Add all items to cart** only after review.

Instacart documents a limit of 200 pasted items and accepts items separated by lines or
commas. Carrinho uses one line per product and English search terms, for example:

```text
chicken thighs (1.2 kg)
tomato sauce (2 cans)
vegetable oil (946 ml)
```

Instacart selects products that match the text. Its help page does not guarantee that a
measurement in parentheses will be interpreted as a quantity. This file is formatted
for manual testing; it does not guarantee a brand, retailer, price, final quantity, or
lactose-free product. The user must review product matches, quantities, ingredients, and
labels before adding anything to the cart.

Carrinho does not transmit this file. The content is sent to Instacart only when the user
copies and pastes it into the app.

Official sources:

- [Canadian Developer Platform application](https://company.instacart.ca/business/developers)
- [Shopping List and Paste items](https://www.instacart.ca/help/section/2893565984/3344870287)

## JSON format

The preview uses only the currently required shopping-list fields:

```json
{
  "title": "Carrinho list - 2 people for 4 days",
  "link_type": "shopping_list",
  "line_items": [
    {
      "name": "chicken thighs",
      "display_text": "Chicken thighs: 1.2 kg",
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

`name` is a generic search term. `display_text` keeps a readable description. Measures
use documented Instacart units. Deprecated top-level item fields `quantity` and `unit`
are omitted; measurements are stored in `line_item_measurements`.

Official sources:

- [Create Shopping List Page](https://docs.instacart.com/developer_platform_api/api/products/create_shopping_list_page/)
- [Shopping-list concepts](https://docs.instacart.com/developer_platform_api/guide/concepts/shopping_list/)
- [Accepted measurement units](https://docs.instacart.com/developer_platform_api/api/units_of_measurement/)
- [Errors and product-name guidance](https://docs.instacart.com/developer_platform_api/errors/)

## Canada

The product remains Canadian. `country_code` is not included in the preview because the
current endpoint reference does not document that field, although an earlier changelog
mentioned it. Shopping location and retailer are not part of the Carrinho request,
planning model, meal plan, or handoff. Location and retailer selection remain inside
Instacart.

Before the first network call, Canadian behaviour must be verified once against the
development server with a project-owned Instacart key. Until then, the JSON is a local
preview and must never be sent automatically.

## Next step

Do not test every product or retailer while the documented manual feature is
unavailable. If the manual handoff appears later, validate only a small representative
set. If development access and a key are approved, run one non-checkout contract test
against the development server before integrating any network call.
