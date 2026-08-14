# Carrinho project instructions

## Start here

At the beginning of every new account or conversation, read `HANDOFF.md` completely.
Then inspect the Carrinho Linear project and the single open issue labelled `Next`
before proposing or implementing work. Do not ask the user to reconstruct context that
is already available in GitHub or Linear.

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

The product has a terminal interface and a local browser interface bound to
`127.0.0.1`. A rule-based planner supports 1–12 people for 1–14 days, package-aware
pantry deductions, a budget balance or shortfall, and one
retailer-neutral simulated Canadian price catalog. Recipe need is separate from
purchasable quantity: mass is normalized to grams, volume to millilitres, fixed-size
products round up to whole packages, and variable-weight products remain approximate.
The request and planning models do not require a city or retailer.

The app saves a meal plan, an Instacart JSON preview, and a plain-text list for the
manual iPhone **Paste items** flow. It performs no network request and uses no
credential. The former No Frills and Toronto pilot and its manual-price research tool
have been removed from the active product; the superseded decision remains in the
documentation as history.

An Instacart Developer Platform interest form was submitted on August 13, 2026. As of
August 14, 2026, no approval or API key has been received. The documented iPhone
**Paste items** flow and **Cart Assistant** were not available in the project's Canadian
Instacart account, so they are not current milestone dependencies. Only no dietary
restrictions or lactose intolerance are supported as hard dietary rules at this stage.
Catalogue-backed foods to avoid or prefer are separate soft ranking inputs that can be
saved in the private local household profile.

## Roadmap

Task status is tracked in the Carrinho Linear project and mirrored in
`docs/roadmap.md`. Work only on the single issue labelled `Next` unless the user
explicitly changes priority. Keep GitHub as the source of code and durable decisions.

1. Understand the household request.
2. Produce one meal plan and shopping list.
3. Attach one Canadian planning estimate per item from one clearly labelled catalog.
4. Provide a usable standalone local browser interface.
5. Let households edit local meals and generic foods through validated workflows.
6. Add an optional guarded LLM selector that returns known meal-template keys only.
7. Add portable, reviewable exports.
8. Enable an official Instacart handoff only after approved access and contract testing.

## Handoff maintenance

Before completing work that changes project state, update Linear first. Update
`HANDOFF.md` whenever the next issue, external approval, ownership, workflow, or product
direction changes. Update `docs/roadmap.md` when milestone ordering changes. The goal is
that a different account can resume from GitHub and Linear without relying on chat
history.
