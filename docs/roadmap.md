# Carrinho roadmap

Updated: August 16, 2026.

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

Start a new account, conversation, or machine with [`START_HERE.md`](../START_HERE.md).
Linear remains authoritative for live task status.

## Operating rule

Exactly one open issue should have the `Next` label. Finish or deliberately cancel
that issue before promoting another one. Every code change should reference its Linear
issue and be published through a tested GitHub pull request.

At the start of a work session:

1. read `START_HERE.md`, `AGENTS.md`, and `docs/project-handoff.md`;
2. open the Linear project;
3. work only on the issue labelled `Next` unless the user explicitly changes priority;
4. update the issue with evidence and move its status when the work changes state.

## Milestone 1 - Reconcile planned quantities with packages

**Complete:** [CAR-2 - Reconcile recipe quantities with purchasable
packages](https://linear.app/thiagoksp/issue/CAR-2), merged through
[pull request #7](https://github.com/thiagoksp/carrinho/pull/7) on August 14, 2026.

Keep recipe requirements separate from purchasable quantities. Normalize compatible
mass, volume, and discrete units; round fixed-size products up to whole packages; show
expected overage; and mark variable-weight products as estimates. Keep the catalogue
simulated and retailer-neutral.

## Milestone 2 - Data-driven households

The next product milestone makes the planner adaptable without adding a database,
account system, or network service.

**Complete:** [CAR-5 - Externalize the meal catalogue](https://linear.app/thiagoksp/issue/CAR-5),
merged through [pull request #9](https://github.com/thiagoksp/carrinho/pull/9) on
August 14, 2026.

It moves meal templates and per-person ingredient quantities from Python into a
validated, versioned Canadian English data file. The catalogue uses stable generic
product keys and structured units shared with the price catalogue.

**Complete:** [CAR-6 - Persist household profile and pantry locally](https://linear.app/thiagoksp/issue/CAR-6),
merged through [pull request #11](https://github.com/thiagoksp/carrinho/pull/11) on
August 14, 2026.

It saves optional household defaults and pantry quantities in private local JSON outside
Git. The user explicitly chooses to use or update it; budget, days, address, retailer,
receipts, and credentials are not stored.

**Complete:** [CAR-7 - Select meals from household constraints](https://linear.app/thiagoksp/issue/CAR-7),
merged through [pull request #13](https://github.com/thiagoksp/carrinho/pull/13) on
August 14, 2026.

It makes cooking energy, lactose intolerance, and pantry inventory influence
deterministic meal selection while preserving the reference case. Lactose-safe catalogue
tags are a hard filter; energy and pantry coverage rank shorter plans predictably.

**Complete:** [CAR-8 - Expand the curated meal library](https://linear.app/thiagoksp/issue/CAR-8),
merged through [pull request #15](https://github.com/thiagoksp/carrinho/pull/15) on
August 14, 2026.

It expands the catalogue from 8 to 12 validated templates with stable keys,
core/extended tiers, and semantic selection tags. A future LLM may suggest ordered
known template keys, but local validation and deterministic calculations remain
authoritative.

**Complete:** [CAR-10 - Separate hard dietary restrictions from soft food
preferences](https://linear.app/thiagoksp/issue/CAR-10), merged through
[pull request #17](https://github.com/thiagoksp/carrinho/pull/17) on August 14, 2026.

It keeps supported dietary restrictions as hard filters, stores catalogue-backed
household tastes as soft local preferences, and validates an ordered known-key contract
for a future LLM without adding an LLM or network service.

## Milestone 3 - Standalone usable prototype

Instacart is no longer on the critical path. Carrinho should remain useful even if an
official shopping handoff is unavailable.

**Implemented:** [CAR-11 - Add a local browser interface](https://linear.app/thiagoksp/issue/CAR-11)

It adds a structured local form and renders the deterministic plan in a browser while
binding only to `127.0.0.1`. It adds no dependency, credential, or external request and
keeps the terminal interface working.

**Complete:** [CAR-12 - Let households edit local meals and generic
foods](https://linear.app/thiagoksp/issue/CAR-12), merged through
[pull request #20](https://github.com/thiagoksp/carrinho/pull/20) on August 14, 2026.

It provides a validated local JSON editor with stable text keys and a small starter
catalogue. Private extensions are saved atomically under ignored `local-data/`, valid
replacements create backups, and the latest backup can be restored. It adds no database,
account system, retailer SKU, or copied food database.

**Complete:** [CAR-13 - Add an optional guarded LLM meal
selector](https://linear.app/thiagoksp/issue/CAR-13)

The LLM may interpret household language and return ordered known meal-template keys.
Local validation, dietary safety, quantities, packages, and estimates remain
deterministic and authoritative. The implementation uses Structured Outputs, a
provider/model adapter, environment-based configuration, cost guards, and OpenAI
`gpt-5.6-luna` as the initial model when the feature is explicitly enabled. The selector
is off by default and stores no prompt, response, credential, token, or API key.

**Complete:** [CAR-14 - Add portable plan and shopping-list
exports](https://linear.app/thiagoksp/issue/CAR-14)

It adds browser copy, print-friendly output, and local downloads for the meal plan,
Instacart paste list, and Instacart JSON preview while preserving the existing terminal
text and JSON exports.

**Complete:** [CAR-22](https://linear.app/thiagoksp/issue/CAR-22/simplify-first-run-household-setup),
merged through [pull request #32](https://github.com/thiagoksp/carrinho/pull/32).

Keep first use light: define the minimum inputs for a useful plan and move richer rules
into progressive prompts, profile editing, or review suggestions. Preserve a
deterministic form path for households that do not enable LLM. The browser surface
should support simple, guided, and future conversational use in one responsive,
app-friendly interface so a later PWA or mobile path remains open.

**Next:** [CAR-32](https://linear.app/thiagoksp/issue/CAR-32/use-carrinho-for-a-real-weekly-planning-run)

Use Carrinho for one realistic weekly planning run and make the smallest practical
fixes that help the user start using the product. This is intentionally narrower than a
new architecture milestone: identify confusing output, rough UI, or missing planning
details that block real use, then fix only what is necessary.

**Backlog:** [CAR-15](https://linear.app/thiagoksp/issue/CAR-15/evaluate-cheaper-llm-providers-for-guarded-meal-selection)

Compare OpenAI, Gemini, Groq, and Claude options against the same guarded
meal-selection eval set. Provider switching must stay behind the CAR-13 adapter and a
second production provider should only be added if cost, quality, reliability, or setup
evidence supports it.

**Backlog:** [CAR-16](https://linear.app/thiagoksp/issue/CAR-16/prepare-catalogue-identities-for-a-future-database)

Document the identity strategy before any database migration. JSON files, exports,
prompts, and LLM contracts use stable text keys; a future database may add internal ids
while preserving unique `stable_key` values.

**Backlog:** [CAR-17](https://linear.app/thiagoksp/issue/CAR-17/expand-supported-dietary-restrictions-safely)

Expand hard dietary restrictions beyond lactose intolerance only through explicit
catalogue tags, validation rules, and tests. Household dislikes and preferred foods stay
soft preferences; dietary safety remains deterministic and is never delegated to an LLM.
Consider CAR-18 before broadening this list so dietary rules and household preferences do
not become separate systems.

**Backlog:** [CAR-18](https://linear.app/thiagoksp/issue/CAR-18/design-a-unified-household-rules-model)

Design one household-rules model for hard restrictions, soft dislikes, soft preferences,
brand-only choices, frequency preferences, and future review feedback. The model should
preserve different enforcement levels while allowing an LLM to suggest pending rules only
after local validation and user confirmation.

**Backlog:** [CAR-19](https://linear.app/thiagoksp/issue/CAR-19/design-ingredient-substitution-rules)

Design catalogue-backed ingredient substitutions so Carrinho can suggest similar
ingredients without losing meal intent, dietary safety, package calculations, or
household rules. LLMs may propose candidates, but local rules approve safety and impact.

**Backlog:** [CAR-21](https://linear.app/thiagoksp/issue/CAR-21/design-configurable-shopping-strategy-preferences)

Design shopping strategy preferences such as cheapest acceptable item, brand-only rule,
package-size preference, or review-required substitution. This must not turn Carrinho
into retailer comparison; it only chooses among available candidates when approved data
or user review exists.

**Backlog:** [CAR-24](https://linear.app/thiagoksp/issue/CAR-24/track-meal-history-and-variety-preferences)

Design local meal-history and feedback rules so Carrinho can avoid repetitive menus,
rotate proteins and meal styles, and learn when a household is tired of a dish. Keep
history private and local, and do not store retailer receipts or sensitive checkout
data.

**Backlog:** [CAR-26](https://linear.app/thiagoksp/issue/CAR-26/design-household-member-dietary-profiles)

Design local household member dietary profiles so one household can select which eaters
are included in a plan. Profiles should represent dietary/planning needs, not separate
login accounts. Selected profiles combine hard restrictions conservatively while keeping
soft preferences, brands, portions, and household-level pantry/budget data distinct.

**Backlog:** [CAR-28](https://linear.app/thiagoksp/issue/CAR-28/evaluate-recipe-sources-and-simplified-recipe-entry)

Design how Carrinho can expand recipes without copying unlicensed recipe content. Start
from a small Canadian starter set and simplified user-entered recipes; later evaluate
approved recipe APIs or licensed sources. Any future LLM help should parse user text
into Carrinho's validated meal-template schema, not bypass local validation.

**Backlog:** [CAR-25](https://linear.app/thiagoksp/issue/CAR-25/verify-codex-and-linear-ownership-before-account-migration)

Before a future account switch, verify GitHub, Linear, Codex, local repository access,
and the single-`Next` workflow. This is a human operating checkpoint, not product code.

**Backlog:** [CAR-30](https://linear.app/thiagoksp/issue/CAR-30/evaluate-freezing-or-removing-the-legacy-terminal-interface)

Evaluate whether the terminal interface should be kept, frozen, hidden from docs, or
removed now that the local browser interface is the primary product surface. Preserve
parser and planner coverage if terminal tests are later removed.

**Complete:** [CAR-27](https://linear.app/thiagoksp/issue/CAR-27/review-ip-licensing-and-public-repository-protection)

Keep the repository public for Instacart review while making it clear that Carrinho is
not open source. The project now has an all-rights-reserved notice, a no-outside-
contributions policy, an English GitHub description, and a legal/IP checklist for
future commercialization review.

## Milestone 4 - Official API integration

**Parallel external dependency:** [CAR-3 - Track Instacart Developer Platform
approval](https://linear.app/thiagoksp/issue/CAR-3/track-instacart-developer-platform-approval)

CAR-3 remains in Backlog until Instacart responds. It is not labelled `Next`, and no code
change is required while the external state is unchanged.

**Blocked by CAR-3:** [CAR-4 - Implement the approved Instacart development
handoff](https://linear.app/thiagoksp/issue/CAR-4/implement-the-approved-instacart-development-handoff)

Network behaviour remains disabled until Instacart approves access and the development
contract is reviewed. Never store an API key in Linear, GitHub, chat, logs, or generated
project files.

**Backlog:** [CAR-20](https://linear.app/thiagoksp/issue/CAR-20/map-generic-grocery-items-to-retailer-product-candidates)

After approved access, design the product-matching layer from Carrinho's generic
catalogue items to retailer or Instacart product candidates. Capture brand, package
size, unit, variable-weight status, price, availability, and evidence source only when
contractually available, and mark ambiguous matches for user review.

**Backlog:** [CAR-23](https://linear.app/thiagoksp/issue/CAR-23/use-approved-popularity-and-review-signals-for-product-selection)

Use approved product-selection signals, such as popularity, ratings, review feedback,
or "most bought" style data, only when the provider contract allows it. These signals
can help choose reliable product candidates and reduce brand decisions, but fake test
data should be used until approved access exists.

## Product boundaries

- one meal plan and one shopping-list handoff;
- Canada and CAD;
- retailer selection, availability, actual prices, fees, and checkout stay in Instacart;
- no retailer comparison, scraping, checkout automation, or live-price claim;
- no new platform or service without a concrete project need.
