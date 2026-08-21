"""Serve Carrinho's standalone interface on the local computer."""

from collections.abc import Mapping
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import secrets
from urllib.parse import parse_qs, urlsplit

from app import format_plan
from catalog import resolve_product_keys
from food_rules import normalize_food_rule_values
from instacart import create_instacart_paste_list, serialize_instacart_payload
from local_catalogue import (
    empty_local_catalogue_json,
    load_effective_price_catalog,
    read_local_catalogue_json,
    read_local_catalogue_source,
    restore_latest_local_catalogue,
    save_local_catalogue_json,
)
from llm_selector import LLMSelectorError, suggest_meal_candidate_keys
from planning import (
    Plan,
    format_planning_quantity,
    generate_plan,
    select_meal_candidate_templates,
)
from request_parser import ParsedRequest, parse_request


HOST = "127.0.0.1"
PORT = 8765
MAX_REQUEST_BYTES = 1024 * 1024
CSRF_TOKEN = secrets.token_urlsafe(32)
DIETARY_RULE_OPTIONS = (
    ("dietary_lactose_intolerance", "Lactose intolerance", "lactose intolerance"),
    ("dietary_vegetarian", "Vegetarian", "vegetarian"),
    ("dietary_vegan", "Vegan", "vegan"),
    (
        "dietary_avoid_gluten_ingredients",
        "Avoid gluten ingredients",
        "avoid gluten ingredients",
    ),
)
DIETARY_RULE_LABELS = {
    canonical: label for _, label, canonical in DIETARY_RULE_OPTIONS
}

