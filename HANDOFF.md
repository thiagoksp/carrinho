# Carrinho handoff

Updated: August 14, 2026.

This is the single starting point for a new ChatGPT or Codex account. Read this file
before asking the user to repeat project context.

## Message to use in a new chat

> Read `HANDOFF.md` and follow its resume checklist. Then inspect the Carrinho Linear
> project, find the only open issue labelled `Next`, and tell me the current state and
> the next small action in Portuguese. Begin every message with `@@`. Do not implement
> anything until you have checked the repository and the active Linear issue.

Repository: <https://github.com/thiagoksp/carrinho>

Linear project:
<https://linear.app/thiagoksp/project/carrinho-instacart-mvp-ad1267b5bbde>

## Sources of truth

- **This file:** how to resume and the current checkpoint.
- **Linear:** live task status, ownership, dependencies, and the single `Next` issue.
- **GitHub `main`:** code, tests, documentation, and durable product decisions.
- **`AGENTS.md`:** mandatory collaboration, language, scope, and safety rules.
- **`docs/project-handoff.md`:** detailed implemented state and operating context.
- **`docs/roadmap.md`:** milestone sequence mirrored outside Linear.

Do not treat an old chat as authoritative when it conflicts with Linear or GitHub.
Slack and Notion are not project-control tools for Carrinho at this stage.

## Ownership

- Project owner and formal assignee: Thiago (`@tkubrusly`).

## Current checkpoint

- Active team: `🛒 Carrinho`.
- Active issue prefix: `CAR`.
- Exactly one issue is labelled `Next`:
  [CAR-6 — Persist household profile and pantry locally](https://linear.app/thiagoksp/issue/CAR-6).
  It is in progress and assigned to Thiago. Start with an explicit, privacy-focused
  local JSON save and update flow outside Git; do not add a database, account, or
  network service.
- [CAR-5 — Externalize the meal catalogue](https://linear.app/thiagoksp/issue/CAR-5)
  is complete. Its implementation was merged as
  [pull request #9](https://github.com/thiagoksp/carrinho/pull/9) on August 14, 2026.
  The meal catalogue now uses stable generic product keys and structured units, ready
  for a future approved provider without storing retailer data in recipes.
- [CAR-2 — Reconcile recipe quantities with purchasable packages](https://linear.app/thiagoksp/issue/CAR-2)
  is complete. Its implementation was merged as
  [pull request #7](https://github.com/thiagoksp/carrinho/pull/7) on August 14, 2026,
  after local and CI test verification.
- CAR-1 was cancelled because neither **Shopping List → Paste items** nor
  **Cart Assistant** was available in the project's Canadian Instacart account.
- A limited public Instacart search confirmed that generic product matching can work,
  but package size and variable weight prevent an exact quantity promise. Carrinho is
  not testing every product at every retailer.
- [CAR-3](https://linear.app/thiagoksp/issue/CAR-3/track-instacart-developer-platform-approval)
  tracks the external Instacart approval.
- [CAR-4](https://linear.app/thiagoksp/issue/CAR-4/implement-the-approved-instacart-development-handoff)
  is blocked by CAR-3.
- The remaining product sequence is [CAR-7](https://linear.app/thiagoksp/issue/CAR-7),
  then [CAR-8](https://linear.app/thiagoksp/issue/CAR-8): select meals from household
  constraints, then expand the curated meal library. These changes do not require a
  database, account, or network service.
- Old `THI-*` work is retained only as completed history or marked as duplicate.
- The Instacart Developer Platform interest form was submitted on August 13, 2026.
  No approval or API key had been received when this file was last updated.

## Resume checklist

1. Read this file completely.
2. Read `AGENTS.md`, `README.md`, and `docs/project-handoff.md`.
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
shopping list, one clearly labelled simulated Canadian planning estimate, and one
retailer-neutral Instacart handoff.

Carrinho does not compare retailers, search for the cheapest basket, claim live prices,
select a retailer, scrape stores, automate checkout, or make network requests without
approved access and contract testing. Actual products, availability, prices, fees, and
checkout remain inside Instacart.

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

