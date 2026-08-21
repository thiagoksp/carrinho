# Carrinho handoff

Updated: August 19, 2026.

This is the complete project handoff for a new ChatGPT or Codex account. On the same
computer, start with the shorter [`START_HERE.md`](START_HERE.md) file and read this
full handoff only when deeper history is needed.

## Fast message to use in a new chat on the same computer

> Read `START_HERE.md` first, then inspect the Carrinho Linear project and the single
> open issue labelled `Next`. Tell me the current state and the next small action in
> Portuguese. Begin every message with `@@`. Do not ask me to reconstruct chat context.
> Only read `HANDOFF.md` if you need deeper history.

## Full-history message to use in a new chat

> Read `HANDOFF.md` and follow its resume checklist. Then inspect the Carrinho Linear
> project, find the only open issue labelled `Next`, and tell me the current state and
> the next small action in Portuguese. Begin every message with `@@`. Do not implement
> anything until you have checked the repository and the active Linear issue.

Repository: <https://github.com/thiagoksp/carrinho>

Linear project:
<https://linear.app/thiagoksp/project/carrinho-instacart-mvp-ad1267b5bbde>

## Sources of truth

- **This file:** how to resume and the current checkpoint.
- **`START_HERE.md`:** short same-computer resume prompt and commands.
- **Linear:** live task status, ownership, dependencies, and the single `Next` issue.
- **GitHub `main`:** code, tests, documentation, and durable product decisions.
- **`AGENTS.md`:** mandatory collaboration, language, scope, and safety rules.
- **`docs/project-handoff.md`:** detailed implemented state and operating context.
- **`docs/roadmap.md`:** milestone sequence mirrored outside Linear.
- **`docs/legal-ip-checklist.md`:** public-repository, licensing, and future legal
  review checklist.

Do not treat an old chat as authoritative when it conflicts with Linear or GitHub.
Slack and Notion are not project-control tools for Carrinho at this stage.

## Ownership