PAGE_STYLES = """
    :root { color-scheme: light; font-family: Inter, system-ui, sans-serif; }
   body { margin: 0; background: #f5f2e9; color: #17352c; line-height: 1.5; }
    main { width: min(920px, calc(100% - 32px)); margin: 40px auto; }
    header { margin-bottom: 24px; }
    h1 { font-size: clamp(2.2rem, 8vw, 4.5rem); margin: 0;
      letter-spacing: -0.06em; }
    h2 { margin-top: 0; }
   h3, h4 { margin-top: 0; }
   a { color: #146b4d; font-weight: 750; }
   .eyebrow { color: #b3422e; font-weight: 800; text-transform: uppercase; }
   .card, .result { background: #fff; border: 1px solid #d8d2c4;
     border-radius: 18px; box-shadow: 0 14px 40px rgba(23, 53, 44, 0.08);
     padding: 22px; }
   .page-intro { margin-bottom: 18px; }
   .page-intro p { margin: 8px 0 0; max-width: 62ch; color: #465a54; }
   .form-section-title { margin: 0; font-size: clamp(1.6rem, 3vw, 2.25rem); }
   .section-kicker { margin: 0 0 10px; color: #6b7b75; font-size: 0.78rem; font-weight: 800;
     text-transform: uppercase; letter-spacing: 0.08em; }
   .summary-banner { display: flex; align-items: end; justify-content: space-between;
     gap: 16px; margin-bottom: 16px; padding-bottom: 14px; border-bottom: 1px solid #e7e0d4; }
   .summary-banner h2 { margin: 0; font-size: clamp(1.15rem, 3vw, 1.8rem);
     line-height: 1.2; max-width: 72%; }
   .summary-banner .summary-meta { color: #5e6d67; font-weight: 700; }
   .summary-banner .settings-button {
     flex-shrink: 0; min-width: 150px; border-radius: 18px; background: #edf2ee;
     color: #17352c; border: 1px solid #cbd9d0; font-weight: 800;
     box-shadow: inset 0 0 0 1px rgba(20, 107, 77, 0.03);
   }
   .summary-banner .settings-button:hover,
   .summary-banner .settings-button:focus-visible {
     background: #e0eadf; border-color: #a7bdb0;
   }
   form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
     gap: 18px; align-items: start; }
   label { display: grid; gap: 7px; font-weight: 750; width: 100%; min-height: 90px; }
   .wide { grid-column: 1 / -1; }
   input, select, textarea { box-sizing: border-box; width: 100%; min-height: 46px;
     border: 1px solid #a7aea6; border-radius: 10px; padding: 11px 12px;
     background: #fff; color: #17352c; font: inherit; }
   textarea { min-height: 76px; resize: vertical; }
   button, .button { grid-column: 1 / -1; border: 0; border-radius: 999px;
     min-height: 48px; padding: 14px 22px; background: #146b4d; color: #fff; font: inherit;
     font-weight: 800; cursor: pointer; text-align: center; text-decoration: none;
     display: inline-flex; align-items: center; justify-content: center; }
   button:hover, .button:hover { background: #0f533c; }
   .button.secondary { background: #e7eee9; color: #17352c; }
   .action-button {
     border-radius: 16px; min-height: 52px; font-size: 1rem; box-shadow:
     inset 0 0 0 1px rgba(20, 107, 77, 0.08);
   }
   .actions { display: flex; justify-content: center; margin-top: 20px; }
   .actions .button { width: fit-content; }
   .hint { color: #5e6d67; font-size: 0.9rem; font-weight: 500; }
   .message { border-radius: 12px; margin-bottom: 18px; padding: 14px 16px; }
   .error { background: #fff0ed; border: 1px solid #d35b45; color: #812817; }
   .success { background: #e8f5ed; border: 1px solid #4a956f; color: #174f37; }
   .result { margin-top: 24px; }
   .plan-controls { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
     gap: 12px; margin: 18px 0 24px; }
   .plan-controls form { display: flex; margin: 0; }
   .plan-controls > button, .plan-controls form button {
       flex: 1 1 0; grid-column: auto; min-width: 0; border-radius: 16px;
       box-shadow: inset 0 0 0 1px rgba(20, 107, 77, 0.08);
   }
   .plan-controls form button { width: 100%; }
   @media (max-width: 760px) {
     .summary-banner { align-items: flex-start; flex-direction: column; }
     .summary-banner h2 { max-width: 100%; }
     .summary-banner .settings-button { width: 100%; }
     .plan-controls { grid-template-columns: 1fr; }
   }
   @media (max-width: 640px) {
     .food-rule-grid { grid-template-columns: 1fr; }
     .food-rule-input-row { flex-direction: column; align-items: stretch; }
   }
   .plan-overview { margin-bottom: 20px; }
   .overview-scroll { overflow-x: auto; padding-bottom: 10px; }
   .overview-grid { list-style: none; margin: 12px 0 0; padding: 0;
     display: grid; grid-auto-flow: column; grid-auto-columns: minmax(170px, 1fr);
     grid-template-columns: none; gap: 12px; min-width: 600px; }
   .meal-summary-card { background: #f7f6f1; border: 1px solid #d8d2c4;
     border-radius: 12px; padding: 14px; }
   .setting-row { display: grid; gap: 12px; border: 1px solid #d8d2c4;
     border-radius: 12px; background: #f9faf7; padding: 16px; }
   .setting-row-header { display: flex; justify-content: space-between; align-items: center;
     gap: 8px; }
   .setting-row-header h3 { margin: 0; font-size: 1.02rem; }
   .setting-row-note { color: #5e6d67; font-size: 0.82rem; font-weight: 700; }
   .food-rule-options { margin: 0; padding: 0; border: 0; }
   .food-rule-options legend { font-weight: 800; margin-bottom: 6px; }
   .food-rule-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
     gap: 10px; }
   .food-rule-choice { display: flex; align-items: center; gap: 10px; min-height: 46px;
     padding: 10px 12px; border: 1px solid #d8d2c4; border-radius: 10px; background: #fff; }
   .food-rule-choice input { width: 18px; height: 18px; min-height: 18px; padding: 0;
     border: 0; background: transparent; accent-color: #146b4d; }
   .food-rule-entry { display: grid; gap: 10px; }
   .food-rule-input-row { display: flex; gap: 10px; align-items: center; }
   .food-rule-input-row input { flex: 1 1 auto; }
   .food-rule-chip-list { display: flex; flex-wrap: wrap; gap: 8px; }
   .food-rule-chip-list .chip { display: inline-flex; align-items: center; }
   .food-rules-summary { margin: 0 0 18px; color: #5e6d67; }
   .pantry-editor { display: grid; gap: 14px; }
   .pantry-list { display: grid; gap: 10px; }
   .pantry-row { display: grid; grid-template-columns: auto minmax(0, 1.2fr) auto auto; gap: 8px;
     align-items: center; padding: 8px 10px; background: #fff; border: 1px solid #d8d2c4;
     border-radius: 10px; min-height: 62px; }
   .pantry-row-check { width: 18px; height: 18px; accent-color: #146b4d; margin: 0; }
   .pantry-row-main { display: grid; gap: 2px; min-width: 0; }
   .pantry-row-name { font-weight: 800; }
   .pantry-row-status { color: #5e6d67; font-size: 0.76rem; }
   .pantry-row-amounts { display: none; gap: 6px; align-items: center; justify-content: flex-end; min-width: 0; }
   .pantry-row-amounts.visible { display: grid; grid-template-columns: minmax(52px, 72px) minmax(62px, 82px); width: fit-content; }
   .pantry-row-amounts input, .pantry-row-amounts select {
     width: 100%; min-height: 32px; padding: 6px 8px; font-size: 0.85rem; border-radius: 8px;
   }
   .pantry-row button { border: 1px solid #bdd0c2; background: #edf6f1; border-radius: 999px;
     color: #17352c; font: inherit; font-weight: 700; padding: 6px 10px; cursor: pointer; }
   .pantry-row .remove-item { border-color: #cf8f7d; background: #fff0ed; color: #7a2a1c; }
   .pantry-row .remove-item:hover { background: #fce5df; }
   .pantry-suggestions { display: flex; flex-wrap: wrap; gap: 8px; }
   .chip { border: 1px solid #7ea292; background: #dfeee5; color: #17352c;
     border-radius: 999px; padding: 8px 12px; font: inherit; font-weight: 800;
     cursor: pointer; box-shadow: inset 0 0 0 1px rgba(20, 107, 77, 0.08); }
   .chip:hover, .chip:focus-visible { background: #cfe5d7; border-color: #4c7a67; outline: none; }
   .chip.selected { background: #146b4d; border-color: #0f533c; color: #fff; }
   .chip.selected:hover, .chip.selected:focus-visible { background: #0f533c; border-color: #0b3f30; }
   .detail-toggle { width: 100%; }
   .advanced-details { display: none; }
   .advanced-details.visible { display: grid; }
   .detail-cta { margin-top: 8px; }
   details { grid-column: 1 / -1; }
   details summary { cursor: pointer; font-weight: 800; }
   details .detail-body { padding-top: 12px; }
   .meal-summary-card h3 { font-size: 1.02rem; margin-bottom: 4px; }
   .meal-kicker { margin: 0 0 8px; font-size: 0.76rem; font-weight: 800;
     letter-spacing: 0.04em; text-transform: uppercase; color: #5e6d67; }
   .meal-meta { display: flex; justify-content: space-between; align-items: center; gap: 10px;
     font-size: 0.9rem; }
   .meal-meta strong { font-weight: 800; }
   .meal-list { display: grid; gap: 16px; }
   .meal-card { background: #f9faf7; border: 1px solid #d8d2c4; border-radius: 14px;
     padding: 16px; }
   .meal-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
   .meal-header h3 { margin: 0; font-size: 1.2rem; }
   .meal-pill { background: #e7eee9; border: 1px solid #bdd0c2; border-radius: 999px;
     display: inline-flex; align-items: center; padding: 6px 10px; font-size: 0.8rem;
     font-weight: 800; color: #17352c; }
   .meal-toggle { grid-column: auto; margin-top: 14px; padding: 10px 14px; border-radius: 10px; }
   .meal-details { margin-top: 14px; padding-top: 14px; border-top: 1px solid #d8d2c4; }
   .meal-details[hidden] { display: none; }
   .meal-details .subhead { margin: 16px 0 8px; font-size: 0.96rem; }
   .meal-details ul, .meal-details ol { margin: 0; padding-left: 1.25rem; }
   .meal-details li + li { margin-top: 6px; }
   .meal-note { margin-top: 14px; padding: 12px 14px; border-radius: 10px;
     background: #eef7f3; border: 1px solid #bfd8c8; color: #17352c; }
   .estimate-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
   .estimate-table th, .estimate-table td {
       border-bottom: 1px solid #d8d2c4; padding: 10px 8px; text-align: left;
       vertical-align: top;
   }
   .estimate-table th { color: #5e6d67; font-size: 0.85rem; text-transform: uppercase; }
   .estimate-table td:last-child, .estimate-table th:last-child { text-align: right; }
   .budget-status { border-radius: 10px; margin: 0 0 20px; padding: 12px 14px; }
   .budget-status.good { background: #e8f5ed; color: #174f37; }
   .budget-status.warning { background: #fff0ed; border: 1px solid #d35b45; color: #812817; }
   .budget-status.neutral { background: #f5f2e9; color: #5e6d67; }
   .plan-details { border-top: 1px solid #d8d2c4; padding: 14px 0; }
   .plan-details summary { cursor: pointer; font-weight: 800; }
   pre { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere;
     font-family: inherit; line-height: 1.55; }
   footer { color: #5e6d67; margin-top: 20px; font-size: 0.9rem; }
   .actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 18px; }
   .actions form { display: block; }
   .actions button, .actions .button { display: inline-block; }
   .export-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
   .export-actions form { display: inline; }
   .copy-status { flex-basis: 100%; min-height: 1.2em; color: #5e6d67;
     font-size: 0.9rem; }
   .form-section-title { grid-column: 1 / -1; margin: 0; font-size: 1.05rem; }
   .details-group { grid-column: 1 / -1; display: grid;
     grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
   .json-editor { min-height: 520px; font-family: Consolas, monospace;
     font-size: 0.9rem; line-height: 1.45; }
   details { margin-top: 20px; }
   code { background: #edf1ed; border-radius: 5px; padding: 2px 5px; }
   @media (max-width: 640px) {
     form, .details-group { grid-template-columns: 1fr; }
     .wide, button { grid-column: 1; }
     .plan-controls { display: grid; }
     .plan-controls form { display: grid; }
     .plan-controls > button, .plan-controls form button { grid-column: 1; }
     .meal-header { display: grid; }
   }
   @media print {
     body { background: #fff; color: #000; }
     main { width: auto; margin: 0; }
     header, .card, .actions, .export-actions, footer { display: none; }
     .result { border: 0; box-shadow: none; padding: 0; margin: 0; }
     .meal-toggle, [data-expand-all] { display: none; }
     .meal-details { display: block !important; }
     pre { color: #000; font-size: 11pt; line-height: 1.35; }
   }
"""


def _split_items(value: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"[\r\n,]+|\s+and\s+", value, flags=re.IGNORECASE)
        if item.strip()
    ]


