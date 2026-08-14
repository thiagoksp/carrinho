# Carrinho reference case

This is the first approved scenario used to guide development and tests.

Status: this is the current retailer-neutral implementation baseline.

## Input

> I have CAD$80 to feed 2 people for 4 days. We have low energy for cooking,
> already have enough rice and 7 eggs, and at least one person is lactose
> intolerant. We need lunch and dinner.

## Expected interpretation

- Maximum budget: CAD$80.
- People: 2.
- Period: 4 days.
- Meals: lunch and dinner.
- Total: 8 household meals, equal to 16 individual servings.
- Cooking energy: low.
- Pantry: enough rice and exactly 7 eggs.
- Dietary restriction: the entire plan must avoid intentional dairy ingredients.
- Foods to avoid or prefer: none supplied, so the established catalogue order remains
  the deterministic baseline.

## Expected response

1. Summary of the understood request.
2. One lunch-and-dinner plan for four days.
3. Leftover and batch-cooking guidance to reduce effort.
4. One shopping list that separates recipe need from purchasable package quantity.
5. One clearly labelled simulated Canadian planning estimate per item and an estimated
   total.
6. Remaining budget balance or a clear shortfall.
7. An explanation of how the rice and seven eggs are used.
8. One retailer-neutral, reviewable Instacart shopping-list handoff.

## Acceptance criteria

- The plan contains exactly 4 lunches and 4 dinners for 2 people.
- No intentional dairy ingredient is required.
- Meals prioritize simple preparation and leftovers.
- The shopping list accounts for the rice and exactly 7 eggs already available.
- Fixed-size items are rounded up to whole packages and show the expected overage.
- Mass, volume, and discrete counts use compatible normalized units even when the
  package is labelled in pounds, kilograms, litres, millilitres, cans, or dozens.
- Variable-weight items are marked as approximate; Carrinho does not promise an exact
  purchased weight or final price.
- The current simulated total for this case remains within CAD$80.
- Soft food preferences remain separate from hard dietary restrictions and do not
  change this case when none are supplied.
- No city or retailer is required, inferred, or included in the summary or saved plan.
- The app uses one simulated Canadian catalog; it does not compare or rank retailers.
- The handoff leaves address, retailer selection, availability, and actual prices to
  Instacart.
- Automatic checkout and live prices are not claimed at this stage.
