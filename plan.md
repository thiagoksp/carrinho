# CAR-17 implementation plan — Food rules

## Objective

Expand Carrinho from lactose-intolerance-only filtering to one simple **Food rules**
experience that supports:

- common household dietary needs;
- catalogue-backed foods the household never wants included;
- deterministic enforcement before meal ranking, pricing, or LLM selection;
- a domain contract that can later support feedback, frequency, brands, and member
  profiles without weakening safety-relevant rules.

This plan is approved product direction. It is intended to be handed directly to the
developer.

## Current status

- Landed the CAR-18 foundation: `food_rules.py`, planner enforcement, request parsing,
  household-profile normalization, and focused tests.
- Landed the browser Food rules UI, chip-based foods-to-avoid editor, and applied-rule
  summary wiring.
- Next: final verification notes and Linear/merge bookkeeping.

## Approved product decisions

1. Dietary needs and disliked foods share one rule mechanism because both can produce
   the action `exclude`.
2. The system must preserve why a rule exists. An intolerance, dietary pattern, and
   preference are not interchangeable even when their current result is the same.
3. `Foods to avoid` means absolute exclusion in this release. It is not a soft ranking
   signal.
4. Rules apply to the whole household in CAR-17. Per-member rules remain future work.
5. The first presets are:
   - `Lactose intolerance`;
   - `Vegetarian`;
   - `Vegan`;
   - `Avoid gluten ingredients`.
6. The product must not describe the gluten option as celiac-safe or make any allergy
   safety guarantee.
7. Custom foods are accepted only after they resolve to a known generic catalogue key.
   Unknown text is rejected clearly rather than silently ignored.
8. The LLM may later propose structured rules, but it never decides dietary safety or
   bypasses deterministic validation.

## Delivery dependency

CAR-17 remains blocked by CAR-18. The smallest CAR-18 foundation must be implemented and
merged first:

- the versioned `FoodRule` contract;
- canonical target resolution;
- deterministic precedence;
- a compatibility adapter for the current request/profile fields.

Do not implement frequency, brand, feedback, member profiles, or LLM interpretation as
part of that prerequisite. Those capabilities only need compatible extension points.

## Domain contract supplied by CAR-18

Represent each active rule with these concepts:

```text
code            Stable semantic key
scope_type      household
target_type     dietary_pattern | catalogue_food
target_key      Canonical catalogue key
action          exclude
reason_type     intolerance | dietary_pattern | preference
enforcement     required
source          preset | user
active          boolean
```

Examples:

```text
code: diet.lactose_intolerance
target_type: dietary_pattern
target_key: lactose_intolerance
action: exclude
reason_type: intolerance
enforcement: required
source: preset
```

```text
code: food.beans.exclude
target_type: catalogue_food
target_key: beans
action: exclude
reason_type: preference
enforcement: required
source: user
```

Versioned JSON, exports, prompts, and integrations continue to use stable text keys. A
future database may add an internal numeric ID while keeping `code` unique and immutable.
Do not add a database in CAR-17 or CAR-18.

### Precedence

Apply rules in this order:

1. required dietary-pattern rules;
2. required catalogue-food exclusions;
3. existing soft preferences only among the surviving meals;
4. optional LLM ordering only among the surviving known meal-template keys;
5. package calculations and the final deterministic plan.

No fallback may remove or weaken an active required rule. If no meal survives, return an
explainable error.

## Preset and catalogue contract

Use stable codes and explicit meal-template tags:

| Preset | Rule code | Required meal tag |
| --- | --- | --- |
| Lactose intolerance | `diet.lactose_intolerance` | `lactose-free` |
| Vegetarian | `diet.vegetarian` | `vegetarian` |
| Vegan | `diet.vegan` | `vegan` |
| Avoid gluten ingredients | `diet.avoid_gluten_ingredients` | `no-gluten-ingredients` |

Catalogue requirements:

- audit every built-in meal template before adding a new dietary tag;
- a `vegan` template must also carry `vegetarian`;
- tags describe known recipe ingredients only, not manufacturing or cross-contamination;
- custom catalogue templates must use the same allowed tags and validation;
- incomplete, unsupported, duplicate, or contradictory tags fail catalogue loading;
- food exclusions match canonical generic food keys used by recipe ingredients, never
  display names or retailer SKUs.

## Compatibility and migration

Preserve existing local data through an input adapter:

```text
dietary_restrictions[] -> preset FoodRule values
foods_to_avoid[]       -> required catalogue-food FoodRule values
```

Migration rules:

- existing lactose-intolerance profiles continue to work;
- existing `foods_to_avoid` entries change from soft demotion to absolute exclusion;
- existing `foods_to_prefer` entries retain their current soft-ranking behaviour and are
  not redesigned in CAR-17;
- duplicate aliases resolve to one canonical rule;
- a food present in both avoid and prefer inputs remains an explicit validation error;
- unknown legacy values fail with a useful message; they are never treated as protected;
- do not require users to edit private JSON manually.

## Planner behaviour

Before ranking meals:

1. normalize the request into active `FoodRule` values;
2. validate all rule codes and targets;
3. filter templates by required dietary tags;
4. remove every template containing a required excluded food key;
5. stop with an explainable error if no compatible template remains;
6. pass only compatible template keys to the existing deterministic or guarded-LLM
   selector;
7. build the shopping list only from the selected compatible templates.

