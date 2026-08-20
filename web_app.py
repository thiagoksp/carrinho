"""Serve Carrinho's standalone interface on the local computer."""

from collections.abc import Mapping
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import secrets
from urllib.parse import parse_qs

from app import format_plan
from catalog import resolve_product_keys
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

PAGE_STYLES = """
    :root { color-scheme: light; font-family: Inter, system-ui, sans-serif; }
    body { margin: 0; background: #f5f2e9; color: #17352c; }
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
     padding: 24px; }
   form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
     gap: 18px; }
   label { display: grid; gap: 7px; font-weight: 750; width: 100%; }
   .wide { grid-column: 1 / -1; }
   input, select, textarea { box-sizing: border-box; width: 100%; border: 1px solid #a7aea6;
     border-radius: 10px; padding: 12px; background: #fff; color: #17352c; font: inherit; }
   textarea { min-height: 76px; resize: vertical; }
   button, .button { grid-column: 1 / -1; border: 0; border-radius: 999px;
     padding: 14px 22px; background: #146b4d; color: #fff; font: inherit;
     font-weight: 800; cursor: pointer; text-align: center; text-decoration: none; }
   button:hover, .button:hover { background: #0f533c; }
   .button.secondary { background: #e7eee9; color: #17352c; }
   .hint { color: #5e6d67; font-size: 0.9rem; font-weight: 500; }
   .message { border-radius: 12px; margin-bottom: 18px; padding: 14px 16px; }
   .error { background: #fff0ed; border: 1px solid #d35b45; color: #812817; }
   .success { background: #e8f5ed; border: 1px solid #4a956f; color: #174f37; }
   .result { margin-top: 24px; }
   .plan-controls { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 24px; }
   .plan-controls form { display: flex; flex: 1 1 210px; margin: 0; }
   .plan-controls > button, .plan-controls form button {
       flex: 1 1 180px; grid-column: auto; min-width: 0;
   }
   .plan-controls form button { width: 100%; }
   .plan-overview { margin-bottom: 20px; }
   .overview-grid { list-style: none; margin: 12px 0 0; padding: 0;
     display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
   .meal-summary-card { background: #f7f6f1; border: 1px solid #d8d2c4;
     border-radius: 12px; padding: 14px; }
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
    return list(resolve_product_keys(food_names, catalog.products))


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

    restriction = form.get("dietary_restrictions", "").strip().casefold()
    restrictions = {
        "none": [],
        "lactose intolerance": ["lactose intolerance"],
    }
    if restriction not in restrictions:
        raise ValueError("Choose a supported dietary restriction.")

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
        dietary_restrictions=restrictions[restriction],
        avoided_product_keys=avoided_keys,
        preferred_product_keys=preferred_keys,
    )


def create_plan(form: Mapping[str, str]) -> Plan:
    """Create one deterministic plan or raise a friendly validation error."""
    request = build_request(form)
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
    dietary_restrictions = form.get(
        "dietary_restrictions",
        "none",
    )
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

        result_html = (
            '<section class="result" aria-live="polite">'
            '<h2>Your Carrinho plan</h2>'
            f'{budget_status}'
            '<div class="plan-controls">'
            '<button type="button" data-copy-target="plan-output">Copy plan</button>'
            '<button type="button" data-print-plan>Print plan</button>'
            f'<form method="post" action="/download/plan">{hidden_fields}<button type="submit">Download plan text</button></form>'
            f'<form method="post" action="/download/instacart-paste-list">{hidden_fields}<button type="submit">Download Instacart paste list</button></form>'
            f'<form method="post" action="/download/instacart-json">{hidden_fields}<button type="submit">Download Instacart JSON preview</button></form>'
            '</div>'
            '<div id="plan-output" class="plan-output">'
            '<section class="plan-overview" aria-label="Weekly overview">'
            '<h3>Weekly overview</h3>'
            f'<ul class="overview-grid">{overview_html}</ul>'
            '</section>'
            '<section class="meal-list" aria-label="Meal details">'
            f'{meals_html}'
            '</section>'
            '<button type="button" data-expand-all="meal-details" aria-expanded="false">Expand all</button>'
            '<details class="plan-details">'
            '<summary>Meal guidance</summary>'
            '<h3>Meal selection guidance</h3>'
            f'<pre>{escape("\n".join(plan.meal_selection_guidance))}</pre>'
            '<h3>Meal prep guidance</h3>'
            f'<pre>{escape("\n".join(plan.meal_prep_guidance))}</pre>'
            '</details>'
            '<section class="shopping-list"><h3>Shopping list</h3>'
            f'<ul>{shopping_html}</ul>'
            '</section>'
            '<details class="plan-details">'
            '<summary>Budget and estimated prices</summary>'
            f'<p><strong>Total range:</strong> {escape(estimated_total_min)} to {escape(estimated_total_max)}</p>'
            f'{budget_summary}'
            f'{budget_note}'
            f'<h3>Estimated price ranges</h3>'
            '<table class="estimate-table">'
            '<thead><tr><th>Ingredient</th><th>Quantity</th><th>Estimated range</th></tr></thead>'
            f'<tbody>{estimates_html}</tbody>'
            '</table>'
            f'<p><strong>Price source:</strong> {escape(display_price_description)} '
            '(retailer-neutral Canadian price catalogue for planning only)</p>'
            '</details>'
            '<details class="plan-details">'
            '<summary>Pantry items used</summary>'
            f'{pantry_html}'
            '</details>'
            '</div>'
            '<div class="copy-status" role="status" aria-live="polite"></div>'
            '</section>'
            f'<script nonce="{CSRF_TOKEN}">'
            'const mealButtons = document.querySelectorAll(".meal-toggle"); '
            'const expandAllButton = document.querySelector("[data-expand-all]"); '
            'function syncMealToggle(button, target, isExpanded) { '
            'if (!button || !target) return; '
            'button.setAttribute("aria-expanded", String(isExpanded)); '
            'button.textContent = isExpanded ? button.dataset.labelExpanded : button.dataset.labelCollapsed; '
            'target.hidden = !isExpanded; '
            '} '
            'for (const button of mealButtons) { '
            'const target = document.getElementById(button.dataset.target); '
            'button.addEventListener("click", () => { '
            'const isExpanded = target.hidden; '
            'for (const otherButton of mealButtons) { '
            'const otherTarget = document.getElementById(otherButton.dataset.target); '
            'if (otherButton === button) continue; '
            'syncMealToggle(otherButton, otherTarget, false); '
            '} '
            'syncMealToggle(button, target, isExpanded); '
            'if (expandAllButton) { '
            'const allOpen = [...document.querySelectorAll(".meal-details")].every((detail) => !detail.hidden); '
            'expandAllButton.setAttribute("aria-expanded", String(allOpen)); '
            'expandAllButton.textContent = allOpen ? "Collapse all" : "Expand all"; '
            '} '
            '}); '
            '} '
            'if (expandAllButton) { '
            'expandAllButton.addEventListener("click", () => { '
            'const anyHidden = [...document.querySelectorAll(".meal-details")].some((detail) => detail.hidden); '
            'for (const button of mealButtons) { '
            'const target = document.getElementById(button.dataset.target); '
            'syncMealToggle(button, target, anyHidden); '
            '} '
            'expandAllButton.setAttribute("aria-expanded", String(anyHidden)); '
            'expandAllButton.textContent = anyHidden ? "Collapse all" : "Expand all"; '
            '}); '
            '} '
            '</script>'
        )

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
    <header>
      <div class="eyebrow">Canadian grocery planning</div>
      <h1>Carrinho</h1>
      <p>Start with people and days. Add details only when they matter.</p>
    </header>
    {error_html}
    <section class="card">
      <form method="post" action="/plan">
        <input type="hidden" name="csrf_token" value="{CSRF_TOKEN}">
        <h2 class="form-section-title">Quick start</h2>
        <p class="hint wide">Required: choose how many people and days to plan for.</p>
        <label>People
          <input name="people" type="number" min="1" max="12" required
            value="{value('people', '2')}">
        </label>
        <label>Days
          <input name="days" type="number" min="1" max="14" required
            value="{value('days', '4')}">
        </label>
        <h2 class="form-section-title">Add details</h2>
        <p class="hint wide">Optional: add budget, pantry, energy, or dietary details
          for a more accurate plan.</p>
        <div class="details-group">
          <label>Budget in CAD
            <input name="budget" inputmode="decimal" value="{value('budget')}">
            <span class="hint">Optional. Add it when you want a balance or shortfall.</span>
          </label>
          <label>Cooking energy
            <select name="cooking_energy">
              <option value="low"{_selected(cooking_energy, 'low')}>Low</option>
              <option value="normal"{_selected(cooking_energy, 'normal')}>Normal</option>
              <option value="high"{_selected(cooking_energy, 'high')}>High</option>
            </select>
          </label>
          <label class="wide">Pantry items
            <textarea name="pantry_items"
              placeholder="rice, 7 eggs">{value('pantry_items')}</textarea>
            <span class="hint">Separate items with commas or new lines.
              Include quantities when known.</span>
          </label>
          <label class="wide">Dietary restrictions
            <select name="dietary_restrictions">
              <option value="none"{_selected(dietary_restrictions, 'none')}>None</option>
              <option value="lactose intolerance"
                {_selected(dietary_restrictions, 'lactose intolerance')}>
                Lactose intolerance
              </option>
            </select>
          </label>
        </div>
        <button type="submit">Build my plan</button>
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
        if self.path == "/":
            self._send_html(render_page())
            return
        if self.path == "/customize":
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
        if self.path not in {
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

        if self.path == "/plan":
            try:
                plan = create_plan(values)
            except ValueError as error:
                self._send_html(render_page(values, error=str(error)), 400)
                return
            self._send_html(render_page(values, plan=plan))
            return

        if self.path.startswith("/download/"):
            try:
                plan = create_plan(values)
            except ValueError as error:
                self._send_html(render_page(values, error=str(error)), 400)
                return
            if self.path == "/download/plan":
                self._send_download(f"{format_plan(plan)}\n", "meal-plan.txt")
                return
            if self.path == "/download/instacart-paste-list":
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

        if self.path == "/customize":
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
