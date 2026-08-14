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
from local_catalogue import (
    empty_local_catalogue_json,
    load_effective_price_catalog,
    read_local_catalogue_json,
    read_local_catalogue_source,
    restore_latest_local_catalogue,
    save_local_catalogue_json,
)
from planning import Plan, generate_plan
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
    a { color: #146b4d; font-weight: 750; }
    .eyebrow { color: #b3422e; font-weight: 800; text-transform: uppercase; }
    .card, .result { background: #fff; border: 1px solid #d8d2c4;
      border-radius: 18px; box-shadow: 0 14px 40px rgba(23, 53, 44, 0.08);
      padding: 24px; }
    form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px; }
    label { display: grid; gap: 7px; font-weight: 750; }
    .wide { grid-column: 1 / -1; }
    input, select, textarea { border: 1px solid #a7aea6; border-radius: 10px;
      padding: 12px; background: #fff; color: #17352c; font: inherit; }
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
    pre { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere;
      font-family: inherit; line-height: 1.55; }
    footer { color: #5e6d67; margin-top: 20px; font-size: 0.9rem; }
    .actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 18px; }
    .actions form { display: block; }
    .actions button, .actions .button { display: inline-block; }
    .json-editor { min-height: 520px; font-family: Consolas, monospace;
      font-size: 0.9rem; line-height: 1.45; }
    details { margin-top: 20px; }
    code { background: #edf1ed; border-radius: 5px; padding: 2px 5px; }
    @media (max-width: 640px) {
      form { grid-template-columns: 1fr; }
      .wide, button { grid-column: 1; }
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
    if not re.fullmatch(r"\d+(?:[.,]\d{1,2})?", budget_text):
        raise ValueError("Enter a valid budget in CAD.")
    parsed_budget = parse_request(f"CAD${budget_text}")
    if parsed_budget.budget is None or parsed_budget.budget <= 0:
        raise ValueError("Enter a budget greater than zero.")

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
        budget=parsed_budget.budget,
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
    plan = generate_plan(build_request(form))
    if plan is None:
        raise ValueError("Carrinho could not create a plan from these values.")
    return plan


def _selected(value: str, expected: str) -> str:
    return " selected" if value == expected else ""


def render_page(
    values: Mapping[str, str] | None = None,
    plan: Plan | None = None,
    error: str | None = None,
) -> str:
    """Render the complete standalone page without external assets."""
    form = values or {}

    def value(name: str, default: str = "") -> str:
        return escape(form.get(name, default), quote=True)

    cooking_energy = form.get("cooking_energy", "low")
    dietary_restrictions = form.get(
        "dietary_restrictions",
        "lactose intolerance",
    )
    error_html = (
        f'<div class="message error" role="alert">{escape(error)}</div>'
        if error
        else ""
    )
    result_html = ""
    if plan is not None:
        result_html = (
            '<section class="result" aria-live="polite">'
            "<h2>Your Carrinho plan</h2>"
            f"<pre>{escape(format_plan(plan))}</pre>"
            "</section>"
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
      <p>One household request. One meal plan. One reviewable shopping list.</p>
    </header>
    {error_html}
    <section class="card">
      <form method="post" action="/plan">
        <input type="hidden" name="csrf_token" value="{CSRF_TOKEN}">
        <label>Budget in CAD
          <input name="budget" inputmode="decimal" required value="{value('budget', '80')}">
        </label>
        <label>People
          <input name="people" type="number" min="1" max="12" required
            value="{value('people', '2')}">
        </label>
        <label>Days
          <input name="days" type="number" min="1" max="14" required
            value="{value('days', '4')}">
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
            placeholder="rice, 7 eggs">{value('pantry_items', 'rice, 7 eggs')}</textarea>
          <span class="hint">Separate items with commas or new lines.
            Include quantities when known.</span>
        </label>
        <label>Dietary restrictions
          <select name="dietary_restrictions">
            <option value="none"{_selected(dietary_restrictions, 'none')}>None</option>
            <option value="lactose intolerance"
              {_selected(dietary_restrictions, 'lactose intolerance')}>
              Lactose intolerance
            </option>
          </select>
        </label>
        <label>Foods to use less often
          <input name="foods_to_avoid" value="{value('foods_to_avoid')}"
            placeholder="beans, onions">
          <span class="hint">Soft preference only. Longer plans may still include
            these foods.</span>
        </label>
        <label class="wide">Foods to use more often
          <input name="foods_to_prefer" value="{value('foods_to_prefer')}"
            placeholder="chicken, eggs">
          <span class="hint">Use common generic foods already known by Carrinho.</span>
        </label>
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
  <title>Local catalogue — Carrinho</title>
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
            "form-action 'self'; base-uri 'none'",
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
        if self.path not in {"/plan", "/customize", "/customize/restore"}:
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
