# Local household data

Carrinho can save an optional household profile in `local-data/household-profile.json`.
The directory is ignored by Git and is never uploaded by Carrinho.

## What is saved

- people;
- cooking energy;
- pantry items;
- dietary restrictions;
- generic product keys for foods to use less often;
- generic product keys for foods to use more often.

Budget, days, currency, address, retailer, payment information, receipts, and API keys
are never part of the household profile.

## How it works

If a profile exists, the terminal asks whether to use it. Saved values fill only the
fields missing from the current request, so a new request always wins. After a confirmed
plan, the terminal separately asks whether to save or update the profile.

The request summary lets the user correct **Foods to use less often** or **Foods to use
more often** and then save those selections with the profile. Carrinho resolves common
names such as
`onions`, `beans`, or `eggs` through the small existing generic product catalogue. It
does not ship or copy an exhaustive external food dataset. An unknown food is reported
clearly and is not silently stored or guessed.

The file uses schema `carrinho.household-profile.v2`. Version 1 profiles remain readable
and load with empty food-preference lists. This is a local convenience feature, not an
account or synchronization service. Deleting `local-data/household-profile.json` removes
the saved profile from that computer.
