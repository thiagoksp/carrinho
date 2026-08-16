# Carrinho start here

This is the single entry point for a new ChatGPT/Codex account or a new machine.
Read this file first. It points to everything else.

## Paste this into the new AI

```text
Read START_HERE.md completely first.
Then inspect the Carrinho Linear project and find the single open issue labelled Next.
Tell me the current state and the next small action in Portuguese.
Begin every message with @@.
Do not ask me to reconstruct chat context.
Use GitHub main and Linear as the source of truth.
Read HANDOFF.md only when deeper history is needed.
```

## Repository

Repository: <https://github.com/thiagoksp/carrinho>

On a new machine:

```powershell
git clone https://github.com/thiagoksp/carrinho.git
cd carrinho
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

On this computer, use the existing folder. Do not clone a second copy.

```powershell
cd "C:\Users\Admin\OneDrive\Documentos\ChatGPT\Carrinho"
git switch main
git pull --ff-only
git status -sb
git log -1 --oneline
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Expected current state:

- repository: <https://github.com/thiagoksp/carrinho>
- branch: `main`
- latest merged PR before this handoff: PR #32, `Simplify browser quick start`
- Linear project:
  <https://linear.app/thiagoksp/project/carrinho-instacart-mvp-ad1267b5bbde>
- exactly one Linear issue should have the `Next` label:
  [CAR-32 - Use Carrinho for a real weekly planning run](https://linear.app/thiagoksp/issue/CAR-32)

## How the user likes to work

- Speak Portuguese with the user and begin every assistant message with `@@`.
- Keep code, docs, tests, filenames, schemas, and user-visible product text in Canadian
  English.
- Move in small steps. Discuss first when the product direction is fuzzy; act decisively
  when the slice is approved.
- Keep Linear organized. The user does not want to lose the thread.
- Do not overbuild. The user wants Carrinho to become useful quickly, not to drown in
  architecture.
- When the user asks for credit economy, follow [`AI_RULES.md`](AI_RULES.md).
- Do not update handoff files for every micro-step. Update them when switching accounts,
  changing the `Next` issue, consolidating to Git, or making a major product decision.

## Current product boundary

Carrinho is a local Canadian grocery-planning prototype. It creates one meal plan, one
shopping list, one simulated Canadian planning estimate range, and one retailer-neutral
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

## Next action

Start with CAR-32. The goal is to use Carrinho for one real weekly planning run, find
only the blockers that prevent practical use, and make the smallest useful fixes. Do not
resume Instacart API work unless CAR-3 changes state.
