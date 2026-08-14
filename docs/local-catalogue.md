# Private local catalogue extensions

Updated: August 14, 2026.

Carrinho ships a deliberately small, versioned starter catalogue. A household can add
its own generic foods and meal templates in one private JSON document without changing
Python code, creating an account, or adding a database.

## Where the data stays

The browser editor saves:

```text
local-data/custom-catalogue.json
```

The entire `local-data/` directory is ignored by Git. It must not contain passwords,
credentials, addresses, receipts, retailer SKUs, or other personal records.

The local document extends the built-in catalogues. It cannot replace a built-in product
or meal key. Removing the local file returns Carrinho to the built-in starter data.

## Browser workflow

1. Start `web_app.py` and open <http://127.0.0.1:8765>.
2. Choose **Manage local meals and foods**.
3. Edit the JSON document.
4. Choose **Validate and save local catalogue**.
5. Read any validation error, correct the named field, and save again.

Carrinho validates the complete document before writing anything. When a previous local
file exists, it is copied into `local-data/backups/` before the new validated document
replaces it. **Restore latest backup** restores the newest valid backup and preserves
the file that it replaces, making the last change reversible.

## Document shape

An empty valid document is:

```json
{
  "schema": "carrinho.local-catalogue.v1",
  "products": [],
  "meal_templates": []
}
```

Keys are stable identifiers, not numeric database IDs. They use lowercase letters,
numbers, and underscores, such as `spinach_rice_bowl`. Local keys must be unique and
must not duplicate a built-in key.

## Generic foods

A product entry describes one generic purchasable package and one clearly labelled
simulated CAD planning estimate. It is not a retailer listing or live-price record.

Required fields:

- `key`, `name`, and `keywords` identify the generic food;
- `package_description`, `package_size`, and `planning_unit` describe the planning
  package;
- `package_price` is a simulated non-negative CAD estimate;
- `variable_weight` marks packages whose final weight may differ;
- `instacart_search_term`, `instacart_quantity`, and `instacart_unit` preserve the
  retailer-neutral future handoff shape.

Supported planning units are `g`, `ml`, `can`, `each`, and `package`. Supported handoff
units are `kg`, `g`, `can`, `lb bag`, `each`, `ml`, and `package`. Carrinho checks that
the two measurements describe the same package.

## Meal templates

A meal template contains:

- a stable `key` and a user-visible `dish`;
- `catalogue_tier`: `core` or `extended`;
- `cooking_energy`: `low`, `normal`, or `high`;
- the currently supported `dietary_tags` and `selection_tags`;
- one or more ingredients with `product_key`, `quantity_per_person`, and
  `planning_unit`.

Every ingredient must reference a built-in or local generic product and use that
product's planning unit. The editor shows copyable food and meal examples.

Dietary tags are household declarations used by local validation. They are not medical
verification. Product labels must still be reviewed.

## Soft preferences

The planner labels disliked foods as **Foods to use less often** and favourites as
**Foods to use more often**. These values rank otherwise eligible meals; they are not
hard exclusions. A longer plan can still contain a disliked food. Supported dietary
restrictions remain the hard filtering boundary.

## Safety boundary

- no network request is made;
- no third-party package or service is required;
- the local document is limited to 256 KiB;
- unknown fields, duplicate keys, unknown ingredients, incompatible units, malformed
  JSON, and unsupported schema versions are rejected;
- invalid updates do not replace the last valid file;
- built-in starter files under `data/` remain unchanged.
