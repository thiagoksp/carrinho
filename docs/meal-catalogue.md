# Meal catalogue

`data/meal-catalogue.json` is the curated source of meal templates used by Carrinho.
It is separate from `data/simulated-prices.json` on purpose:

- meal templates express what is needed to prepare a meal;
- the price catalogue describes generic purchasable products, packages, estimates, and
  Instacart search terms.

## Schema

The current schema is `carrinho.meal-catalogue.v2`. Each template has:

- a stable `key` using lowercase letters, numbers, and underscores;
- a user-visible `dish` name;
- a `catalogue_tier` of `core` or `extended`;
- one `cooking_energy` value: `low`, `normal`, or `high`;
- one or more supported `dietary_tags`;
- one or more validated `selection_tags` such as `quick`, `one-pot`, or
  `batch-friendly`;
- one or more ingredients, each with a generic `product_key`, a positive
  `quantity_per_person`, and a canonical `planning_unit`.

The permitted planning units are `g`, `ml`, `can`, `each`, and `package`. Every
ingredient key and unit must match a product in the selected price catalogue before a
plan can be generated.

## Deterministic selection

Carrinho treats the current lactose constraint as a hard filter through the
`lactose-free` tag. It then ranks meals with fewer avoided ingredients, prefers meals
whose `cooking_energy` is closest to the household request, ranks meals with more
preferred ingredients, and finally uses matching pantry ingredients as a deterministic
tie-breaker.
Food likes and dislikes are soft: they change ranking but never bypass a hard dietary
filter. Catalogue order is preserved for the reference case when no soft preferences
are supplied. Extended templates add variety without changing the established
eight-meal reference sequence.

Future dietary restrictions must remain hard constraints. Future likes and disliked
foods must be separate soft preferences, rather than being represented as medical or
dietary tags. The optional LLM selector may suggest candidates, but this validated
catalogue and deterministic selector remain the source of truth for what can be planned.

## Optional LLM boundary

When explicitly enabled, the LLM may receive stable template keys, dish names,
catalogue tiers, cooking energy, dietary tags, selection tags, and generic product
keys. It may return an ordered list of known template keys as a suggestion. It must not
generate authoritative product quantities, cost estimates, dietary compatibility, or
retailer identifiers.

Carrinho will validate every returned key and restriction before the deterministic
planner calculates ingredient totals, pantry deductions, packages, and estimates. This
keeps an LLM useful for preference matching without making it the source of truth.

The public `validate_meal_candidate_keys` boundary accepts only an ordered list of known,
unique template keys and rejects candidates that violate current hard dietary tags. The
LLM adapter is disabled by default, uses Structured Outputs when enabled, and never
grants an LLM authority over calculations. See
[`llm-meal-selector.md`](llm-meal-selector.md).

## Integration boundary

Meal templates do not contain retailer SKUs, brands, prices, or network identifiers.
Those remain product-catalogue or future official-platform concerns. The shared generic
`product_key` is the durable bridge: a future approved provider can map it to an
available product without changing a recipe template.