def _parse_quantity(value: str, unit: str, field_name: str) -> int:
    clean_value = value.strip()
    if not re.fullmatch(r"\d+", clean_value):
        raise ValueError(f"Enter a valid number of {unit}.")
    parsed = parse_request(f"{clean_value} {unit}")
    quantity = getattr(parsed, field_name)
    if quantity is None:
        raise ValueError(f"Enter a valid number of {unit}.")
    return quantity


def _resolve_preferences(value: str) -> list[str]:
    food_names = _split_items(value)
    if not food_names:
        return []
    catalog = load_effective_price_catalog()
    try:
        return list(resolve_product_keys(food_names, catalog.products))
    except ValueError as error:
        message = str(error)
        prefix = "Unknown food preference: "
        if message.startswith(prefix):
            unknown_names = message[len(prefix) :].rstrip(".")
            first_unknown = unknown_names.split(",")[0].strip()
            raise ValueError(
                f"We can't reliably filter \"{first_unknown}\" yet. Try a more general ingredient."
            ) from error
        raise


def _selected_dietary_restrictions(form: Mapping[str, str]) -> list[str]:
    selected = [
        canonical
        for field_name, _, canonical in DIETARY_RULE_OPTIONS
        if form.get(field_name)
    ]
    if selected:
        return selected

    legacy_value = form.get("dietary_restrictions", "").strip()
    if not legacy_value or legacy_value.casefold() == "none":
        return []
    return [legacy_value]


def _food_rule_summary(form: Mapping[str, str]) -> str:
    items: list[str] = []
    selected_restrictions = _selected_dietary_restrictions(form)
    try:
        for restriction in normalize_food_rule_values(selected_restrictions):
            items.append(DIETARY_RULE_LABELS[restriction])
    except ValueError:
        for restriction in selected_restrictions:
            display = restriction.strip().replace("_", " ").replace("-", " ")
            if display:
                items.append(display.title())
    for food_name in _split_items(form.get("foods_to_avoid", "")):
        items.append(f"no {food_name.casefold()}")
    return ", ".join(items) if items else "none"


def _render_form_values(form: Mapping[str, str], request: ParsedRequest) -> dict[str, str]:
    render_values = dict(form)
    for field_name, _, canonical in DIETARY_RULE_OPTIONS:
        if canonical in request.dietary_restrictions:
            render_values[field_name] = "on"
        else:
            render_values.pop(field_name, None)

    products = {
        product.key: product.name
        for product in load_effective_price_catalog().products
    }
    render_values["foods_to_avoid"] = "\n".join(
        products.get(product_key, product_key)
        for product_key in request.avoided_product_keys or ()
    )
    render_values["foods_to_prefer"] = "\n".join(
        products.get(product_key, product_key)
        for product_key in request.preferred_product_keys or ()
    )
    return render_values


def build_request(form: Mapping[str, str]) -> ParsedRequest:
    """Build and validate one planning request from browser form values."""
    budget_text = form.get("budget", "").strip()
    budget: float | None = None
    if budget_text:
        if not re.fullmatch(r"\d+(?:[.,]\d{1,2})?", budget_text):
            raise ValueError("Enter a valid budget in CAD.")
        parsed_budget = parse_request(f"CAD${budget_text}")
        if parsed_budget.budget is None or parsed_budget.budget <= 0:
            raise ValueError("Enter a budget greater than zero.")
        budget = parsed_budget.budget

    people = _parse_quantity(form.get("people", ""), "people", "people")
    days = _parse_quantity(form.get("days", ""), "days", "days")
    if not 1 <= people <= 12:
        raise ValueError("People must be between 1 and 12.")
    if not 1 <= days <= 14:
        raise ValueError("Days must be between 1 and 14.")

    cooking_energy = form.get("cooking_energy", "").strip().casefold()
    if cooking_energy not in {"low", "normal", "high"}:
        raise ValueError("Choose low, normal, or high cooking energy.")

    try:
        restrictions = list(
            normalize_food_rule_values(_selected_dietary_restrictions(form))
        )
    except ValueError as error:
        raise ValueError("Choose a supported dietary restriction.") from error

    avoided_keys = _resolve_preferences(form.get("foods_to_avoid", ""))
    preferred_keys = _resolve_preferences(form.get("foods_to_prefer", ""))
    if set(avoided_keys).intersection(preferred_keys):
        raise ValueError(
            "The same food cannot be both used less often and used more often."
        )

    return ParsedRequest(
        budget=budget,
        currency="CAD",
        people=people,
        days=days,
        cooking_energy=cooking_energy,
        pantry_items=_split_items(form.get("pantry_items", "")),
        dietary_restrictions=restrictions,
        avoided_product_keys=avoided_keys,
        preferred_product_keys=preferred_keys,
    )

def create_plan(
    form: Mapping[str, str],
    request: ParsedRequest | None = None,
) -> Plan:
    """Create one deterministic plan or raise a friendly validation error."""
    request = request or build_request(form)
    try:
        meal_candidate_keys = suggest_meal_candidate_keys(
            request,
            select_meal_candidate_templates(request),
        )
    except LLMSelectorError as error:
        raise ValueError(
            f"Optional LLM meal selection is not available: {error}"
        ) from error
    except ValueError:
        meal_candidate_keys = None

    plan = generate_plan(request, meal_candidate_keys=meal_candidate_keys)
    if plan is None:
        raise ValueError("Carrinho could not create a plan from these values.")
    return plan


def _hidden_form_fields(values: Mapping[str, str]) -> str:
    fields = [("csrf_token", CSRF_TOKEN)]
    fields.extend(
        (name, values.get(name, ""))
        for name in (
            "budget",
            "people",
            "days",
            "cooking_energy",
            "pantry_items",
            "dietary_restrictions",
            "dietary_lactose_intolerance",
            "dietary_vegetarian",
            "dietary_vegan",
            "dietary_avoid_gluten_ingredients",
            "foods_to_avoid",
            "foods_to_prefer",
        )
    )
    return "\n".join(
        f'<input type="hidden" name="{escape(name, quote=True)}" '
        f'value="{escape(value, quote=True)}">'
        for name, value in fields
    )


def _selected(value: str, expected: str) -> str:
    return " selected" if value == expected else ""


def _checked(values: Mapping[str, str], field_name: str) -> str:
    return " checked" if values.get(field_name) else ""


def _format_money(currency: str, value: float) -> str:
    prefixes = {"CAD": "CAD$", "USD": "US$", "BRL": "R$"}
    prefix = prefixes.get(currency, f"{currency} ")
    return f"{prefix}{value:.2f}"