- Project owner and formal assignee: Thiago (`@tkubrusly`).
- Repository visibility: public for project review, but not open source.

  ## Current checkpoint

  - Active Linear team: Carrinho team with the `CAR` issue prefix.
  - [CAR-58 - Review the full UI of the current Carrinho screen](https://linear.app/thiagoksp/issue/CAR-58/review-the-full-ui-of-the-current-carrinho-screen)
    is the current `Next` issue. It keeps the scope on the current browser flow, audits the
    form, pantry, settings, and generated plan end to end, and identifies the highest-value
    UI improvements without expanding into retailer work or live price data.
  - Current repo status remains aligned with a local-only, retailer-neutral planner. The app
    keeps the browser as the primary surface, no official Instacart API access is enabled,
    and the generated estimates remain clearly labelled as simulated planning ranges.
  - [CAR-32 - Use Carrinho for a real weekly planning run](https://linear.app/thiagoksp/issue/CAR-32)
    is complete and closed after the real planning pass and the follow-up browser UX fixes.
  - [CAR-22 - Simplify first-run household setup](https://linear.app/thiagoksp/issue/CAR-22)
    is complete and was merged through [pull request #32](https://github.com/thiagoksp/carrinho/pull/32).
  - [CAR-14 - Add portable plan and shopping-list exports](https://linear.app/thiagoksp/issue/CAR-14)
    is complete.
  - [CAR-13 - Add an optional guarded LLM meal selector](https://linear.app/thiagoksp/issue/CAR-13)
    is complete.
  - [CAR-57 - Render the structured plan in the browser UI](https://linear.app/thiagoksp/issue/CAR-57)
    is complete. The browser renders the structured plan, shopping list, and estimate view
    with the current local-only model.
  - The current browser pass is deliberately scoped to UX cleanup and local planning quality,
    not retailer integration or live product pricing. The planner may select a validated low-cost noodle meal, but does not  force it into every day; budgets below the floor remain reviewable and show a shortfall.
- [CAR-23](https://linear.app/thiagoksp/issue/CAR-23/use-approved-popularity-and-review-signals-for-product-selection)
  is a future approved-integration task for using product popularity, ratings, review
  feedback, and "most bought" style signals only when that data is contractually
  available. It should help reduce brand decisions without scraping or pretending
  Carrinho knows Instacart ranking data before approval.
- [CAR-24](https://linear.app/thiagoksp/issue/CAR-24/track-meal-history-and-variety-preferences)
  is a future local-history task for reducing repetitive menus. It will track generated
  meals and household feedback so Carrinho can preserve variety over time without
  storing sensitive purchase details.
- [CAR-25](https://linear.app/thiagoksp/issue/CAR-25/verify-codex-and-linear-ownership-before-account-migration)
  is a future human checkpoint for account migration. Use it before relying on a
  different GitHub, Linear, or Codex account so old Julia-linked setup does not confuse
  ownership, permissions, or the single-`Next` workflow.
- [CAR-26](https://linear.app/thiagoksp/issue/CAR-26/design-household-member-dietary-profiles)
  is a future design task for local household member dietary profiles. These profiles
  represent eaters inside one household, not separate login accounts, so a plan can be
  generated for Thiago, Julia, guests, or any selected subset without applying every
  household member's restrictions to every meal plan.
- [CAR-27](https://linear.app/thiagoksp/issue/CAR-27/review-ip-licensing-and-public-repository-protection)
  is complete. The repository stays public for Instacart review, but it now has an
  all-rights-reserved `LICENSE`, a no-outside-contributions policy, an English GitHub
  description, and a legal/IP checklist for future commercialization review.
- [CAR-28](https://linear.app/thiagoksp/issue/CAR-28/evaluate-recipe-sources-and-simplified-recipe-entry)
  is a future recipe-sourcing task. It covers user-entered simplified recipes, a small
  Canadian starter set, possible licensed/API recipe sources, and future LLM-assisted
  parsing into Carrinho's validated generic meal-template schema. Do not scrape recipe
  sites or copy unlicensed recipe content.
- [CAR-12 - Let households edit local meals and generic foods](https://linear.app/thiagoksp/issue/CAR-12)
  is complete. Its implementation was merged as
  [pull request #20](https://github.com/thiagoksp/carrinho/pull/20) on August 14, 2026.
  The local browser now provides a validated private JSON editor for generic foods and
  meal templates, atomic saves, local backups, and restore support without a database,
  account system, retailer SKU, or copied food database.
- [CAR-11 - Add a local browser interface](https://linear.app/thiagoksp/issue/CAR-11)
  is complete. Carrinho now serves a structured form and the generated plan locally at
  `http://127.0.0.1:8765`, without a dependency, credential, or external request.
- [CAR-10 - Separate hard dietary restrictions from soft food preferences](https://linear.app/thiagoksp/issue/CAR-10)
  is complete. Its implementation was merged as
  [pull request #17](https://github.com/thiagoksp/carrinho/pull/17) on August 14, 2026.
  Dietary restrictions remain hard filters; catalogue-backed household tastes are soft
  ranking inputs stored in the private local profile. The future LLM boundary accepts
  ordered known template keys only and performs no network call.
- [CAR-8 - Expand the curated meal library](https://linear.app/thiagoksp/issue/CAR-8)
  is complete. Its implementation was merged as
  [pull request #15](https://github.com/thiagoksp/carrinho/pull/15) on August 14, 2026.
  The catalogue now contains 12 validated templates with stable keys, core/extended
  tiers, and semantic selection tags while preserving the reference case and CAD$58.25
  estimate.
- [CAR-7 - Select meals from household constraints](https://linear.app/thiagoksp/issue/CAR-7)
  is complete. Its implementation was merged as
  [pull request #13](https://github.com/thiagoksp/carrinho/pull/13) on August 14, 2026.
  The selector now filters current lactose-safe templates, prefers the requested cooking
  energy, then uses pantry coverage as a deterministic tie-breaker.
- [CAR-6 - Persist household profile and pantry locally](https://linear.app/thiagoksp/issue/CAR-6)
  is complete. Its implementation was merged as
  [pull request #11](https://github.com/thiagoksp/carrinho/pull/11) on August 14, 2026.
  The optional profile is local, explicit, updateable, and ignored by Git.
- [CAR-5 - Externalize the meal catalogue](https://linear.app/thiagoksp/issue/CAR-5)
  is complete. Its implementation was merged as
  [pull request #9](https://github.com/thiagoksp/carrinho/pull/9) on August 14, 2026.
  The meal catalogue now uses stable generic product keys and structured units, ready
  for a future approved provider without storing retailer data in recipes.
- [CAR-2 - Reconcile recipe quantities with purchasable packages](https://linear.app/thiagoksp/issue/CAR-2)
  is complete. Its implementation was merged as
  [pull request #7](https://github.com/thiagoksp/carrinho/pull/7) on August 14, 2026,
  after local and CI test verification.
- CAR-1 was cancelled because neither **Shopping List -> Paste items** nor
  **Cart Assistant** was available in the project's Canadian Instacart account.
- A limited public Instacart search confirmed that generic product matching can work,
  but package size and variable weight prevent an exact quantity promise. Carrinho is
  not testing every product at every retailer.
- [CAR-3](https://linear.app/thiagoksp/issue/CAR-3/track-instacart-developer-platform-approval)
  tracks the external Instacart approval in parallel and is not on the standalone
  product's critical path.
- [CAR-4](https://linear.app/thiagoksp/issue/CAR-4/implement-the-approved-instacart-development-handoff)
  is blocked by CAR-3.
- The household profile schema is now v2. Version 1 remains readable and loads with
  empty food-preference lists. The current generic catalogue remains deliberately small;
  Carrinho does not copy an exhaustive external food dataset.
- Old `THI-*` work is retained only as completed history or marked as duplicate.
- The Instacart Developer Platform interest form was submitted on August 13, 2026.
  No approval or API key had been received when this file was last updated.
- Julia is no longer used as a secondary collaborator on future Carrinho tasks. CAR-4
  now lists Thiago as the sole owner; older canceled or completed history may still
  mention Julia and should be treated as historical.

## Resume checklist

1. On the same computer, read `START_HERE.md` first. Read this file completely only
   when deeper history is needed.
2. Read `AGENTS.md`, `README.md`, and `docs/project-handoff.md` when the quick resume
   file is not enough.
3. Open the existing local repository; do not create a second copy on the same computer.
4. Check the current branch, local changes, latest commit, and remote state.
5. Open the Linear project and verify that exactly one open issue has the `Next` label.
6. Read that issue completely, including its description, dependencies, labels, and
   recent comments.
7. Run the relevant tests before changing code.
8. Tell the user, in a short Portuguese update beginning with `@@`, what is already
   done, what is next, and whether anything is blocked.
9. Work only on the `Next` issue unless the user explicitly changes priority.

Useful Windows commands:

```powershell
git status -sb
git switch main
git pull --ff-only
git log -1 --oneline
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Product boundary

Carrinho is a Canadian grocery-planning agent. It receives budget, people, days,
cooking energy, pantry items, and dietary restrictions. It produces one meal plan, one
shopping list, one clearly labelled simulated Canadian planning estimate range, and one
retailer-neutral Instacart handoff.

The local browser result supports copying the generated plan, printing a clean plan
page, and downloading the meal plan, Instacart paste list, and Instacart JSON preview.

The browser quick start requires only people and days. Budget, cooking energy, pantry,
and dietary restrictions are optional details. If no budget is provided, Carrinho still
generates a plan and reports the estimated total without a balance or shortfall.

Carrinho does not compare retailers, search for the cheapest basket, claim live prices,
select a retailer, scrape stores, automate checkout, or make network requests without
approved access and contract testing. Actual products, availability, prices, fees, and
checkout remain inside Instacart.

An optional guarded LLM meal selector is available for local experiments. It is disabled
by default, uses Structured Outputs, and can return only ordered known meal-template
keys. Local validation, dietary safety, quantities, packages, and estimates remain
authoritative. Do not store optional LLM prompts, responses, credentials, tokens, or API
keys in GitHub, Linear, chat, logs, or generated outputs.

## Maintenance rule

Before finishing work that changes the project state:

1. update the Linear issue status, evidence, dependencies, and `Next` label;
2. update the current checkpoint in this file when the next issue, external approval,
   ownership, workflow, or product direction changes;
3. update `docs/roadmap.md` when milestone ordering changes;
4. keep documentation and code in Canadian English;
5. publish tested changes through the repository workflow;
6. leave no secrets, personal addresses, receipts, phone numbers, passwords, tokens,
   or API keys in GitHub, Linear, generated files, or chat.
