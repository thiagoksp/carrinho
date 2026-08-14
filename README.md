# Carrinho

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
adjusts package quantities and accounts for pantry amounts expressed in kilograms,
grams, litres, cans, dozens, units, and package fractions. The current values come from
one JSON catalog that is explicitly labelled as simulated.

The current terminal pilot still accepts only No Frills in Toronto, Ontario. This is
transitional behaviour scheduled for removal; it is not the approved product direction.
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

A separate manual-price importer creates an Excel-compatible CSV and stores local,
self-declared observations with package, exact store location, date, channel, and source.
The CSV hash preserves an import trail but does not prove that a value is authentic,
licensed, live, or verified. These observations are isolated from the planner and cannot
change its budget calculations. This importer remains a legacy research tool from the
store-specific pilot and is not the planned Instacart price source.

## Approved transition

The next product increment removes shopping area and selected store from the Carrinho
request. Canada and CAD remain fixed product constraints. Carrinho will generate one
retailer-neutral list and hand it to Instacart; the user's Instacart context will
determine available retailers, local products, availability, and actual checkout prices.

Until approved API access exists, the handoff remains a local preview and a manual
iPhone paste list. Carrinho must not claim that it selected a specific retailer or knows
the final price before the user reviews the list in Instacart.

Project decisions and formats are documented in:

- [`docs/reference-case.md`](docs/reference-case.md)
- [`docs/instacart-platform-direction.md`](docs/instacart-platform-direction.md)
- [`docs/initial-integration-decision.md`](docs/initial-integration-decision.md)
- [`docs/instacart-list-preparation.md`](docs/instacart-list-preparation.md)
- [`docs/manual-price-observations.md`](docs/manual-price-observations.md)

## Next step

Remove the transitional No Frills and Toronto fields from the request and planning model
while keeping the current simulated Canadian catalog for budget guidance. Preserve the
manual iPhone paste flow and keep all network integration disabled until approved access
and contract testing are available.

## Local environment

The project uses Python 3.12 and currently has no third-party runtime dependencies.

Run Carrinho on Windows:

```powershell
.\.venv\Scripts\python.exe app.py
```

Create the manual-price CSV template:

```powershell
.\.venv\Scripts\python.exe manual_prices.py create-template
```

Run the test suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
