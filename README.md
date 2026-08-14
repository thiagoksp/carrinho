# Carrinho

Carrinho is a Canadian grocery-planning agent designed to reduce the decisions between
“we need food” and “the cart is ready to review.”

## Product direction

The user describes a household situation in natural language:

- available budget in Canadian dollars;
- number of people and days;
- cooking energy;
- food already available at home;
- dietary restrictions;
- shopping area and selected store.

Carrinho produces one practical meal plan, one shopping list, one selected working price
per item, and one cart handoff. It is not a store or price comparison product: it does
not rank retailers, combine carts, or silently replace the meal plan with a cheaper one.
The budget remains visible as either a balance or a shortfall.

## Current state

The terminal app understands and completes an English request, allows one field at a
time to be corrected, and supports 1–12 people for 1–14 days. Its rule-based planner
adjusts package quantities and accounts for pantry amounts expressed in kilograms,
grams, litres, cans, dozens, units, and package fractions. The current values come from
one JSON catalog that is explicitly labelled as simulated.

The current terminal pilot accepts only No Frills in Toronto, Ontario. The program
creates three local files when a plan is saved:

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
change its budget calculations.

Project decisions and formats are documented in:

- [`docs/reference-case.md`](docs/reference-case.md)
- [`docs/initial-integration-decision.md`](docs/initial-integration-decision.md)
- [`docs/instacart-list-preparation.md`](docs/instacart-list-preparation.md)
- [`docs/manual-price-observations.md`](docs/manual-price-observations.md)

## Next step

Record one manual No Frills price observation without using it in the plan, validate the
manual iPhone paste flow once, and wait for the Instacart application response.

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
