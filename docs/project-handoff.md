# Carrinho project handoff

Updated: August 14, 2026.

This file preserves the project state when work moves to another ChatGPT or Codex
account. The repository, not a previous conversation, is the source of truth.

The single cross-account starting point is [`HANDOFF.md`](../HANDOFF.md). This document
provides the more detailed implementation context referenced from that file.

## Read first

1. [`HANDOFF.md`](../HANDOFF.md)
2. [`AGENTS.md`](../AGENTS.md)
3. [`README.md`](../README.md)
4. [`instacart-platform-direction.md`](instacart-platform-direction.md)
5. [`reference-case.md`](reference-case.md)
6. [`instacart-list-preparation.md`](instacart-list-preparation.md)
7. [`roadmap.md`](roadmap.md)

## Source of truth

Continue from the current `main` branch of the public repository:

<https://github.com/thiagoksp/carrinho>

Do not restart from an earlier conversation or rebuild completed work. The expected
handoff state is a clean `main` branch with all tests passing.

## Stable product decisions

- Carrinho serves the Canadian market and uses CAD.
- The user provides budget, people, days, cooking energy, pantry items, and dietary
  restrictions.
- Carrinho creates one meal plan, one shopping list, and one clearly labelled simulated
  Canadian planning estimate.
- Carrinho does not request or select a city or retailer.
- Instacart is the planned shopping platform, not a retailer.
- The user selects an available retailer inside Instacart.
- Carrinho does not compare retailers, search for the cheapest basket, or combine carts.
- Actual products, availability, retailer prices, fees, and checkout remain inside
  Instacart.
- Network integration and checkout automation remain disabled.

When collaborating with the user, converse in Portuguese and begin every assistant
message with `@@`. Keep code, identifiers, documentation, tests, filenames, schemas,
and user-visible output in Canadian English.

## Implemented state

- Python 3.12 terminal and local browser interfaces with no third-party runtime
  dependencies.
- The browser server binds only to `127.0.0.1`, provides a structured form, and renders
  the complete plan on one page without an external request.
- The planner supports 1–12 people for 1–14 days.
- Package-aware pantry deductions and lactose intolerance are supported within the
  documented limits.
- Recipe quantities and purchasable quantities are separate. Mass is normalized to
  grams, volume to millilitres, and discrete products to compatible counts. Fixed-size
  products round up to whole packages and expose expected overage; variable-weight
  products are explicitly approximate.
- The local price catalog is simulated and retailer-neutral.
- The request, plan, summary, and saved files contain no city or selected retailer.
- Saving a plan creates:
  - `meal-plan.txt`;
  - `instacart-list.json`;
  - `instacart-paste-list.txt`.
- Generated files remain local and are excluded from Git.
- No network request is made and no API key is required.
- The former No Frills and Toronto pilot and manual-price experiment have been removed
  from the active product. Their rationale remains available in Git history and the
  superseded decision record.

## External Instacart status

Carrinho submitted the Canadian Instacart Developer Platform interest form on
August 13, 2026. As of August 14, 2026, no approval or API key has been received.

The documented iPhone **Shopping List → Paste items** flow and **Cart Assistant** were
not available in the project's Canadian Instacart account on August 14, 2026. A limited
public Instacart search was used only to confirm the package-size problem; it is not a
catalogue, retailer comparison, or network integration in Carrinho. Do not add a network
request until approved access exists and the development contract has been tested.

The [Carrinho Linear project](https://linear.app/thiagoksp/project/carrinho-instacart-mvp-ad1267b5bbde)
tracks task status. Its essential roadmap is mirrored in [`roadmap.md`](roadmap.md) so
continuity does not depend on one connected account. Slack and Notion are not used for
project control at this stage.

## Resume on the same computer

Open the existing `carrinho` folder. Do not clone a second copy.

```powershell
git status -sb
git switch main
git pull --ff-only
git log -1 --oneline
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run Carrinho:

```powershell
.\.venv\Scripts\python.exe app.py
```

Run the local browser interface:

```powershell
.\.venv\Scripts\python.exe web_app.py
```

Open <http://127.0.0.1:8765> and press `Ctrl+C` in the terminal to stop it.

If `.venv` does not exist:

```powershell
py -3.12 -m venv .venv
```

## Next single step

Continue [CAR-12](https://linear.app/thiagoksp/issue/CAR-12), the only issue labelled
`Next`. Add a validated local editing or import workflow for household meal templates
and generic foods. Do not add a database, account system, retailer SKU, or large copied
food dataset. CAR-3 continues to track Instacart approval in parallel.

## Current deterministic selection

CAR-7 was merged as [pull request #13](https://github.com/thiagoksp/carrinho/pull/13) on
August 14, 2026. Current lactose intolerance is filtered through validated catalogue
tags. For plans shorter than the eligible library, Carrinho chooses the closest cooking
energy and then uses pantry coverage as a stable tie-breaker. When a plan needs every
eligible template, catalogue order preserves the reference case.

CAR-8 was merged as [pull request #15](https://github.com/thiagoksp/carrinho/pull/15) on
August 14, 2026. The catalogue now contains 12 validated templates with stable keys,
core/extended tiers, and semantic selection tags. A future LLM may suggest ordered known
template keys only; Carrinho validates the candidates and deterministically calculates
restrictions, quantities, packages, and estimates.

CAR-10 was merged as [pull request #17](https://github.com/thiagoksp/carrinho/pull/17) on
August 14, 2026. Supported dietary restrictions remain hard filters. Foods to avoid or
prefer are separate soft ranking inputs resolved through the existing generic product
keys and optionally saved in private household profile schema v2. The catalogue remains
small, unknown foods are reported rather than guessed, and version 1 profiles remain
readable.

The official Instacart validation and API milestones remain externally gated. The
complete ordering is mirrored in [`roadmap.md`](roadmap.md) and Linear.

## Security boundary

- The repository contains no Instacart or OpenAI credential.
- Never commit or paste an API key, token, password, receipt, address, phone number, or
  other personal information.
- `.env` files and generated outputs stay local.
- Do not scrape Instacart or retailer sites, automate login or checkout, bypass CAPTCHA,
  or call private endpoints.
