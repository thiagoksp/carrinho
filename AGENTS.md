# Carrinho project instructions

## Goal

Build Carrinho step by step: a Canadian grocery agent that receives a budget, number of
days and people, cooking energy, pantry items, dietary restrictions, shopping area, and
one selected store. It produces one meal plan, one shopping list, one selected working
price per item, and one reviewable cart handoff.

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

- Documentation, filenames, modules, identifiers, schemas, CLI commands, generated
  filenames, tests, and user-visible output must use Canadian English.
- Docstrings must be in English.
- Code comments may be in Portuguese, but every code comment must begin with `# @@`.
- Keep `Carrinho` as the project name.

## Current scope

The interface is a terminal app. A rule-based planner supports 1–12 people for 1–14
days, package-aware pantry deductions, a budget balance or shortfall, and a single
simulated price catalog. This version accepts only No Frills in Toronto. The app saves a
meal plan, an Instacart JSON preview, and a plain-text list for the manual iPhone
**Paste items** flow. It performs no network request and uses no credential.

An Instacart Developer Platform interest form was submitted on August 13, 2026, but no
approval or API key has been received. Manual price observations remain local,
self-declared, unverified, and isolated from planning. Only no dietary restrictions or
lactose intolerance are supported at this stage.

## Roadmap

1. Understand the household request.
2. Produce one meal plan and shopping list.
3. Attach one selected working price per item from the chosen retailer and location.
4. Produce one reviewable cart handoff.
5. Enable an official cart integration only after approved access and contract testing.