The planner result must expose a human-readable summary of the applied rules. Excluded
foods must not appear in meals, recipe requirements, or the shopping list.

## Browser experience

Replace the current single dietary restriction select with one optional, responsive
section:

```text
Food rules
Tell us about dietary needs and foods you want left out.

Dietary needs
Choose any that apply.
[Lactose intolerance] [Vegetarian] [Vegan] [Avoid gluten ingredients]

Foods to avoid
[Add an ingredient, such as coconut or mushrooms]
```

Interaction requirements:

- no rule is selected by default;
- users can generate a plan without interacting with the section;
- presets support multiple selections using accessible checkboxes or equivalent controls;
- recognized custom foods become removable chips;
- aliases and duplicate entries collapse to one canonical item;
- the layout remains usable with keyboard, screen reader, touchscreen, and a 320–360 px
  viewport;
- entered values remain present when validation fails;
- do not show a large ingredient directory;
- do not add recipe dislikes, frequency controls, brand controls, or member selectors.

Required messages:

```text
We can't reliably filter "X" yet. Try a more general ingredient.
```

```text
We couldn't build a plan with all these food rules. Remove one rule or adjust your meal preferences.
```

On a successful result:

```text
Food rules applied: Vegan, no beans.
```

Safety copy:

```text
Carrinho uses available ingredient information to filter meals. Always check product labels for allergies or medical dietary needs.
```

## Expected implementation surface

The developer should confirm the final placement after reading the current code, but the
expected focused changes are:

- add `food_rules.py` for the versioned rule contract, preset definitions, normalization,
  canonical resolution, and precedence;
- update `meal_catalogue.py` and `data/meal-catalogue.json` with validated dietary tags;
- update `planning.py` to apply normalized rules before ranking and LLM selection;
- update `household_profile.py` with the backward-compatible field adapter;
- update `web_app.py` with the Food rules interface, validation, preserved form state,
  and result summary;
- keep `request_parser.py` compatible with current terminal input without adding LLM or
  broad free-text interpretation;
- add focused tests in `tests/test_food_rules.py` and update the existing meal catalogue,
  planning, household profile, and browser tests.

Do not redesign unrelated screens or remove the terminal interface in this issue.

## Implementation sequence

1. **Land the minimal CAR-18 contract**
   - add `FoodRule`, preset definitions, validation, and legacy-field normalization;
   - add contract tests without changing user-visible behaviour.
2. **Audit and tag the catalogue**
   - classify every built-in template;
   - enforce tag implications and custom-catalogue validation.
3. **Enforce the rules in planning**
   - apply dietary tags and foods-to-avoid before ranking;
   - protect both deterministic and LLM selector paths;
   - add no-compatible-meal behaviour.
4. **Migrate local profile input**
   - read legacy fields through the adapter;
   - preserve valid existing profiles and reject unknown values clearly.
5. **Implement the browser flow**
   - add the Food rules UI and validation states;
   - show applied rules in the result.
6. **Verify the approved slice**
   - run the focused tests for each modified module;
   - run the full suite only when the user authorizes consolidation.

## Acceptance criteria

- A request with no food rules produces the existing baseline behaviour.
- Each supported preset deterministically removes incompatible templates.
- `Vegan` never returns a non-vegan template and all vegan templates validate as
  vegetarian.
- `Avoid gluten ingredients` is never labelled or described as celiac-safe.
- A recognized custom food never appears in the generated meals or shopping list.
- Unknown foods or dietary values are rejected and remain visible for correction.
- Alias and duplicate input resolves to one canonical rule.
- Conflicting avoid/prefer values produce an explicit validation error.
- Required rules are applied before soft ranking and before the LLM receives candidates.
- No-compatible-meal scenarios never relax rules automatically.
- Applied rules appear in the browser result.
- Legacy lactose and food-preference profiles remain readable through the adapter.
- Invalid built-in or custom catalogue tags fail during catalogue loading.
- Tests cover every preset, custom exclusion, conflict, unknown value, zero-result state,
  legacy profile, custom catalogue, deterministic selector, and guarded-LLM selector.
- No network request, database, retailer SKU, live price, credential, or medical-safety
  claim is added.

## Explicitly deferred work

Track these outside CAR-17:

- recipe and product likes/dislikes;
- `prefer more`, `prefer less`, and weekly frequency;
- feedback-driven personalization and automatic rule suggestions;
- brand-only rules and product-ranking signals;
- ingredient substitution;
- household-member profiles;
- LLM interpretation of conversational food rules;
- celiac-safe or allergy-safe product verification;
- unresolved user-created food concepts and large external food taxonomies.

## Definition of done

CAR-17 is done only when the approved Food rules flow works end to end in the local
browser, the planner and shopping list obey every required rule, unsupported input fails
clearly, focused and consolidation tests pass, Linear records the implementation result,
and the published documentation contains no medical guarantee.

## Canadian safety references

- CFIA: <https://inspection.canada.ca/en/food-labels/labelling/industry/allergens-and-gluten>
- Health Canada gluten-free position:
  <https://www.canada.ca/en/health-canada/services/food-nutrition/food-safety/food-allergies-intolerances/celiac-disease/health-canada-position-gluten-free-claims.html>
- Health Canada milk allergen information:
  <https://www.canada.ca/en/health-canada/services/food-nutrition/reports-publications/food-safety/milk-priority-food-allergen.html>