def render_page(
    values: Mapping[str, str] | None = None,
    plan: Plan | None = None,
    error: str | None = None,
) -> str:
    """Render the complete standalone page without external assets."""
    form = values or {}

    def value(name: str, default: str = "") -> str:
        return escape(form.get(name, default), quote=True)

    cooking_energy = form.get("cooking_energy", "normal")
    food_rules_summary = _food_rule_summary(form)
    error_html = (
        f'<div class="message error" role="alert">{escape(error)}</div>'
        if error
        else ""
    )
    result_html = ""
    if plan is not None:
        # Render the plan as structured HTML so recipe guidance is visible and interactive
        hidden_fields = _hidden_form_fields(form)
        # Build per-meal HTML
        products_by_key = {p.key: p.name for p in load_effective_price_catalog().products}
        overview_parts = []
        meals_parts = []
        for index, meal in enumerate(plan.meals):
            template = plan.meal_templates[index]
            meal_id = f"meal-{index}"
            overview_parts.append(
                f'<li class="meal-summary-card">'
                f'<p class="meal-kicker">Day {meal.day}</p>'
                f'<h3>{escape(meal.dish)}</h3>'
                f'<div class="meal-meta"><span>{escape(meal.meal_slot)}</span>'
                f'<strong>{escape(meal.difficulty.title())}</strong></div>'
                f'</li>'
            )

            ing_items = []
            for ingredient in template.ingredients:
                product_name = products_by_key.get(ingredient.product_key, ingredient.product_key)
                required_quantity = ingredient.quantity_per_person * plan.people
                qty_label = format_planning_quantity(
                    required_quantity,
                    ingredient.planning_unit,
                    product_name,
                )
                ing_items.append(
                    f"<li>{escape(product_name)} — need {escape(qty_label)}</li>"
                )
            ing_html = "\n".join(ing_items) or "<li>None</li>"

            step_items = []
            for step in meal.instructions:
                step_items.append(f"<li>{escape(step)}</li>")
            steps_html = "\n".join(step_items) or "<li>No steps provided.</li>"

            prev_html = ""
            if "leftover" in template.selection_tags and plan.pantry_usage:
                prev_html = (
                    '<div class="meal-note">'
                    '<strong>Previously prepared:</strong> '
                    'This meal is already positioned for a leftover-friendly reuse within the plan. '
                    'Read the meal guidance section for the relevant notes and portions.'
                    '</div>'
                )

            meals_parts.append(
                f'<article class="meal-card" id="{meal_id}">'
                f'<div class="meal-header">'
                f'<div>'
                f'<p class="meal-kicker">Day {meal.day} • {escape(meal.meal_slot)}</p>'
                f'<h3>{escape(meal.dish)}</h3>'
                f'</div>'
                f'<span class="meal-pill">{escape(meal.difficulty.title())}</span>'
                f'</div>'
                f'<button type="button" class="meal-toggle" '
                f'aria-expanded="false" aria-controls="{meal_id}-details" '
                f'data-target="{meal_id}-details" '
                f'data-label-expanded="Hide details" '
                f'data-label-collapsed="Open details">Open details</button>'
                f'<div id="{meal_id}-details" class="meal-details" hidden>'
                f'<p><strong>Meal slot:</strong> {escape(meal.meal_slot)}</p>'
                f'<p><strong>Difficulty:</strong> {escape(meal.difficulty.title())}</p>'
                f'<h4 class="subhead">Ingredients for {plan.people} people</h4>'
                f'<ul>{ing_html}</ul>'
                f'<h4 class="subhead">Cooking steps</h4>'
                f'<ol>{steps_html}</ol>'
                f'{prev_html}'
                f'</div>'
                f'</article>'
            )
        overview_html = "\n".join(overview_parts)
        meals_html = "\n".join(meals_parts)

        # Shopping list HTML
        shop_parts = []
        estimate_parts = []
        for item in plan.shopping_items:
            required_quantity = format_planning_quantity(item.required_quantity, item.planning_unit, item.name)
            purchase_quantity = format_planning_quantity(item.purchase_quantity, item.planning_unit, item.name)
            if item.variable_weight:
                quantity_details = f"need {required_quantity}; plan about {purchase_quantity}; actual package weight may be higher or lower"
            elif item.overage_quantity > 0.000001:
                overage_quantity = format_planning_quantity(item.overage_quantity, item.planning_unit, item.name)
                quantity_details = f"need {required_quantity}; buy {purchase_quantity}; {overage_quantity} extra"
            else:
                quantity_details = f"need {required_quantity}; buy {purchase_quantity}"
            shop_parts.append(
                f'<li><strong>{escape(item.name)}</strong>: '
                f'{escape(item.quantity_label)}</li>'
            )
            item_price_min = _format_money(plan.currency, item.estimated_price_min)
            item_price_max = _format_money(plan.currency, item.estimated_price_max)
            estimate_parts.append(
                f'<tr><td>{escape(item.name)}</td>'
                f'<td>{escape(item.quantity_label)}</td>'
                f'<td>{escape(item_price_min)} to {escape(item_price_max)}</td></tr>'
            )
        shopping_html = "\n".join(shop_parts) or "<li>None</li>"
        estimates_html = "\n".join(estimate_parts) or "<tr><td colspan=\"3\">None</td></tr>"

        estimated_total_min = _format_money(plan.currency, plan.estimated_total_min)
        estimated_total_max = _format_money(plan.currency, plan.estimated_total_max)
        display_price_description = (
            plan.price_description.replace("Simulated", "Canadian")
            .replace("simulated", "Canadian")
        )

        if plan.budget_balance is None:
            budget_summary = "<p><strong>Budget:</strong> No budget provided.</p>"
            budget_note = (
                "<p>Budget note: this is a local planning estimate range only; "
                "it is not a live retailer quote or current store price.</p>"
            )
        elif plan.budget_balance >= 0:
            budget_balance_min = _format_money(plan.currency, plan.budget_balance_min)
            budget_balance_max = _format_money(plan.currency, plan.budget_balance_max)
            budget_summary = (
                f"<p><strong>Budget balance range:</strong> {escape(budget_balance_min)} to {escape(budget_balance_max)}</p>"
            )
            budget_note = (
                "<p>Budget note: this is a local planning estimate range only; "
                "it is not a live retailer quote or current store price.</p>"
            )
        else:
            budget_shortfall_min = _format_money(plan.currency, abs(plan.budget_balance_max))
            budget_shortfall_max = _format_money(plan.currency, abs(plan.budget_balance_min))
            budget_summary = (
                f"<p><strong>Budget shortfall range:</strong> {escape(budget_shortfall_min)} to {escape(budget_shortfall_max)}</p>"
            )
            budget_note = (
                "<p>Budget note: this is a local planning estimate range only; "
                "it is not a live retailer quote or current store price.</p>"
            )

        if plan.budget_balance is None:
            budget_status = '<p class="budget-status neutral"><strong>Budget:</strong> No budget provided.</p>'
        elif plan.budget_balance >= 0:
            budget_status = (
                f'<p class="budget-status good"><strong>Budget check:</strong> '
                f'within budget, with {escape(budget_balance_min)} to '
                f'{escape(budget_balance_max)} remaining.</p>'
            )
        else:
            budget_status = (
                f'<p class="budget-status warning"><strong>Budget check:</strong> '
                f'this plan is over budget by {escape(budget_shortfall_min)} to '
                f'{escape(budget_shortfall_max)}. Review the plan or increase the budget.</p>'
            )

        pantry_html = (
            "<ul>"
            + "\n".join(f"<li>{escape(item)}</li>" for item in plan.pantry_usage)
            + "</ul>"
            if plan.pantry_usage
            else "<p>No main ingredient from the plan was identified at home.</p>"
        )

        summary_label = {
            "low": "Low cooking",
            "normal": "Everyday cooking",
            "high": "Enjoy cooking",
        }.get(cooking_energy, "Everyday cooking")
        pantry_count = len(plan.pantry_usage)
        result_summary = (
            '<div class="summary-banner">'
            + f'<div><div class="summary-meta">Plan summary</div>'
            + f'<h2>{plan.people} people · {plan.days} days · {escape(summary_label)} · {pantry_count} pantry items</h2></div>'
            + '<button type="button" class="button secondary settings-button" data-toggle-plan-form>Edit settings</button>'
            + '</div>'
        )
        result_html_parts = [
            '<section class="result" aria-live="polite">',
            result_summary,
            f'<p class="food-rules-summary"><strong>Food rules applied:</strong> {escape(food_rules_summary)}</p>',
            '<h2 id="plan-focus">Your weekly plan</h2>',
            budget_status,
            '<div class="plan-controls">',
            '<button type="button" class="action-button" data-copy-target="plan-output">Copy plan</button>',
            '<button type="button" class="action-button" data-print-plan>Print plan</button>',
            f'<form method="post" action="/download/plan">{hidden_fields}<button type="submit" class="action-button">Download plan text</button></form>',
            f'<form method="post" action="/download/instacart-paste-list">{hidden_fields}<button type="submit" class="action-button">Download Instacart paste list</button></form>',
            f'<form method="post" action="/download/instacart-json">{hidden_fields}<button type="submit" class="action-button">Download Instacart JSON preview</button></form>',
            '</div>',
            '<div id="plan-output" class="plan-output">',
            '<section class="plan-overview" aria-label="Weekly overview">',
            '<h3>Weekly overview</h3>',
            '<div class="overview-scroll">',
            f'<ul class="overview-grid">{overview_html}</ul>',
            '</div>',
            '</section>',
            '<section class="meal-list" aria-label="Meal details">',
            meals_html,
            '</section>',
            '<button type="button" data-expand-all="meal-details" aria-expanded="false">Expand all</button>',
            '<details class="plan-details">',
            '<summary>Meal guidance</summary>',
            '<h3>Meal selection guidance</h3>',
            f'<pre>{escape("\\n".join(plan.meal_selection_guidance))}</pre>',
            '<h3>Meal prep guidance</h3>',
            f'<pre>{escape("\\n".join(plan.meal_prep_guidance))}</pre>',
            '</details>',
            '<section class="shopping-list"><h3>Shopping list</h3>',
            f'<ul>{shopping_html}</ul>',
            '</section>',
            '<details class="plan-details">',
            '<summary>Budget + estimated prices</summary>',
            f'<p><strong>Total range:</strong> {escape(estimated_total_min)} to {escape(estimated_total_max)}</p>',
            budget_summary,
            budget_note,
            '<h3>Estimated price ranges</h3>',
            '<table class="estimate-table">',
            '<thead><tr><th>Ingredient</th><th>Quantity</th><th>Estimated range</th></tr></thead>',
            f'<tbody>{estimates_html}</tbody>',
            '</table>',
            f'<p><strong>Planning estimate source:</strong> {escape(display_price_description)} (retailer-neutral Canadian price catalogue for planning only)</p>',
            '</details>',
            '<details class="plan-details">',
            '<summary>Pantry items from home</summary>',
            pantry_html,
            '</details>',
            '</div>',
            '<div class="copy-status" role="status" aria-live="polite"></div>',
            '</section>',
            f'<script nonce="{CSRF_TOKEN}">',
            'const mealButtons = document.querySelectorAll(".meal-toggle"); ',
            'const expandAllButton = document.querySelector("[data-expand-all]"); ',
            'function syncMealToggle(button, target, isExpanded) { ',
            'if (!button || !target) return; ',
            'button.setAttribute("aria-expanded", String(isExpanded)); ',
            'button.textContent = isExpanded ? button.dataset.labelExpanded : button.dataset.labelCollapsed; ',
            'target.hidden = !isExpanded; ',
            '} ',
            'for (const button of mealButtons) { ',
            'const target = document.getElementById(button.dataset.target); ',
            'button.addEventListener("click", () => { ',
            'const isExpanded = target.hidden; ',
            'for (const otherButton of mealButtons) { ',
            'const otherTarget = document.getElementById(otherButton.dataset.target); ',
            'if (otherButton === button) continue; ',
            'syncMealToggle(otherButton, otherTarget, false); ',
            '} ',
            'syncMealToggle(button, target, isExpanded); ',
            'if (expandAllButton) { ',
            'const allOpen = [...document.querySelectorAll(".meal-details")].every((detail) => !detail.hidden); ',
            'expandAllButton.setAttribute("aria-expanded", String(allOpen)); ',
            'expandAllButton.textContent = allOpen ? "Collapse all" : "Expand all"; ',
            '} ',
            '}); ',
            '} ',
            'if (expandAllButton) { ',
            'expandAllButton.addEventListener("click", () => { ',
            'const anyHidden = [...document.querySelectorAll(".meal-details")].some((detail) => detail.hidden); ',
            'for (const button of mealButtons) { ',
            'const target = document.getElementById(button.dataset.target); ',
            'syncMealToggle(button, target, anyHidden); ',
            '} ',
            'expandAllButton.setAttribute("aria-expanded", String(anyHidden)); ',
            'expandAllButton.textContent = anyHidden ? "Collapse all" : "Expand all"; ',
            '}); ',
            '} ',
            'const planFocus = document.getElementById("plan-focus"); ',
            'if (planFocus) { planFocus.scrollIntoView({ behavior: "smooth", block: "start" }); planFocus.focus(); } ',
            'const editSettingsButton = document.querySelector("[data-toggle-plan-form]"); ',
            'const plannerFormCard = document.querySelector("form[action=\'/plan\']").closest(".card"); ',
            'if (editSettingsButton && plannerFormCard) { ',
            '  editSettingsButton.addEventListener("click", () => { ',
            '    plannerFormCard.scrollIntoView({ behavior: "smooth", block: "start" }); ',
            '    const formInputs = plannerFormCard.querySelectorAll("input, select, textarea, button"); ',
            '    if (formInputs.length) formInputs[0].focus(); ',
            '  }); ',
            '} ',
            '</script>',
        ]
        result_html = "".join(result_html_parts)

    return f"""<!doctype html>
<html lang="en-CA">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Carrinho</title>
  <style>
{PAGE_STYLES}
  </style>
</head>
<body>
  <main>
    <header class="page-intro">
      <div class="eyebrow">Canadian grocery planning</div>
      <h1>Carrinho</h1>
      <p>Start with people and days. Add details only when they matter.</p>
    </header>
    {error_html}
    <section class="card">
      <form method="post" action="/plan">
        <input type="hidden" name="csrf_token" value="{CSRF_TOKEN}">
        <div class="wide">
          <p class="section-kicker">Quick start</p>
          <h2 class="form-section-title">Plan your week</h2>
        </div>
        <p class="hint wide">Tell us the minimum. You can customize more if you want.</p>
        <label>People
          <input name="people" type="number" min="1" max="12" required
            value="{value('people', '2')}">
        </label>
        <label>Days
          <input name="days" type="number" min="1" max="14" required
            value="{value('days', '4')}">
        </label>
        <label class="wide">Target grocery budget
          <input name="budget" inputmode="decimal" value="{value('budget')}" placeholder="CAD$ 120">
          <span class="hint">Used only to compare the simulated plan estimate with your target.</span>
        </label>
        <label class="wide">Cooking energy
          <select name="cooking_energy">
            <option value="low"{_selected(cooking_energy, 'low')}>Low — meals under 20 minutes</option>
            <option value="normal"{_selected(cooking_energy, 'normal')}>Normal — everyday cooking</option>
            <option value="high"{_selected(cooking_energy, 'high')}>Enjoy cooking — more prep is okay</option>
          </select>
        </label>
        <div class="setting-row wide">
          <div class="setting-row-header">
            <h3>Pantry</h3>
            <span class="setting-row-note">Check + quantity</span>
          </div>
          <div class="pantry-editor">
            <div class="pantry-suggestions" aria-label="Pantry quick adds">
              <button type="button" class="chip" data-pantry-chip="rice">Rice</button>
              <button type="button" class="chip" data-pantry-chip="eggs">Eggs</button>
              <button type="button" class="chip" data-pantry-chip="pasta">Pasta</button>
              <button type="button" class="chip" data-pantry-chip="oil">Oil</button>
              <button type="button" class="chip" data-pantry-chip="beans">Beans</button>
            </div>
            <div class="pantry-list" id="pantry-list" aria-live="polite"></div>
            <label class="wide">Pantry text list
              <textarea id="pantry_items_fallback" rows="3" placeholder="Rice, 7 eggs">{value('pantry_items')}</textarea>
              <span class="hint">Quick text backup. The checked list is the main editor.</span>
            </label>
            <label class="wide">Audio transcript or spoken note
              <textarea id="pantry_transcript" rows="2" placeholder="Example: 'I have rice, two bags of beans, and six eggs'"></textarea>
              <span class="hint">Optional third method: paste a spoken note or transcript to add pantry items in text.</span>
            </label>
          </div>
          <textarea id="pantry_items" name="pantry_items" hidden>{value('pantry_items')}</textarea>
        </div>
        <div class="setting-row wide">
          <div class="setting-row-header">
            <h3>Food rules</h3>
            <span class="setting-row-note">Applies before ranking</span>
          </div>
          <p class="hint">Tell us about dietary needs and foods you want left out.</p>
          <fieldset class="food-rule-options">
            <legend>Dietary needs</legend>
            <p class="hint">Choose any that apply.</p>
            <div class="food-rule-grid">
              <label class="food-rule-choice">
                <input type="checkbox" name="dietary_lactose_intolerance"{_checked(form, 'dietary_lactose_intolerance')}>
                <span>Lactose intolerance</span>
              </label>
              <label class="food-rule-choice">
                <input type="checkbox" name="dietary_vegetarian"{_checked(form, 'dietary_vegetarian')}>
                <span>Vegetarian</span>
              </label>
              <label class="food-rule-choice">
                <input type="checkbox" name="dietary_vegan"{_checked(form, 'dietary_vegan')}>
                <span>Vegan</span>
              </label>
              <label class="food-rule-choice">
                <input type="checkbox" name="dietary_avoid_gluten_ingredients"{_checked(form, 'dietary_avoid_gluten_ingredients')}>
                <span>Avoid gluten ingredients</span>
              </label>
            </div>
          </fieldset>
          <div class="food-rule-entry">
            <label class="wide">Foods to avoid
              <div class="food-rule-input-row">
                <input id="foods_to_avoid_input" type="text" placeholder="Coconut or mushrooms">
                <button type="button" class="chip" data-food-rule-add>Add food</button>
              </div>
            </label>
            <div id="foods-to-avoid-list" class="food-rule-chip-list" aria-live="polite"></div>
            <textarea id="foods_to_avoid" name="foods_to_avoid" hidden>{value('foods_to_avoid')}</textarea>
          </div>
          <p class="hint">Carrinho uses available ingredient information to filter meals. Always check product labels for allergies or medical dietary needs.</p>
        </div>
        <button type="submit" class="button detail-cta">Create my meal plan</button>
      </form>
    </section>
    {result_html}
    <div class="actions">
      <a class="button secondary" href="/customize">Manage local meals and foods</a>
    </div>
    <footer>Runs only on this computer. No request is sent to Instacart or another
      service.</footer>
  </main>
  <script nonce="{CSRF_TOKEN}">
    for (const button of document.querySelectorAll("[data-copy-target]")) {{
      button.addEventListener("click", async () => {{
        const target = document.getElementById(button.dataset.copyTarget);
        const status = button.parentElement.querySelector(".copy-status");
        try {{
          await navigator.clipboard.writeText(target.innerText);
          status.textContent = "Plan copied to clipboard.";
        }} catch {{
          status.textContent = "Copy was not available. Select the plan text manually.";
        }}
      }});
    }}
    for (const button of document.querySelectorAll("[data-print-plan]")) {{
      button.addEventListener("click", () => window.print());
    }}
    const pantryForm = document.querySelector("form[action='/plan']");
    const pantryTextArea = document.getElementById("pantry_items");
    const pantryFallback = document.getElementById("pantry_items_fallback");
    const pantryTranscript = document.getElementById("pantry_transcript");
    const pantryList = document.getElementById("pantry-list");
    const pantryUnits = ['kg', 'g', 'ml', 'L', 'cups', 'cans', 'boxes', 'bags', 'dozens', 'eggs'];

    function splitPantryEntries(rawValue) {{
      return Array.from(new Set(
        (rawValue || '')
          .split(/[\\r\\n,]+|\\s+and\\s+/i)
          .map((entry) => entry.trim())
          .filter(Boolean)
      ));
    }}

    function parsePantryEntry(rawEntry) {{
      const entry = (rawEntry || '').trim();
      if (!entry) return {{ name: '', quantity: '', unit: '' }};
      const quantityMatch = entry.match(/^(.+?)\\s+(\\d+(?:\\.\\d+)?)\\s+([a-zA-Z/]+)$/);
      if (quantityMatch) {{
        return {{
          name: quantityMatch[1].trim(),
          quantity: quantityMatch[2],
          unit: quantityMatch[3].trim(),
        }};
      }}
      const simpleQuantityMatch = entry.match(/^(\\d+(?:\\.\\d+)?)\\s+(.+)$/);
      if (simpleQuantityMatch) {{
        return {{
          name: simpleQuantityMatch[2].trim(),
          quantity: simpleQuantityMatch[1],
          unit: '',
        }};
      }}
      return {{ name: entry, quantity: '', unit: '' }};
    }}

    function rowEntryString(row) {{
      const checked = row.querySelector('input[type="checkbox"]');
      if (checked && !checked.checked) return '';
      const name = row.dataset.name || '';
      const quantityInput = row.querySelector('input[type="number"]');
      const unitSelect = row.querySelector('select');
      const quantity = quantityInput ? quantityInput.value.trim() : '';
      const unit = unitSelect ? unitSelect.value.trim() : '';
      if (quantity && unit) return `${{name}} ${{quantity}} ${{unit}}`;
      if (quantity) return `${{name}} ${{quantity}}`;
      return name;
    }}

    function applyPantryEntry(row, parsed) {{
      row.dataset.name = parsed.name;
      row.className = 'pantry-row';

      const checkInput = document.createElement('input');
      checkInput.type = 'checkbox';
      checkInput.checked = true;
      checkInput.className = 'pantry-row-check';
      checkInput.setAttribute('aria-label', `Include ${{parsed.name}} in the pantry`);

      const main = document.createElement('div');
      main.className = 'pantry-row-main';
      const nameEl = document.createElement('div');
      nameEl.className = 'pantry-row-name';
      nameEl.textContent = parsed.name;
      const statusEl = document.createElement('div');
      statusEl.className = 'pantry-row-status';
      if (parsed.quantity) {{
        statusEl.textContent = `${{parsed.quantity}} ${{parsed.unit || 'unit'}}`;
      }} else {{
        statusEl.textContent = 'Enough for this plan';
      }}
      main.appendChild(nameEl);
      main.appendChild(statusEl);

      const amountGroup = document.createElement('div');
      amountGroup.className = 'pantry-row-amounts';
      if (parsed.quantity) amountGroup.classList.add('visible');

      const qtyInput = document.createElement('input');
      qtyInput.type = 'number';
      qtyInput.min = '0';
      qtyInput.step = '1';
      qtyInput.value = parsed.quantity || '';
      qtyInput.placeholder = 'qty';

      const unitSelect = document.createElement('select');
      for (const unit of pantryUnits) {{
        const option = document.createElement('option');
        option.value = unit;
        option.textContent = unit;
        if (unit === (parsed.unit || '')) option.selected = true;
        unitSelect.appendChild(option);
      }}
      amountGroup.appendChild(qtyInput);
      amountGroup.appendChild(unitSelect);

      const removeButton = document.createElement('button');
      removeButton.type = 'button';
      removeButton.className = 'remove-item';
      removeButton.textContent = 'Remove';

      checkInput.addEventListener('change', () => {{
        syncPantryListValue();
      }});
      qtyInput.addEventListener('input', syncPantryListValue);
      unitSelect.addEventListener('change', syncPantryListValue);
      removeButton.addEventListener('click', () => {{
        row.remove();
        syncPantryListValue();
      }});

      row.appendChild(checkInput);
      row.appendChild(main);
      row.appendChild(amountGroup);
      row.appendChild(removeButton);
      row.dataset.name = parsed.name;
    }}

    function syncPantryList() {{
      if (!pantryList) return;
      pantryList.innerHTML = '';
      const entries = splitPantryEntries((pantryFallback && pantryFallback.value) || (pantryTextArea && pantryTextArea.value) || '');
      for (const entry of entries) {{
        const parsed = parsePantryEntry(entry);
        if (!parsed.name) continue;
        const row = document.createElement('div');
        applyPantryEntry(row, parsed);
        pantryList.appendChild(row);
      }}
    }}

    function syncPantryListValue() {{
      if (!pantryList || !pantryTextArea) return;
      const rows = Array.from(pantryList.querySelectorAll('.pantry-row'));
      const deduped = [];
      const seen = new Set();
      for (const row of rows) {{
        const stringValue = rowEntryString(row);
        const key = stringValue.trim().toLowerCase();
        if (!key || seen.has(key)) continue;
        seen.add(key);
        deduped.push(stringValue.trim());
      }}
      const value = deduped.join('\\n');
      pantryTextArea.value = value;
      if (pantryFallback) pantryFallback.value = value;
    }}

    function mergeTranscriptToPantry() {{
      if (!pantryTranscript) return;
      const transcript = pantryTranscript.value.trim();
      if (!transcript) return;
      const entries = splitPantryEntries(transcript);
      const current = splitPantryEntries((pantryFallback && pantryFallback.value) || (pantryTextArea && pantryTextArea.value) || '');
      const merged = Array.from(new Set([...current, ...entries])).join('\\n');
      if (pantryFallback) pantryFallback.value = merged;
      if (pantryTextArea) pantryTextArea.value = merged;
      syncPantryList();
    }}

    if (pantryForm && pantryTextArea) {{
      pantryForm.addEventListener('submit', () => {{
        syncPantryListValue();
      }});
    }}

    if (pantryFallback) {{
      pantryFallback.addEventListener('input', () => {{
        syncPantryListValue();
        syncPantryList();
      }});
    }}

    if (pantryTranscript) {{
      pantryTranscript.addEventListener('change', mergeTranscriptToPantry);
      pantryTranscript.addEventListener('blur', mergeTranscriptToPantry);
    }}

    for (const chip of document.querySelectorAll('[data-pantry-chip]')) {{
      chip.addEventListener('click', () => {{
        const item = chip.dataset.pantryChip;
        const existing = splitPantryEntries((pantryFallback && pantryFallback.value) || (pantryTextArea && pantryTextArea.value) || '');
        const selected = existing.includes(item);
        const next = selected
          ? existing.filter((entry) => entry.trim().toLowerCase() !== item.trim().toLowerCase())
          : [...existing, item];
        const unique = Array.from(new Set(next.map((entry) => entry.trim()).filter(Boolean)));
        if (pantryFallback) pantryFallback.value = unique.join('\\n');
        if (pantryTextArea) pantryTextArea.value = unique.join('\\n');
        chip.classList.toggle('selected', !selected);
        syncPantryList();
      }});
    }}

    for (const chip of document.querySelectorAll('[data-pantry-chip]')) {{
      const item = chip.dataset.pantryChip;
      const existing = splitPantryEntries((pantryFallback && pantryFallback.value) || (pantryTextArea && pantryTextArea.value) || '');
      chip.classList.toggle('selected', existing.includes(item));
    }}

    const foodRulesInput = document.getElementById('foods_to_avoid_input');
    const foodRulesHidden = document.getElementById('foods_to_avoid');
    const foodRulesList = document.getElementById('foods-to-avoid-list');
    const addFoodRuleButton = document.querySelector('[data-food-rule-add]');

    function splitFoodRuleEntries(rawValue) {{
      return Array.from(new Set(
        (rawValue || '')
          .split(/[\\r\\n,]+|\\s+and\\s+|\\s+or\\s+/i)
          .map((entry) => entry.trim())
          .filter(Boolean)
      ));
    }}

    function setFoodRuleEntries(entries) {{
      if (!foodRulesHidden) return;
      foodRulesHidden.value = entries.join('\n');
    }}

    function renderFoodRuleChips() {{
      if (!foodRulesList || !foodRulesHidden) return;
      foodRulesList.innerHTML = '';
      const entries = splitFoodRuleEntries(foodRulesHidden.value);
      if (!entries.length) {{
        const empty = document.createElement('p');
        empty.className = 'hint';
        empty.textContent = 'No foods are excluded yet.';
        foodRulesList.appendChild(empty);
        return;
      }}
      for (const entry of entries) {{
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'chip selected';
        chip.textContent = entry;
        chip.setAttribute('aria-label', `Remove ${{entry}} from foods to avoid`);
        chip.addEventListener('click', () => {{
          const next = splitFoodRuleEntries(foodRulesHidden.value).filter(
            (current) => current.trim().toLowerCase() !== entry.trim().toLowerCase()
          );
          setFoodRuleEntries(next);
          renderFoodRuleChips();
        }});
        foodRulesList.appendChild(chip);
      }}
    }}

    function addFoodRuleEntry(rawValue) {{
      if (!foodRulesHidden) return;
      const entry = (rawValue || '').trim();
      if (!entry) return;
      const current = splitFoodRuleEntries(foodRulesHidden.value);
      const seen = new Set(current.map((value) => value.trim().toLowerCase()));
      if (!seen.has(entry.toLowerCase())) {{
        current.push(entry);
      }}
      setFoodRuleEntries(current);
      renderFoodRuleChips();
    }}

    if (foodRulesInput && addFoodRuleButton) {{
      addFoodRuleButton.addEventListener('click', () => {{
        addFoodRuleEntry(foodRulesInput.value);
        foodRulesInput.value = '';
        foodRulesInput.focus();
      }});
      foodRulesInput.addEventListener('keydown', (event) => {{
        if (event.key === 'Enter') {{
          event.preventDefault();
          addFoodRuleEntry(foodRulesInput.value);
          foodRulesInput.value = '';
        }}
      }});
    }}

    if (foodRulesHidden) {{
      foodRulesHidden.addEventListener('input', renderFoodRuleChips);
    }}

    renderFoodRuleChips();

    syncPantryList();
  </script>
</body>
</html>
"""


