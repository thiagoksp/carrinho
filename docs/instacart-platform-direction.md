# Decision: Instacart as the Canadian shopping platform

Date: August 14, 2026.

## Decision

Carrinho will use **Instacart as its single planned shopping platform for Canada**.
Instacart is a marketplace and handoff destination, not a retailer that Carrinho can
select or guarantee.

Carrinho will create one meal plan, one retailer-neutral shopping list, and one
reviewable shopping-list handoff. The user's address and Instacart context determine
which retailers are available. The user selects a retailer inside Instacart, which then
determines product matches, availability, local prices, fees, and checkout details.

Carrinho will not require No Frills, Toronto, a city, or a selected retailer as planning
inputs. Canada and CAD remain product constraints. The current No Frills and Toronto
requirement is transitional implementation behaviour and will be removed in a separate
code increment.

## Price boundary

The planner may use one clearly labelled, non-store-specific Canadian estimate per item
to show a budget balance or shortfall. That estimate is simulated, is not a live quote,
and is not attributed to the retailer the user later chooses.

Actual retailer-specific prices and availability belong to the Instacart experience.
Carrinho must not claim to know the final cart total before the user reviews matched
products, quantities, substitutions, fees, and prices there.

Manual price declarations remain local, self-declared, unverified, and isolated from
planning. They are legacy research artifacts from the store-specific pilot, not the
planned Instacart price source.

## Rationale

- Instacart's shopping-list flow is designed for an application to send line items and
  return a hosted page where the user selects a preferred store.
- Instacart currently does not support directing the user to a specific merchant through
  the shopping-list integration.
- Available retailers, products, and delivery service depend on the user's address.
- Delegating retailer selection removes unnecessary store and city decisions from
  Carrinho's planning conversation.
- One shopping-list handoff preserves Carrinho's simple direction without turning the
  product into a retailer or price comparator.
- Carrinho submitted the Canadian Developer Platform interest form on August 13, 2026.
  No approval or API key has been received, so network integration remains disabled.
- Until approved access exists, the official iPhone **Shopping List -> Paste items**
  feature provides a manual, reviewable handoff.

## Planned implementation sequence

1. Remove shopping area and selected retailer from the parsed request and terminal flow.
2. Remove the No Frills and Toronto eligibility rule from planning.
3. Keep one simulated Canadian catalog for clearly labelled budget guidance.
4. Keep generating one Instacart preview and one manual paste list.
5. Let the user choose one available retailer during the Instacart handoff.
6. Validate one official development request only after access and a key are approved.
7. Replace estimates with retailer results only if an approved contract exposes them to
   Carrinho; do not scrape or infer private marketplace data.

## Non-goals

- choosing or guaranteeing a specific retailer;
- building direct retailer carts or retailer-specific price feeds;
- comparing retailers or building a cheapest-store basket;
- combining multiple retailer carts;
- scraping Instacart or retailer sites;
- automating login, checkout, CAPTCHA handling, or private endpoints;
- presenting planning estimates as live retailer prices.

## Official sources

- [Shopping-list concepts](https://docs.instacart.com/developer_platform_api/guide/concepts/shopping_list/)
- [Create Shopping List Page](https://docs.instacart.com/developer_platform_api/api/products/create_shopping_list_page/)
- [Instacart integration FAQ](https://docs.instacart.com/developer_platform_api/faq/)
- [Selecting a store](https://www.instacart.ca/help/section/809794019/691600369)
- [Where Instacart delivers](https://www.instacart.ca/help/section/360007797972/360039569711)
- [Shopping List and Paste items](https://www.instacart.ca/help/section/2893565984/3344870287)
- [Canadian Developer Platform application](https://company.instacart.ca/business/developers)
- [Instacart Developer Platform terms](https://docs.instacart.com/developer_platform_api/guide/terms_and_policies/developer_terms/)
- [Instacart Canada terms](https://www.instacart.ca/terms)

## Safety boundary

No network behaviour changes with this decision. The current local conversion creates
an API-shaped preview and a manual paste list without sending data or requiring a key.
When the user pastes that list into Instacart, the content is sent to Instacart. See
[`instacart-list-preparation.md`](instacart-list-preparation.md).
