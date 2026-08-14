# Carrinho roadmap

Updated: August 14, 2026.

## Tracking decision

Carrinho uses a deliberately small tool set:

- [Linear](https://linear.app/thiagoksp/project/carrinho-instacart-mvp-ad1267b5bbde)
  tracks what is next, in progress, blocked, or done;
- [GitHub](https://github.com/thiagoksp/carrinho) stores code, tests, pull requests,
  and durable product decisions;
- Slack is not a task tracker and is not needed at this stage;
- Notion is not needed while the repository documentation remains sufficient.

The roadmap is mirrored here so another ChatGPT or Codex account can recover the
project direction before its Linear connection is configured.

Start a new account or conversation with [`HANDOFF.md`](../HANDOFF.md). Linear remains
authoritative for live task status.

## Operating rule

Exactly one open issue should have the `Next` label. Finish or deliberately cancel
that issue before promoting another one. Every code change should reference its Linear
issue and be published through a tested GitHub pull request.

At the start of a work session:

1. read `HANDOFF.md`, `AGENTS.md`, and `docs/project-handoff.md`;
2. open the Linear project;
3. work only on the issue labelled `Next` unless the user explicitly changes priority;
4. update the issue with evidence and move its status when the work changes state.

## Milestone 1 — Reconcile planned quantities with packages

**Complete:** [CAR-2 — Reconcile recipe quantities with purchasable
packages](https://linear.app/thiagoksp/issue/CAR-2), merged through
[pull request #7](https://github.com/thiagoksp/carrinho/pull/7) on August 14, 2026.

Keep recipe requirements separate from purchasable quantities. Normalize compatible
mass, volume, and discrete units; round fixed-size products up to whole packages; show
expected overage; and mark variable-weight products as estimates. Keep the catalogue
simulated and retailer-neutral.

## Milestone 2 — Data-driven households

The next product milestone makes the planner adaptable without adding a database,
account system, or network service.

**Complete:** [CAR-5 — Externalize the meal catalogue](https://linear.app/thiagoksp/issue/CAR-5),
merged through [pull request #9](https://github.com/thiagoksp/carrinho/pull/9) on
August 14, 2026.

It moves meal templates and per-person ingredient quantities from Python into a
validated, versioned Canadian English data file. The catalogue uses stable generic
product keys and structured units shared with the price catalogue.

**Complete:** [CAR-6 — Persist household profile and pantry locally](https://linear.app/thiagoksp/issue/CAR-6),
merged through [pull request #11](https://github.com/thiagoksp/carrinho/pull/11) on
August 14, 2026.

It saves optional household defaults and pantry quantities in private local JSON outside
Git. The user explicitly chooses to use or update it; budget, days, address, retailer,
receipts, and credentials are not stored.

**Next, in progress:** [CAR-7 — Select meals from household constraints](https://linear.app/thiagoksp/issue/CAR-7)
   makes cooking energy, lactose intolerance, and pantry inventory influence
   deterministic meal selection while preserving the reference case.

Then complete the remaining backlog item:

1. [CAR-8 — Expand the curated meal library](https://linear.app/thiagoksp/issue/CAR-8)
   adds tested meal variety only after the catalogue and selection rules are stable.

CAR-7 is the sole `Next` issue. The remaining work stays in backlog until it is
promoted.

## Milestone 3 — Validate an available official handoff

CAR-1 was cancelled after the project's Canadian account did not expose either the
documented iPhone **Shopping List → Paste items** flow or **Cart Assistant**. A limited
public product search was enough to identify package reconciliation as the useful
generic problem; Carrinho will not test every product across multiple retailers.

Resume handoff validation only when an official Instacart surface is available. Change
generic search terms or structured measurements only from observed evidence, add
regression tests, and keep the output retailer-neutral.

## Milestone 4 — Official API integration

**External dependency:** [CAR-3 — Track Instacart Developer Platform
approval](https://linear.app/thiagoksp/issue/CAR-3/track-instacart-developer-platform-approval)

**Blocked by CAR-3:** [CAR-4 — Implement the approved Instacart development
handoff](https://linear.app/thiagoksp/issue/CAR-4/implement-the-approved-instacart-development-handoff)

Network behaviour remains disabled until Instacart approves access and the development
contract is reviewed. Never store an API key in Linear, GitHub, chat, logs, or generated
project files.

## Product boundaries

- one meal plan and one shopping-list handoff;
- Canada and CAD;
- retailer selection, availability, actual prices, fees, and checkout stay in Instacart;
- no retailer comparison, scraping, checkout automation, or live-price claim;
- no new platform or service without a concrete project need.
