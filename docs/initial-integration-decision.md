# Decision: initial store and external integration

Date: August 13, 2026.

Status: superseded on August 14, 2026, by
[`instacart-platform-direction.md`](instacart-platform-direction.md). This document is
retained as the historical decision behind the current transitional implementation.

## Decision

The first Carrinho pilot uses **No Frills in Toronto, Ontario** as its selected store.
Each run uses one catalog and one working price per item. Store ranking, lowest-price
search, multi-store baskets, and cross-store comparison are not product goals.

Budget calculations continue to use one local catalog clearly labelled as simulated.
The **Instacart Developer Platform** may later provide a reviewable hosted shopping-list
handoff after approved access. It is not a price source for the planner and cannot
guarantee that No Frills is selected.

Manual price declarations may be saved in separate local files. They are historical,
self-declared, unverified, and isolated from planning. No external request has been
added to the app.

## Rationale

- No public, authorized No Frills or Loblaw feed was identified for exact local consumer
  prices by store.
- Instacart documents a shopping-list integration for meal-planning applications in
  Canada.
- The selected create-list endpoint receives product names and quantities and returns a
  hosted link; its response does not provide prices to Carrinho.
- The user controls the retailer on the hosted experience. Carrinho cannot guarantee
  that the pilot store is selected.
- The integration requires approved access and credentials.
- Carrinho submitted the Canadian Developer Platform interest form on August 13, 2026.
  No approval or API key has been received, so network integration remains disabled.
- Until access is approved, the official iPhone **Shopping List → Paste items** feature
  provides a manual handoff that the user can review.

Official sources:

- [Instacart Developer Platform](https://docs.instacart.com/developer_platform_api/)
- [Canadian Developer Platform application](https://company.instacart.ca/business/developers)
- [Shopping List and Paste items](https://www.instacart.ca/help/section/2893565984/3344870287)
- [Nearby Canadian retailers](https://docs.instacart.com/developer_platform_api/api/retailers/get_nearby_retailers/)
- [Create Shopping List Page](https://docs.instacart.com/developer_platform_api/api/products/create_shopping_list_page)
- [No Frills on Instacart Canada](https://www.instacart.ca/store/no-frills-can/storefront)
- [Instacart integration FAQ](https://docs.instacart.com/developer_platform_api/faq/)
- [Instacart Developer Platform terms](https://docs.instacart.com/developer_platform_api/guide/terms_and_policies/developer_terms/)
- [Instacart Canada terms](https://www.instacart.ca/terms)
- [No Frills terms](https://www.nofrills.ca/en/termsofuse)

## Safety boundaries

Carrinho will not use scraping, private endpoints, a user session, login automation,
CAPTCHA bypass, or automatic checkout. A value may be described as a real price only
when it comes from an authorized source under terms that permit the intended use.

The current local conversion creates an API-shaped preview and a manual paste list
without sending data or requiring a key. When the user pastes that list into Instacart,
the content is then sent to Instacart. See
[`instacart-list-preparation.md`](instacart-list-preparation.md).
