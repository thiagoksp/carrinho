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

The current handoff is the manual iPhone **Shopping List → Paste items** flow. Do not
add a network request until approved access exists and the development contract has
been tested.

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

Run the approved reference case, inspect all three generated files, and manually test
`instacart-paste-list.txt` with Instacart's iPhone **Paste items** flow.

This work is tracked as Linear issue
[CAR-1](https://linear.app/thiagoksp/issue/CAR-1/validate-the-reference-list-in-instacart-paste-items),
the only issue currently labelled `Next`.

Record only product-matching or quantity problems observed during that test. Improve
the generic Instacart search terms from evidence before adding another feature.

## Security boundary

- The repository contains no Instacart or OpenAI credential.
- Never commit or paste an API key, token, password, receipt, address, phone number, or
  other personal information.
- `.env` files and generated outputs stay local.
- Do not scrape Instacart or retailer sites, automate login or checkout, bypass CAPTCHA,
  or call private endpoints.
