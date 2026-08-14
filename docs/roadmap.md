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

## Operating rule

Exactly one open issue should have the `Next` label. Finish or deliberately cancel
that issue before promoting another one. Every code change should reference its Linear
issue and be published through a tested GitHub pull request.

At the start of a work session:

1. read `AGENTS.md` and `docs/project-handoff.md`;
2. open the Linear project;
3. work only on the issue labelled `Next` unless the user explicitly changes priority;
4. update the issue with evidence and move its status when the work changes state.

## Milestone 1 — Validate manual handoff

**Next:** [THI-6 — Validate the reference list in Instacart Paste
items](https://linear.app/thiagoksp/issue/THI-6/validate-the-reference-list-in-instacart-paste-items)

Run the approved reference case, inspect the three generated files, and test every
paste-list line through Instacart's iPhone **Shopping List → Paste items** flow. Record
only observed matching, quantity, and dietary-label problems. Do not record an address,
receipt, checkout detail, or credential.

## Milestone 2 — Improve product matching

**Blocked by THI-6:** [THI-7 — Improve Instacart matching from manual
evidence](https://linear.app/thiagoksp/issue/THI-7/improve-instacart-matching-from-manual-evidence)

Change generic search terms or structured measurements only when the manual test
provides evidence. Add regression tests and keep the output retailer-neutral.

## Milestone 3 — Official API integration

**External dependency:** [THI-5 — Track Instacart Developer Platform
approval](https://linear.app/thiagoksp/issue/THI-5/track-instacart-developer-platform-approval)

**Blocked by THI-5:** [THI-8 — Implement the approved Instacart development
handoff](https://linear.app/thiagoksp/issue/THI-8/implement-the-approved-instacart-development-handoff)

Network behaviour remains disabled until Instacart approves access and the development
contract is reviewed. Never store an API key in Linear, GitHub, chat, logs, or generated
project files.

## Product boundaries

- one meal plan and one shopping-list handoff;
- Canada and CAD;
- retailer selection, availability, actual prices, fees, and checkout stay in Instacart;
- no retailer comparison, scraping, checkout automation, or live-price claim;
- no new platform or service without a concrete project need.
