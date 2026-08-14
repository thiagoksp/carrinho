# Carrinho reference case

This is the first approved scenario used to guide development and tests.

## Input

> I have CAD$80 to feed 2 people for 4 days. We have low energy for cooking,
> already have enough rice and 7 eggs, and at least one person is lactose
> intolerant. We need lunch and dinner. I am in Toronto and will shop at No Frills.

## Expected interpretation

- Maximum budget: CAD$80.
- People: 2.
- Period: 4 days.
- Meals: lunch and dinner.
- Total: 8 household meals, equal to 16 individual servings.
- Cooking energy: low.
- Pantry: enough rice and exactly 7 eggs.
- Dietary restriction: the entire plan must avoid intentional dairy ingredients.
- Shopping area: Toronto.
- Selected store: No Frills.

## Expected response

1. Summary of the understood request.
2. One lunch-and-dinner plan for four days.
3. Leftover and batch-cooking guidance to reduce effort.
4. One shopping list with package-aware quantities.
5. One selected working price per item and an estimated total.
6. Remaining budget balance or a clear shortfall.
7. An explanation of how the rice and seven eggs are used.
8. One reviewable cart handoff.

## Acceptance criteria

- The plan contains exactly 4 lunches and 4 dinners for 2 people.
- No intentional dairy ingredient is required.
- Meals prioritize simple preparation and leftovers.
- The shopping list accounts for the rice and exactly 7 eggs already available.
- The current simulated total for this case remains within CAD$80.
- The shopping area and selected store appear in the summary and saved plan.
- The app uses one price catalog and one selected store; it does not compare or rank
  retailers.
- Automatic checkout and live prices are not claimed at this stage.
