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
7. [`llm-meal-selector.md`](llm-meal-selector.md)
8. [`roadmap.md`](roadmap.md)

## Source of truth

Continue from the current `main` branch of the public repository:

<https://github.com/thiagoksp/carrinho>

Do not restart from an earlier conversation or rebuild completed work. The expected
handoff state is a clean `main` branch with all tests passing.

The repository is public for project review and development transparency, but Carrinho
is not open source. All rights are reserved under [`LICENSE`](../LICENSE), and outside
contributions are not accepted yet under [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Stable product decisions

- Carrinho serves the Canadian market and uses CAD.
- The user provides people, days, and optional budget, cooking energy, pantry items, and dietary
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
- The browser server binds only to `127.0.0.1`, provides a quick-start form for people
  and days, keeps budget and other details optional, and renders the complete plan on
  one page without an external request.
- The planner supports 1-12 people for 1-14 days.
- Package-aware pantry deductions and lactose intolerance are supported within the
  documented limits.
- Recipe quantities and purchasable quantities are separate. Mass is normalized to
  grams, volume to millilitres, and discrete products to compatible counts. Fixed-size
  products round up to whole packages and expose expected overage; variable-weight
  products are explicitly approximate.
- The local price catalog is simulated and retailer-neutral.
- The request, plan, summary, and saved files contain no city or selected retailer.
- If no budget is provided, Carrinho still generates a plan and shows the estimated total
  without a balance or shortfall.
- Saving a plan creates:
  - `meal-plan.txt`;
  - `instacart-list.json`;
  - `instacart-paste-list.txt`.
- The browser result can copy the generated plan, print a clean plan page, and download
  the meal plan, Instacart paste list, and Instacart JSON preview from the local page.
- Generated files remain local and are excluded from Git.
- A validated browser editor can extend generic foods and meal templates in ignored
  `local-data/custom-catalogue.json`. Valid replacements create a local backup, and the
  latest backup can be restored without changing the built-in starter catalogue.
- An optional guarded LLM meal selector can be enabled through local environment
  variables. It uses the OpenAI Responses API target `gpt-5.6-luna`, Structured Outputs,
  and returns only ordered known meal-template keys. It is disabled by default, stores no
  prompt or response, and never overrides local dietary validation, quantity
  calculation, package rounding, or estimates.
- No network request is made and no API key is required unless the optional LLM selector
  is explicitly enabled in the local shell.
- The former No Frills and Toronto pilot and manual-price experiment have been removed
  from the active product. Their rationale remains available in Git history and the
  superseded decision record.

## External Instacart status

Carrinho submitted the Canadian Instacart Developer Platform interest form on
August 13, 2026. As of August 14, 2026, no approval or API key has been received.

The documented iPhone **Shopping List -> Paste items** flow and **Cart Assistant** were
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

Continue [CAR-22](https://linear.app/thiagoksp/issue/CAR-22/simplify-first-run-household-setup),
the only issue labelled `Next`. Simplify first-run household setup so Carrinho stays
easy to try before asking for richer rules. CAR-3 continues to track Instacart approval
in parallel.

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
August 14, 2026. Supported dietary restrictions remain hard filters. Foods to use less
or more often are separate soft ranking inputs resolved through existing generic
product keys and optionally saved in private household profile schema v2. The catalogue
remains small, unknown foods are reported rather than guessed, and version 1 profiles
remain readable.

CAR-12 was merged as [pull request #20](https://github.com/thiagoksp/carrinho/pull/20)
on August 14, 2026. Households can extend generic foods and meal templates through a
validated private JSON editor. Local entries cannot replace built-in keys, valid
replacements create restorable backups, and the starter catalogues remain versioned and
unchanged.

CAR-13 added the optional guarded LLM selector. The selector is off by default, uses
Structured Outputs when enabled, sends only a bounded candidate set, and validates every
returned key locally before generating a plan. The default OpenAI model is
`gpt-5.6-luna`, but the provider/model adapter keeps the production boundary ready for
CAR-15 provider comparison.

CAR-14 added portable browser exports. The standalone page now provides copy, print,
meal-plan download, Instacart paste-list download, and Instacart JSON preview download
without sending any request to Instacart or another service.

CAR-22 is in progress locally. The browser quick start now requires only people and days;
budget is optional; neutral defaults avoid assuming lactose intolerance or pantry items;
and `Foods to use more/less often` has been removed from the main browser form pending
the CAR-18 household-rules redesign.

The official Instacart validation and API milestones remain externally gated. The
complete ordering is mirrored in [`roadmap.md`](roadmap.md) and Linear.

## Security boundary

- The repository contains no Instacart or OpenAI credential.
- The repository is public but not open source; do not add an open-source license unless
  the owner explicitly changes that decision.
- Never commit or paste an API key, token, password, receipt, address, phone number, or
  other personal information.
- `.env` files and generated outputs stay local.
- Do not log or commit optional LLM prompts, responses, API keys, or household secrets.
- Do not scrape Instacart or retailer sites, automate login or checkout, bypass CAPTCHA,
  or call private endpoints.
