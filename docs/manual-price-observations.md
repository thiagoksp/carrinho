# Manual price observations

Status: this is a legacy research tool from the No Frills and Toronto pilot. The
approved product direction uses Instacart as the shopping handoff and does not require
Carrinho to select a retailer or city. These observations remain isolated and will not
become the source of planning estimates or checkout prices.

Date: August 13, 2026.

## Why this experiment was manual

No public, authorized No Frills or Loblaw feed was identified that provided Carrinho
with exact consumer prices by store. Prices can vary by location, channel, promotion,
and fulfilment time. The experiment was therefore local, manual, and limited to personal
development use.

Carrinho does not scrape a website, import Flipp data, or turn flyers into a commercial
database. Any future automated or commercial use requires a source licensed in writing.

This is not a comparison dataset. Each valid record documents one historical observation
tied to an exact store, package, channel, and observation date. It never becomes a
planning estimate, a selected retailer price, or a checkout price.

## Create the template

From a terminal opened in the project directory:

```powershell
.\.venv\Scripts\python.exe manual_prices.py create-template
```

The command creates `outputs/no-frills-toronto-prices.csv` and adds a number to the name
when a template already exists. The importer uses the most recently modified template.
The file opens in Excel on this Windows system and may be saved with either a comma or a
semicolon delimiter.

The `key` and `product_reference` columns come from the simulated catalog only to
identify the type of food being observed. They are not real SKUs and must not be edited.

To start a row, complete every remaining field:

- `observed_package`: the package actually seen, such as `750 g package`;
- `price_cad`: the regular price of one package, such as `13.49` or `13,49`;
- `observed_on`: the date in `YYYY-MM-DD`; Excel's `M/D/YYYY` format is also accepted;
- `store_location`: the exact No Frills Toronto branch, including an address or postal
  code;
- `channel`: `official-site`, `store-label`, or `final-receipt`;
- `price_type`: `regular`;
- `quantity_mode`: `fixed-package` or `final-receipt-weight`;
- `declared_source`: an official URL or a short description such as
  `personal receipt without personal data`.

Use `final-receipt-weight` only with `final-receipt`. For products sold by weight, do not
import an approximate website total; use the final weight and amount actually charged on
a completed receipt.

This version rejects promotions, coupons, member prices, and multi-buy offers such as
`2 for $5`. Common email, phone, card, order, and receipt identifiers are rejected, but
this is not a complete personal-data detector. Do not enter a name, home address, order
or receipt number, card information, or other personal data in `declared_source`.

You may start with one product. Leave all observation fields blank on the other rows.
If you enter multiple products, every row must use the same exact store location.

## Validate and import

After saving the CSV:

```powershell
.\.venv\Scripts\python.exe manual_prices.py import
```

The importer validates the header, product references, observed package, value, date,
exact store, channel, price type, quantity mode, and declared source. If it finds a
problem, it displays every error together and creates no partial snapshot.

A valid import creates a JSON file in `outputs/` containing:

- the pilot retailer and region;
- the declared package, price in cents, exact store, date, channel, and source;
- the source CSV filename and SHA-256 hash;
- a warning that the record is manual, historical, self-declared, and unverified.

The hash identifies the bytes that were imported. It does not prove a receipt, page,
price, or authenticity. Files in `outputs/` are excluded from Git.

## Boundary of this stage

The planner continues to use only the simulated catalog. Manual records are permanently
isolated, are never labelled as licensed, do not enable `real_prices_available`, and
cannot affect a budget or shopping-list handoff. No manual observation becomes a
canonical product price source.

Official sources:

- [No Frills](https://www.nofrills.ca/en/food/c/27985)
- [Loblaw explanation of store and channel price variation](https://www.loblaw.ca/en/real-talk-does-loblaw-use-personal-data-to-raise-prices/)
- [Loblaw legal terms](https://www.loblaw.ca/en/legal/)
- [Flipp terms of use](https://corp.flipp.com/terms-of-use/)

## Next step

No further manual price collection is planned. Keep the tool isolated until a later
code-cleanup decision removes or archives the experiment.