def render_customization_page(
    content: str,
    *,
    message: str | None = None,
    error: str | None = None,
) -> str:
    """Render the private local catalogue editor and recovery controls."""
    message_html = (
        f'<div class="message success" role="status">{escape(message)}</div>'
        if message
        else ""
    )
    error_html = (
        f'<div class="message error" role="alert">{escape(error)}</div>'
        if error
        else ""
    )
    example_template = json.dumps(
        {
            "key": "my_rice_bowl",
            "dish": "My rice and vegetable bowl",
            "catalogue_tier": "extended",
            "cooking_energy": "low",
            "dietary_tags": ["lactose-free"],
            "selection_tags": ["quick", "one-pan"],
            "ingredients": [
                {
                    "product_key": "rice",
                    "quantity_per_person": 100,
                    "planning_unit": "g",
                },
                {
                    "product_key": "vegetables",
                    "quantity_per_person": 150,
                    "planning_unit": "g",
                },
            ],
        },
        indent=2,
    )
    example_product = json.dumps(
        {
            "key": "spinach",
            "name": "Frozen spinach",
            "package_description": "300 g package",
            "package_size": 300,
            "package_price": 3.0,
            "planning_unit": "g",
            "variable_weight": False,
            "keywords": ["spinach"],
            "instacart_search_term": "frozen spinach",
            "instacart_quantity": 300,
            "instacart_unit": "g",
        },
        indent=2,
    )
    return f"""<!doctype html>
<html lang="en-CA">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Local catalogue - Carrinho</title>
  <style>
{PAGE_STYLES}
  </style>
</head>
<body>
  <main>
    <header>
      <div class="eyebrow">Private household data</div>
      <h1>Local catalogue</h1>
      <p>Add your own generic foods and meal templates without changing Carrinho's
        built-in starter catalogue.</p>
    </header>
    {message_html}
    {error_html}
    <section class="card">
      <form method="post" action="/customize">
        <input type="hidden" name="csrf_token" value="{CSRF_TOKEN}">
        <label class="wide">Local catalogue JSON
          <textarea class="json-editor" name="catalogue_json"
            spellcheck="false">{escape(content)}</textarea>
          <span class="hint">Carrinho validates the complete document before saving.
            Existing local data is backed up automatically.</span>
        </label>
        <button type="submit">Validate and save local catalogue</button>
      </form>
      <details>
        <summary>Show a meal-template example</summary>
        <p>Add an object like this inside <code>meal_templates</code>. Stable keys use
          lowercase letters, numbers, and underscores.</p>
        <pre>{escape(example_template)}</pre>
      </details>
      <details>
        <summary>Show a generic-food example</summary>
        <p>Add an object like this inside <code>products</code>. Package prices are
          simulated planning values, never live retailer prices.</p>
        <pre>{escape(example_product)}</pre>
      </details>
      <details>
        <summary>Important limits</summary>
        <ul>
          <li>Built-in keys cannot be replaced.</li>
          <li>New foods require generic package data and a simulated CAD estimate.</li>
          <li>Do not enter retailer SKUs, live prices, credentials, or personal data.</li>
          <li>Dietary tags are household declarations, not medical verification.</li>
        </ul>
      </details>
    </section>
    <div class="actions">
      <a class="button secondary" href="/">Back to planner</a>
      <form method="post" action="/customize/restore">
        <input type="hidden" name="csrf_token" value="{CSRF_TOKEN}">
        <button type="submit">Restore latest backup</button>
      </form>
    </div>
    <footer>Local catalogue files and backups stay in the ignored
      <code>local-data</code> directory.</footer>
  </main>
</body>
</html>
"""


