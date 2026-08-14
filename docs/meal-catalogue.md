# Meal catalogue

`data/meal-catalogue.json` is the curated source of meal templates used by Carrinho.
It is separate from `data/simulated-prices.json` on purpose:

- meal templates express what is needed to prepare a meal;
- the price catalogue describes generic purchasable products, packages, estimates, and
  Instacart search terms.

## Schema

The current schema is `carrinho.meal-catalogue.v1`. Each template has:

- a stable `key` using lowercase letters, numbers, and underscores;
- a user-visible `dish` name;
- one or more ingredients, each with a generic `product_key`, a positive
  `quantity_per_person`, and a canonical `planning_unit`.

The permitted planning units are `g`, `ml`, `can`, `each`, and `package`. Every
ingredient key and unit must match a product in the selected price catalogue before a
plan can be generated.

## Integration boundary

Meal templates do not contain retailer SKUs, brands, prices, or network identifiers.
Those remain product-catalogue or future official-platform concerns. The shared generic
`product_key` is the durable bridge: a future approved provider can map it to an
available product without changing a recipe template.
