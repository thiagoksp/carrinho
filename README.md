# Carrinho

> Changing ChatGPT or Codex accounts? Start with [`HANDOFF.md`](HANDOFF.md).

Carrinho is a Canadian grocery-planning agent designed to reduce the decisions between
“we need food” and “the cart is ready to review.”

## Product direction

The user describes a household situation in natural language:

- available budget in Canadian dollars;
- number of people and days;
- cooking energy;
- food already available at home;
- dietary restrictions.

Carrinho produces one practical meal plan, one shopping list, one simulated Canadian
planning estimate per item, and one Instacart shopping-list handoff. Instacart is the
planned shopping platform, not a retailer selected by Carrinho. The user chooses an
available retailer inside Instacart, where address-specific availability and actual
prices are determined.

Carrinho is not a store or price comparison product: it does not rank retailers, combine
carts, or silently replace the meal plan with a cheaper one. The budget remains visible
as either a balance or a shortfall.

## Current state

The terminal app understands and completes an English request, allows one field at a
time to be corrected, and supports 1–12 people for 1–14 days. Its rule-based planner
separates recipe requirements from whole purchasable packages, reports expected
overage, marks variable-weight products as approximate, and accounts for pantry amounts
expressed in kilograms, grams, pounds, litres, millilitres, cans, dozens, units, and
package fractions. Mass is normalized to grams and volume to millilitres before package
rounding. The current values come from
one retailer-neutral JSON catalog that is explicitly labelled as simulated. A planning
request does not require a city or retailer.

The program creates three local files when a plan is saved:

- a readable meal plan;
- an Instacart JSON preview for a future approved integration;
- a plain-text list for manually testing the iPhone **Shopping List → Paste items** flow.

Nothing is sent automatically, and no API key is required. The current planner supports
either no dietary restrictions or lactose intolerance. It does not intentionally include
dairy ingredients, but users must still review product labels.

An Instacart Developer Platform interest form was submitted on August 13, 2026.
Applications are subject to Instacart review and approval; submission did not provide
access or an API key. Network integration therefore remains disabled.

Until approved API access exists, the handoff remains a local preview and a manual
iPhone paste list. Carrinho must not claim that it selected a specific retailer or knows
the final price before the user reviews the list in Instacart.

Project decisions and formats are documented in:

- [`HANDOFF.md`](HANDOFF.md), the single cross-account starting point
- [`docs/reference-case.md`](docs/reference-case.md)
- [`docs/instacart-platform-direction.md`](docs/instacart-platform-direction.md)
- [`docs/instacart-list-preparation.md`](docs/instacart-list-preparation.md)
- [`docs/project-handoff.md`](docs/project-handoff.md)
- [`docs/roadmap.md`](docs/roadmap.md)
- [`docs/initial-integration-decision.md`](docs/initial-integration-decision.md), retained
  as a superseded historical decision

## Next step

Complete CAR-2 by reviewing the new package reconciliation output: recipe need, whole
package count, expected purchased quantity, overage, and variable-weight warning. Do
not test every product or retailer. The documented iPhone **Paste items** and **Cart
Assistant** features were not available in the project's Canadian Instacart account,
so further handoff testing remains gated on an available official surface or approved
Developer Platform access. Keep all network integration disabled until approved access
and contract testing are available.

Task status is tracked in the
[Carrinho Linear project](https://linear.app/thiagoksp/project/carrinho-instacart-mvp-ad1267b5bbde).
The single next task is also mirrored in [`docs/roadmap.md`](docs/roadmap.md) for
cross-account continuity.

## Local environment

The project uses Python 3.12 and currently has no third-party runtime dependencies.

Run Carrinho on Windows:

```powershell
.\.venv\Scripts\python.exe app.py
```

Run the test suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
