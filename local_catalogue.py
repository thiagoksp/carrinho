"""Validate and store private household catalogue extensions."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from catalog import (
    PriceCatalog,
    Product,
    load_simulated_catalog,
    parse_catalog_data,
)
from meal_catalogue import (
    MEAL_CATALOGUE_SCHEMA,
    MealCatalogue,
    MealTemplate,
    load_default_meal_catalogue,
    parse_meal_catalogue_data,
)


LOCAL_CATALOGUE_SCHEMA = "carrinho.local-catalogue.v1"
DEFAULT_LOCAL_DATA_DIRECTORY = Path(__file__).resolve().parent / "local-data"
LOCAL_CATALOGUE_FILENAME = "custom-catalogue.json"
BACKUP_DIRECTORY_NAME = "backups"
MAX_LOCAL_CATALOGUE_BYTES = 256 * 1024
PRODUCT_FIELDS = {
    "key",
    "name",
    "package_description",
    "package_size",
    "package_price",
    "planning_unit",
    "variable_weight",
    "keywords",
    "instacart_search_term",
    "instacart_quantity",
    "instacart_unit",
}
MEAL_TEMPLATE_FIELDS = {
    "key",
    "dish",
    "catalogue_tier",
    "cooking_energy",
    "dietary_tags",
    "selection_tags",
    "ingredients",
    "cuisine",
}
INGREDIENT_FIELDS = {
    "product_key",
    "quantity_per_person",
    "planning_unit",
}


@dataclass(frozen=True)
class LocalCatalogue:
    products: tuple[Product, ...]
    meal_templates: tuple[MealTemplate, ...]


@dataclass(frozen=True)
class LocalCatalogueSaveResult:
    path: Path
    backup_path: Path | None
    product_count: int
    meal_template_count: int


def _local_catalogue_path(local_data_directory: Path | None = None) -> Path:
    directory = local_data_directory or DEFAULT_LOCAL_DATA_DIRECTORY
    return directory / LOCAL_CATALOGUE_FILENAME


def empty_local_catalogue_document() -> dict[str, object]:
    """Return the smallest valid editable local catalogue document."""
    return {
        "schema": LOCAL_CATALOGUE_SCHEMA,
        "products": [],
        "meal_templates": [],
    }


def empty_local_catalogue_json() -> str:
    """Return readable JSON for a household that has no custom entries yet."""
    return json.dumps(empty_local_catalogue_document(), indent=2) + "\n"


def _validate_document_shape(data: object) -> dict[str, object]:
    if not isinstance(data, dict):
        raise ValueError("The local catalogue must be a JSON object.")
    fields = {"schema", "products", "meal_templates"}
    unexpected_fields = sorted(set(data).difference(fields))
    if unexpected_fields:
        raise ValueError(
            "The local catalogue has unsupported fields: "
            + ", ".join(unexpected_fields)
            + "."
        )
    if data.get("schema") != LOCAL_CATALOGUE_SCHEMA:
        raise ValueError("The local catalogue has an unsupported schema.")
    if not isinstance(data.get("products"), list):
        raise ValueError("The local catalogue products must be a list.")
    if not isinstance(data.get("meal_templates"), list):
        raise ValueError("The local catalogue meal_templates must be a list.")
    for position, product in enumerate(data["products"], start=1):
        if isinstance(product, dict):
            unexpected = sorted(set(product).difference(PRODUCT_FIELDS))
            if unexpected:
                raise ValueError(
                    f"Local product {position} has unsupported fields: "
                    + ", ".join(unexpected)
                    + "."
                )
    for position, template in enumerate(data["meal_templates"], start=1):
        if not isinstance(template, dict):
            continue
        unexpected = sorted(set(template).difference(MEAL_TEMPLATE_FIELDS))
        if unexpected:
            raise ValueError(
                f"Local meal {position} has unsupported fields: "
                + ", ".join(unexpected)
                + "."
            )
        ingredients = template.get("ingredients")
        if not isinstance(ingredients, list):
            continue
        for ingredient_position, ingredient in enumerate(ingredients, start=1):
            if isinstance(ingredient, dict):
                unexpected = sorted(set(ingredient).difference(INGREDIENT_FIELDS))
                if unexpected:
                    raise ValueError(
                        f"Local meal {position} ingredient {ingredient_position} "
                        "has unsupported fields: "
                        + ", ".join(unexpected)
                        + "."
                    )
    return data


def parse_local_catalogue_data(data: object) -> LocalCatalogue:
    """Validate local extensions against Carrinho's built-in catalogues."""
    document = _validate_document_shape(data)
    raw_products = document["products"]
    raw_templates = document["meal_templates"]
    assert isinstance(raw_products, list)
    assert isinstance(raw_templates, list)

    if raw_products:
        local_prices = parse_catalog_data(
            {
                "currency": "CAD",
                "price_type": "simulated",
                "description": (
                    "Household-local simulated planning estimates; retailer prices "
                    "and current offers may differ."
                ),
                "products": raw_products,
            }
        )
        products = local_prices.products
    else:
        products = ()

    if raw_templates:
        local_meals = parse_meal_catalogue_data(
            {
                "schema": MEAL_CATALOGUE_SCHEMA,
                "description": "Household-local meal templates.",
                "templates": raw_templates,
            },
            require_core=False,
        )
        meal_templates = local_meals.templates
    else:
        meal_templates = ()

    default_prices = load_simulated_catalog()
    default_meals = load_default_meal_catalogue()
    default_product_keys = {product.key for product in default_prices.products}
    default_meal_keys = {template.key for template in default_meals.templates}
    duplicate_product_keys = sorted(
        default_product_keys.intersection(product.key for product in products)
    )
    duplicate_meal_keys = sorted(
        default_meal_keys.intersection(template.key for template in meal_templates)
    )
    if duplicate_product_keys:
        raise ValueError(
            "Local product keys cannot replace built-in products: "
            + ", ".join(duplicate_product_keys)
            + "."
        )
    if duplicate_meal_keys:
        raise ValueError(
            "Local meal keys cannot replace built-in meals: "
            + ", ".join(duplicate_meal_keys)
            + "."
        )

    products_by_key = {
        product.key: product
        for product in (*default_prices.products, *products)
    }
    for template in meal_templates:
        for ingredient in template.ingredients:
            product = products_by_key.get(ingredient.product_key)
            if product is None:
                raise ValueError(
                    f"Local meal {template.key} uses unknown product "
                    f"{ingredient.product_key}."
                )
            if ingredient.planning_unit != product.planning_unit:
                raise ValueError(
                    f"Local meal {template.key} uses the wrong unit for "
                    f"{ingredient.product_key}."
                )

    return LocalCatalogue(
        products=products,
        meal_templates=meal_templates,
    )


