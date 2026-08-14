# Carrinho

> Changing ChatGPT or Codex accounts? Start with [`HANDOFF.md`](HANDOFF.md).

Carrinho is a Canadian grocery-planning agent designed to reduce the decisions between
"we need food" and "the cart is ready to review."

## Product direction

The user describes a household situation in natural language:

- available budget in Canadian dollars;
- number of people and days;
- cooking energy;
- food already available at home;
- dietary restrictions.

Carrinho produces one practical meal plan, one shopping list, and one simulated Canadian
planning estimate per item. It is useful as a standalone local application. Instacart is
an optional future shopping handoff, not a retailer selected by Carrinho. The user would
choose an available retailer inside Instacart, where address-specific availability and
actual prices are determined.

Carrinho is not a store or price comparison product: it does not rank retailers, combine
carts, or silently replace the meal plan with a cheaper one. The budget remains visible
as either a balance or a shortfall.

## Current state

The terminal app and local browser interface support 1-12 people for 1-14 days. The
browser provides a structured form, friendly validation, and the complete plan on one
page at `http://127.0.0.1:8765`. The terminal interface remains available for natural
language requests and one-field-at-a-time corrections. The rule-based planner
separates recipe requirements from whole purchasable packages, reports expected
overage, marks variable-weight products as approximate, and accounts for pantry amounts
expressed in kilograms, grams, pounds, litres, millilitres, cans, dozens, units, and
package fractions. Mass is normalized to grams and volume to millilitres before package
rounding. The current values come from
one retailer-neutral JSON catalog that is explicitly labelled as simulated. A planning
request does not require a city or retailer.

Dietary restrictions are hard safety filters. Foods the household avoids or prefers are
separate soft ranking inputs backed by the existing generic product keys. The built-in
vocabulary remains deliberately small, and a household can save its own selections in
the private local profile without Carrinho copying a large external food database.

The local browser also includes a validated JSON editor for private generic foods and
meal templates. Local extensions use stable text keys, stay under ignored `local-data/`,
create a backup before replacement, and never replace the versioned starter catalogue.

An optional guarded LLM meal selector is available for experiments. It is disabled by
default, uses Structured Outputs when enabled, and can return only ordered known
meal-template keys. Local validation, dietary safety, pantry deductions, package
rounding, and cost estimates remain deterministic and authoritative.

The program creates three local files when a plan is saved:

- a readable meal plan;
- an Instacart JSON preview for a future approved integration;
- a plain-text list for manually testing the iPhone **Shopping List -> Paste items** flow.

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
- [`LICENSE`](LICENSE), the all-rights-reserved project notice
- [`CONTRIBUTING.md`](CONTRIBUTING.md), the current no-outside-contributions policy
- [`docs/reference-case.md`](docs/reference-case.md)
- [`docs/instacart-platform-direction.md`](docs/instacart-platform-direction.md)
- [`docs/instacart-list-preparation.md`](docs/instacart-list-preparation.md)
- [`docs/local-household-data.md`](docs/local-household-data.md)
- [`docs/local-catalogue.md`](docs/local-catalogue.md)
- [`docs/meal-catalogue.md`](docs/meal-catalogue.md)
- [`docs/llm-meal-selector.md`](docs/llm-meal-selector.md)
- [`docs/legal-ip-checklist.md`](docs/legal-ip-checklist.md)
- [`docs/project-handoff.md`](docs/project-handoff.md)
- [`docs/roadmap.md`](docs/roadmap.md)
- [`docs/initial-integration-decision.md`](docs/initial-integration-decision.md), retained
  as a superseded historical decision

## License and contributions

Carrinho is publicly visible for project review and development transparency, but it is
not open source. All rights are reserved. See [`LICENSE`](LICENSE).

Outside contributions are not accepted yet. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Next step

[CAR-14](https://linear.app/thiagoksp/issue/CAR-14) will add portable, reviewable plan
and shopping-list exports. Instacart approval is tracked separately in CAR-3; all
official shopping network integration stays disabled until approved access and contract
testing are available.

Task status is tracked in the
[Carrinho Linear project](https://linear.app/thiagoksp/project/carrinho-instacart-mvp-ad1267b5bbde).
The single next task is also mirrored in [`docs/roadmap.md`](docs/roadmap.md) for
cross-account continuity.

## Local environment

The project uses Python 3.12 and currently has no third-party runtime dependencies.

The optional LLM selector also uses the Python standard library. It stays off unless
`CARRINHO_LLM_SELECTOR_ENABLED=1` and a local `OPENAI_API_KEY` are set in the current
shell. See [`docs/llm-meal-selector.md`](docs/llm-meal-selector.md).

Run Carrinho on Windows:

```powershell
.\.venv\Scripts\python.exe app.py
```

Run the local browser interface:

```powershell
.\.venv\Scripts\python.exe web_app.py
```

Then open <http://127.0.0.1:8765>. Press `Ctrl+C` in the terminal to stop it.

Run the test suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
