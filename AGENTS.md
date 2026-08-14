# Carrinho project instructions

## Goal

Build Carrinho step by step: a Canadian grocery agent that receives a budget, number of
days and people, cooking energy, pantry items, and dietary restrictions. It produces one
meal plan, one shopping list, one clearly labelled simulated Canadian planning estimate
per item, and one reviewable Instacart handoff.

Instacart is the planned shopping platform, not a retailer. Carrinho does not choose or
guarantee a merchant. The user's address, available retailers, product availability, and
actual prices are handled inside Instacart during the handoff.

Carrinho is not a price-comparison product. Do not rank retailers, combine stores, search
for the cheapest basket, or silently replace the requested plan with a cheaper menu.

## Working style

- Advance in small steps and explain them in accessible language.
- Minimize the number of decisions presented to the user.
- Verify the result of each stage before starting the next one.
- Do not implement features beyond the requested stage.
- Do not add libraries, services, plugins, or infrastructure without a concrete need.
- Prefer simplicity and ease of learning over premature architecture.

## Language and naming

- Converse with the user in Portuguese and begin every assistant message with `@@`.
- Documentation, filenames, modules, identifiers, schemas, CLI commands, generated
  filenames, tests, and user-visible output must use Canadian English.
- Docstrings must be in English.
- Code comments may be in Portuguese, but every code comment must begin with `# @@`.
- Keep `Carrinho` as the project name.

## Current scope

The interface is a terminal app. A rule-based planner supports 1–12 people for 1–14
days, package-aware pantry deductions, a budget balance or shortfall, and one
retailer-neutral simulated Canadian price catalog. The request and planning models do
not require a city or retailer.

The app saves a meal plan, an Instacart JSON preview, and a plain-text list for the
manual iPhone **Paste items** flow. It performs no network request and uses no
credential. The former No Frills and Toronto pilot and its manual-price research tool
have been removed from the active product; the superseded decision remains in the
documentation as history.

An Instacart Developer Platform interest form was submitted on August 13, 2026. As of
August 14, 2026, no approval or API key has been received. Only no dietary restrictions
or lactose intolerance are supported at this stage.

## Roadmap

1. Understand the household request.
2. Produce one meal plan and shopping list.
3. Attach one Canadian planning estimate per item from one clearly labelled catalog.
4. Prepare one retailer-neutral Instacart preview and manual paste list.
5. Validate product matching through the manual Instacart flow and improve generic
   search terms only from observed results.
6. Enable an official handoff only after approved access and contract testing.
7. Treat retailer-specific availability and actual prices as Instacart-owned results.