class CarrinhoHandler(BaseHTTPRequestHandler):
    """Handle the two local routes used by Carrinho's browser interface."""

    def _send_html(self, content: str, status: int = 200) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; "
            f"script-src 'nonce-{CSRF_TOKEN}'; form-action 'self'; base-uri 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def _send_download(
        self,
        content: str,
        filename: str,
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        body = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Disposition",
            f'attachment; filename="{filename}"',
        )
        self.end_headers()
        self.wfile.write(body)

    def _read_form(self) -> dict[str, str]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("The submitted form has an invalid size.") from error
        if not 0 < length <= MAX_REQUEST_BYTES:
            raise ValueError("The submitted form is too large or empty.")
        try:
            raw_form = self.rfile.read(length).decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("The submitted form is not valid UTF-8.") from error
        parsed_form = parse_qs(raw_form, keep_blank_values=True)
        values = {key: items[-1] for key, items in parsed_form.items()}
        if not secrets.compare_digest(values.get("csrf_token", ""), CSRF_TOKEN):
            raise ValueError("Refresh the page and submit the form again.")
        return values

    def do_GET(self) -> None:
        path = urlsplit(self.path).path.rstrip("/") or "/"
        if path in {"/", "/plan"}:
            self._send_html(render_page())
            return
        if path == "/customize":
            try:
                content = read_local_catalogue_json()
            except ValueError as error:
                content = read_local_catalogue_source()
                self._send_html(
                    render_customization_page(content, error=str(error)),
                    400,
                )
                return
            self._send_html(render_customization_page(content))
            return
        self._send_html(render_page(error="Page not found."), 404)

    def do_POST(self) -> None:
        path = urlsplit(self.path).path.rstrip("/") or "/"
        if path not in {
            "/plan",
            "/customize",
            "/customize/restore",
            "/download/plan",
            "/download/instacart-paste-list",
            "/download/instacart-json",
        }:
            self._send_html(render_page(error="Page not found."), 404)
            return
        try:
            values = self._read_form()
        except ValueError as error:
            if self.path.startswith("/customize"):
                error_page = render_customization_page(
                    empty_local_catalogue_json(),
                    error=str(error),
                )
            else:
                error_page = render_page(error=str(error))
            self._send_html(error_page, 400)
            return

        if path == "/plan":
            try:
                request = build_request(values)
                plan = create_plan(values, request=request)
            except ValueError as error:
                self._send_html(render_page(values, error=str(error)), 400)
                return
            self._send_html(render_page(_render_form_values(values, request), plan=plan))
            return

        if path.startswith("/download/"):
            try:
                plan = create_plan(values)
            except ValueError as error:
                self._send_html(render_page(values, error=str(error)), 400)
                return
            if path == "/download/plan":
                self._send_download(f"{format_plan(plan)}\n", "meal-plan.txt")
                return
            if path == "/download/instacart-paste-list":
                self._send_download(
                    f"{create_instacart_paste_list(plan)}\n",
                    "instacart-paste-list.txt",
                )
                return
            self._send_download(
                f"{serialize_instacart_payload(plan)}\n",
                "instacart-list.json",
                "application/json; charset=utf-8",
            )
            return

        if path == "/customize":
            content = values.get("catalogue_json", "")
            try:
                result = save_local_catalogue_json(content)
            except ValueError as error:
                self._send_html(
                    render_customization_page(content, error=str(error)),
                    400,
                )
                return
            backup_note = " A backup of the previous file was created." if (
                result.backup_path is not None
            ) else ""
            message = (
                f"Saved {result.product_count} custom food(s) and "
                f"{result.meal_template_count} custom meal(s).{backup_note}"
            )
            self._send_html(
                render_customization_page(
                    read_local_catalogue_json(),
                    message=message,
                )
            )
            return

        try:
            result = restore_latest_local_catalogue()
            content = read_local_catalogue_json()
        except ValueError as error:
            try:
                current_content = read_local_catalogue_source()
            except ValueError:
                current_content = empty_local_catalogue_json()
            self._send_html(
                render_customization_page(
                    current_content,
                    error=str(error),
                ),
                400,
            )
            return
        self._send_html(
            render_customization_page(
                content,
                message=(
                    "Restored the latest backup with "
                    f"{result.product_count} custom food(s) and "
                    f"{result.meal_template_count} custom meal(s)."
                ),
            )
        )

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    """Start the local-only Carrinho web server until the user stops it."""
    server = ThreadingHTTPServer((HOST, PORT), CarrinhoHandler)
    print(f"Carrinho is ready at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop it.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCarrinho stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
