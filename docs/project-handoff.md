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

- Python 3.12 terminal application with no third-party runtime dependencies.
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

If `.venv` does not exist:

```powershell
py -3.12 -m venv .venv
```

## Next single step

Finish and review package reconciliation in Linear issue
[CAR-2](https://linear.app/thiagoksp/issue/CAR-2), the only issue currently labelled
`Next`. The reference output must distinguish recipe need, whole package count,
expected purchased quantity, overage, and variable-weight uncertainty. Do not expand
this into product-by-product or retailer-by-retailer testing.

## Planned sequence after CAR-2

Once CAR-2 is reviewed and merged, promote the next backlog item in this order:

1. [CAR-5 — Externalize the meal catalogue](https://linear.app/thiagoksp/issue/CAR-5).
   Move meal templates and ingredient quantities from code into a validated versioned
   data file.
2. [CAR-6 — Persist household profile and pantry locally](https://linear.app/thiagoksp/issue/CAR-6).
   Store private household defaults and pantry quantities in ignored local JSON, not in
   Git. Do not add a database, account, or network service at this stage.
3. [CAR-7 — Select meals from household constraints](https://linear.app/thiagoksp/issue/CAR-7).
   Make cooking energy, lactose intolerance, and pantry inventory influence the chosen
   meals.
4. [CAR-8 — Expand the curated meal library](https://linear.app/thiagoksp/issue/CAR-8).
   Add variety after the catalogue and selection rules have stable coverage.

The official Instacart validation and API milestones remain externally gated. The
complete ordering is mirrored in [`roadmap.md`](roadmap.md) and Linear.

## Security boundary

- The repository contains no Instacart or OpenAI credential.
- Never commit or paste an API key, token, password, receipt, address, phone number, or
  other personal information.
- `.env` files and generated outputs stay local.
- Do not scrape Instacart or retailer sites, automate login or checkout, bypass CAPTCHA,
  or call private endpoints.