def parse_local_catalogue_json(content: str) -> LocalCatalogue:
    """Decode and validate one local catalogue JSON document."""
    if len(content.encode("utf-8")) > MAX_LOCAL_CATALOGUE_BYTES:
        raise ValueError("The local catalogue is larger than 256 KiB.")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"The local catalogue is not valid JSON near line {error.lineno}."
        ) from error
    return parse_local_catalogue_data(data)


def load_local_catalogue(
    local_data_directory: Path | None = None,
) -> LocalCatalogue:
    """Load private catalogue extensions, or an empty catalogue when absent."""
    path = _local_catalogue_path(local_data_directory)
    if not path.exists():
        return LocalCatalogue(products=(), meal_templates=())
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError("The local catalogue could not be read.") from error
    return parse_local_catalogue_json(content)


def load_effective_price_catalog(
    local_data_directory: Path | None = None,
) -> PriceCatalog:
    """Merge validated local products after the immutable starter catalogue."""
    base = load_simulated_catalog()
    local = load_local_catalogue(local_data_directory)
    if not local.products:
        return base
    return PriceCatalog(
        currency=base.currency,
        price_type=base.price_type,
        description=(
            f"{base.description} Household-local simulated entries are included."
        ),
        products=base.products + local.products,
    )


def load_effective_meal_catalogue(
    local_data_directory: Path | None = None,
) -> MealCatalogue:
    """Merge validated local meals after the immutable starter catalogue."""
    base = load_default_meal_catalogue()
    local = load_local_catalogue(local_data_directory)
    if not local.meal_templates:
        return base
    return MealCatalogue(
        description=f"{base.description} Household-local templates are included.",
        templates=base.templates + local.meal_templates,
    )


def read_local_catalogue_json(
    local_data_directory: Path | None = None,
) -> str:
    """Return the editable local document without creating it."""
    path = _local_catalogue_path(local_data_directory)
    if not path.exists():
        return empty_local_catalogue_json()
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError("The local catalogue could not be read.") from error
    parse_local_catalogue_json(content)
    return content


def read_local_catalogue_source(
    local_data_directory: Path | None = None,
) -> str:
    """Return raw editable content even when external changes made it invalid."""
    path = _local_catalogue_path(local_data_directory)
    if not path.exists():
        return empty_local_catalogue_json()
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError("The local catalogue could not be read.") from error


def _backup_path(directory: Path, timestamp: datetime) -> Path:
    backups = directory / BACKUP_DIRECTORY_NAME
    backups.mkdir(parents=True, exist_ok=True)
    suffix = timestamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return backups / f"custom-catalogue-{suffix}.json"


def save_local_catalogue_json(
    content: str,
    local_data_directory: Path | None = None,
    *,
    timestamp: datetime | None = None,
) -> LocalCatalogueSaveResult:
    """Validate, back up, and atomically save a private local catalogue."""
    catalogue = parse_local_catalogue_json(content)
    data = json.loads(content)
    canonical_content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path = _local_catalogue_path(local_data_directory)
    path.parent.mkdir(parents=True, exist_ok=True)

    backup_path = None
    if path.exists():
        backup_path = _backup_path(
            path.parent,
            timestamp or datetime.now(timezone.utc),
        )
        shutil.copy2(path, backup_path)

    temporary_path = path.with_suffix(".tmp")
    try:
        temporary_path.write_text(canonical_content, encoding="utf-8")
        temporary_path.replace(path)
    except OSError as error:
        if temporary_path.exists():
            temporary_path.unlink()
        raise ValueError("The local catalogue could not be saved.") from error

    return LocalCatalogueSaveResult(
        path=path,
        backup_path=backup_path,
        product_count=len(catalogue.products),
        meal_template_count=len(catalogue.meal_templates),
    )


def restore_latest_local_catalogue(
    local_data_directory: Path | None = None,
    *,
    timestamp: datetime | None = None,
) -> LocalCatalogueSaveResult:
    """Restore the newest valid backup while preserving the current document."""
    directory = local_data_directory or DEFAULT_LOCAL_DATA_DIRECTORY
    backup_directory = directory / BACKUP_DIRECTORY_NAME
    backups = sorted(backup_directory.glob("custom-catalogue-*.json"))
    if not backups:
        raise ValueError("No local catalogue backup is available.")
    try:
        content = backups[-1].read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError("The local catalogue backup could not be read.") from error
    return save_local_catalogue_json(
        content,
        directory,
        timestamp=timestamp,
    )
