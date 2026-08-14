# Carrinho quick resume

Use this file when switching ChatGPT or Codex accounts on the same computer.

## Paste this into the new account

```text
Read START_HERE.md first, then inspect the Carrinho Linear project and the single open
issue labelled Next. Tell me the current state and the next small action in Portuguese.
Begin every message with @@. Do not ask me to reconstruct chat context.
Only read HANDOFF.md if you need deeper history.
```

## Local repository

Use the existing folder. Do not clone a second copy on this computer.

```powershell
cd "C:\Users\Admin\OneDrive\Documentos\ChatGPT\Carrinho"
git switch main
git pull --ff-only
git status -sb
git log -1 --oneline
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected current state:

- repository: <https://github.com/thiagoksp/carrinho>
- branch: `main`
- latest merged PR: <https://github.com/thiagoksp/carrinho/pull/29>
- Linear project:
  <https://linear.app/thiagoksp/project/carrinho-instacart-mvp-ad1267b5bbde>
- exactly one Linear issue should have the `Next` label:
  [CAR-14 - Add portable plan and shopping-list exports](https://linear.app/thiagoksp/issue/CAR-14)

## Current product boundary

Carrinho is a local Canadian grocery-planning prototype. It creates one meal plan, one
shopping list, one simulated Canadian planning estimate, and one retailer-neutral
Instacart handoff preview.

Do not add retailer comparison, scraping, checkout automation, live-price claims,
credentials, or network requests unless an approved issue explicitly asks for it.

## Current LLM boundary

CAR-13 is complete. Carrinho has an optional guarded LLM meal selector, disabled by
default. It may return only ordered known meal-template keys through Structured Outputs.
Local code remains authoritative for dietary safety, quantities, package rounding,
pantry deductions, estimates, and final plan generation.

## If more context is needed

Read these in order:

1. `AGENTS.md`
2. `HANDOFF.md`
3. `docs/project-handoff.md`
4. `docs/roadmap.md`
5. the active Linear `Next` issue
