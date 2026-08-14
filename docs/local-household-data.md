# Local household data

Carrinho can save an optional household profile in `local-data/household-profile.json`.
The directory is ignored by Git and is never uploaded by Carrinho.

## What is saved

- people;
- cooking energy;
- pantry items;
- dietary restrictions.

Budget, days, currency, address, retailer, payment information, receipts, and API keys
are never part of the household profile.

## How it works

If a profile exists, the terminal asks whether to use it. Saved values fill only the
fields missing from the current request, so a new request always wins. After a confirmed
plan, the terminal separately asks whether to save or update the profile.

The file uses schema `carrinho.household-profile.v1`. It is a local convenience feature,
not an account or synchronization service. Deleting `local-data/household-profile.json`
removes the saved profile from that computer.
