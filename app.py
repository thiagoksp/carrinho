"""Run Carrinho's initial terminal experience."""

from pathlib import Path
import re

from catalog import resolve_product_keys
from household_profile import (
    apply_household_defaults,
    load_household_profile,
    save_household_profile,
)
from instacart import (
    create_instacart_paste_list,
    save_instacart_paste_list,
    save_instacart_payload,
)
from llm_selector import LLMSelectorError, suggest_meal_candidate_keys
from local_catalogue import load_effective_price_catalog, load_local_catalogue
from planning import (
    Plan,
    format_planning_quantity,
    generate_plan,
    select_meal_candidate_templates,
)
from request_parser import ParsedRequest, parse_request


def _display(value: object | None) -> str:
    return str(value) if value is not None else "not identified"


def _display_product_preferences(product_keys: list[str] | None) -> str:
    if product_keys is None:
        return "not identified"
    if not product_keys:
        return "none"
    products_by_key = {
        product.key: product for product in load_effective_price_catalog().products
    }
    return ", ".join(
        products_by_key[key].name if key in products_by_key else key
        for key in product_keys
    )


def print_request_summary(request_data: ParsedRequest) -> None:
    """Show only the identified request data before building a plan."""
    if request_data.budget is None:
        budget = "not identified"
    else:
        currency = request_data.currency or ""
        value = f"{request_data.budget:g}"
        budget = (
            f"{currency}${value}"
            if currency == "CAD"
            else f"{currency} {value}".strip()
        )

    if request_data.pantry_items is None:
        pantry_items = "not identified"
    else:
        pantry_items = ", ".join(request_data.pantry_items) or "none"

    if request_data.dietary_restrictions is None:
        dietary_restrictions = "not identified"
    else:
        dietary_restrictions = (
            ", ".join(request_data.dietary_restrictions) or "none"
        )

    print("\nCarrinho understood:")
    print(f"- Budget: {budget}")
    print(f"- People: {_display(request_data.people)}")
    print(f"- Days: {_display(request_data.days)}")
    print(f"- Cooking energy: {_display(request_data.cooking_energy)}")
    print(f"- Pantry items: {pantry_items}")
    print(f"- Dietary restrictions: {dietary_restrictions}")
    print(
        "- Foods to use less often: "
        f"{_display_product_preferences(request_data.avoided_product_keys)}"
    )
    print(
        "- Foods to use more often: "
        f"{_display_product_preferences(request_data.preferred_product_keys)}"
    )


def _read_budget() -> tuple[float, str]:
    while True:
        response = input("\nWhat is your budget in CAD? (for example, 80)\n> ").strip()
        text = response if re.search(r"[A-Za-z$]", response) else f"CAD${response}"
        partial_request = parse_request(text)
        if partial_request.budget is not None and partial_request.budget > 0:
            return partial_request.budget, partial_request.currency or "CAD"
        print("I could not understand that. Enter only the amount, such as 80.")


def _read_quantity(question: str, unit: str, attribute: str) -> int:
    while True:
        response = input(f"\n{question}\n> ").strip()
        partial_request = parse_request(f"{response} {unit}")
        quantity = getattr(partial_request, attribute)
        if quantity is not None and quantity > 0:
            return quantity
        print("Enter a quantity greater than zero.")


def _read_cooking_energy() -> str:
    options = {"1": "low", "2": "normal", "3": "high"}
    while True:
        response = input(
            "\nHow much energy do you have for cooking?\n"
            "1 - Low\n2 - Normal\n3 - High\n> "
        ).strip().casefold()
        cooking_energy = options.get(response, response)
        if cooking_energy in options.values():
            return cooking_energy
        print("Choose 1, 2, or 3.")


def _split_response(response: str) -> list[str]:
    return [
        item.strip().casefold()
        for item in re.split(r"\s*,\s*|\s+and\s+", response, flags=re.IGNORECASE)
        if item.strip()
    ]


def _read_pantry_items() -> list[str]:
    while True:
        response = input(
            "\nWhat do you already have at home? Separate items with commas; "
            "enter 'nothing' if your pantry is empty.\n> "
        ).strip()
        if response.casefold() in {"nothing", "none"}:
            return []
        pantry_items = _split_response(response)
        if pantry_items:
            return pantry_items
        print("Enter the items or type 'nothing'.")


def _read_dietary_restrictions() -> list[str]:
    while True:
        response = input(
            "\nAre there any dietary restrictions? Enter 'none' if there are not.\n> "
        ).strip()
        if response.casefold() in {"no", "none"}:
            return []

        partial_request = parse_request(response)
        dietary_restrictions = (
            partial_request.dietary_restrictions or _split_response(response)
        )
        if dietary_restrictions:
            return dietary_restrictions
        print("Enter the restriction or type 'none'.")


def _read_product_preferences(preference: str) -> list[str]:
    catalog = load_effective_price_catalog()
    available_foods = ", ".join(product.name for product in catalog.products)
    prompts = {
        "avoid": "Which foods should the plan try to use less often?",
        "prefer": "Which foods should the plan try to use more often?",
    }
    while True:
        response = input(
            f"\n{prompts[preference]} Separate foods with commas; "
            "enter 'none' if there are not any.\n> "
        ).strip()
        if response.casefold() in {"no", "none"}:
            return []
        try:
            return list(
                resolve_product_keys(_split_response(response), catalog.products)
            )
        except ValueError as error:
            print(error)
            print(f"Available generic foods: {available_foods}.")


def _validate_product_preferences(request_data: ParsedRequest) -> None:
    catalog = load_effective_price_catalog()
    available_keys = {product.key for product in catalog.products}
    avoided_keys = request_data.avoided_product_keys or []
    preferred_keys = request_data.preferred_product_keys or []
    unknown_keys = set(avoided_keys + preferred_keys).difference(available_keys)
    if unknown_keys:
        raise ValueError(
            "Unknown food preference key: " + ", ".join(sorted(unknown_keys)) + "."
        )
    if set(avoided_keys).intersection(preferred_keys):
        raise ValueError(
            "The same food cannot be both used less often and used more often."
        )


def complete_request(request_data: ParsedRequest) -> ParsedRequest:
    """Ask only for data that was not present in the initial request."""
    if request_data.budget is None:
        request_data.budget, request_data.currency = _read_budget()
    if request_data.people is None:
        request_data.people = _read_quantity(
            "How many people are you feeding?",
            "people",
            "people",
        )
    if request_data.days is None:
        request_data.days = _read_quantity("For how many days?", "days", "days")
    if request_data.cooking_energy is None:
        request_data.cooking_energy = _read_cooking_energy()
    if request_data.pantry_items is None:
        request_data.pantry_items = _read_pantry_items()
    if request_data.dietary_restrictions is None:
        request_data.dietary_restrictions = _read_dietary_restrictions()
    if request_data.avoided_product_keys is None:
        request_data.avoided_product_keys = []
    if request_data.preferred_product_keys is None:
        request_data.preferred_product_keys = []
    return request_data


def _confirm_request() -> bool:
    while True:
        response = input("\nIs this information correct? (y/n)\n> ").strip().casefold()
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        print("Enter 'y' for yes or 'n' for no.")


def _correct_one_field(request_data: ParsedRequest) -> None:
    options = {
        "1": "budget",
        "2": "people",
        "3": "days",
        "4": "cooking_energy",
        "5": "pantry_items",
        "6": "dietary_restrictions",
        "7": "avoided_product_keys",
        "8": "preferred_product_keys",
    }

    while True:
        response = input(
            "\nWhich detail would you like to correct?\n"
            "1 - Budget\n"
            "2 - People\n"
            "3 - Days\n"
            "4 - Cooking energy\n"
            "5 - Pantry items\n"
            "6 - Dietary restrictions\n"
            "7 - Foods to use less often\n"
            "8 - Foods to use more often\n> "
        ).strip()
        choice = options.get(response)
        if choice is not None:
            break
        print("Choose a number from 1 to 8.")

    if choice == "budget":
        request_data.budget, request_data.currency = _read_budget()
    elif choice == "people":
        request_data.people = _read_quantity(
            "How many people are you feeding?",
            "people",
            "people",
        )
    elif choice == "days":
        request_data.days = _read_quantity("For how many days?", "days", "days")
    elif choice == "cooking_energy":
        request_data.cooking_energy = _read_cooking_energy()
    elif choice == "pantry_items":
        request_data.pantry_items = _read_pantry_items()
    elif choice == "dietary_restrictions":
        request_data.dietary_restrictions = _read_dietary_restrictions()
    elif choice == "avoided_product_keys":
        request_data.avoided_product_keys = _read_product_preferences("avoid")
    else:
        request_data.preferred_product_keys = _read_product_preferences("prefer")


def review_request(request_data: ParsedRequest) -> ParsedRequest:
    """Let the user correct one field at a time until the summary is confirmed."""
    while True:
        print_request_summary(request_data)
        if _confirm_request():
            try:
                _validate_product_preferences(request_data)
            except ValueError as error:
                print(f"\n{error} Correct one of the food preference fields.")
            else:
                return request_data
        _correct_one_field(request_data)


def _format_money(currency: str, value: float) -> str:
    prefixes = {"CAD": "CAD$", "USD": "US$", "BRL": "R$"}
    prefix = prefixes.get(currency, f"{currency} ")
    return f"{prefix}{value:.2f}"


def format_plan(plan: Plan) -> str:
    """Build the same English output for the terminal and the saved file."""
    lines = [
        "MEAL PLAN",
        f"For {plan.people} person(s) over {plan.days} day(s).",
        "Retailer: to be selected by the user in Instacart.",
        "The current estimate uses one simulated, retailer-neutral Canadian "
        "price catalogue for this trip.",
    ]

    for meal in plan.meals:
        lines.append(f"- Day {meal.day} - {meal.meal_slot}: {meal.dish}")

    lines.extend(("", "MEAL SELECTION"))
    for guidance in plan.meal_selection_guidance:
        lines.append(f"- {guidance}")

    lines.extend(("", "MEAL PREP GUIDANCE"))
    for guidance in plan.meal_prep_guidance:
        lines.append(f"- {guidance}")

    lines.extend(("", f"SHOPPING LIST - {plan.price_type.upper()} PRICES"))
    for item in plan.shopping_items:
        required_quantity = format_planning_quantity(
            item.required_quantity,
            item.planning_unit,
            item.name,
        )
        purchase_quantity = format_planning_quantity(
            item.purchase_quantity,
            item.planning_unit,
            item.name,
        )
        if item.variable_weight:
            quantity_details = (
                f"need {required_quantity}; plan about {purchase_quantity}; "
                "actual package weight may be higher or lower"
            )
        elif item.overage_quantity > 0.000001:
            overage_quantity = format_planning_quantity(
                item.overage_quantity,
                item.planning_unit,
                item.name,
            )
            quantity_details = (
                f"need {required_quantity}; buy {purchase_quantity}; "
                f"{overage_quantity} extra"
            )
        else:
            quantity_details = (
                f"need {required_quantity}; buy {purchase_quantity}"
            )
        lines.append(
            f"- {item.name}: {item.quantity_label} "
            f"- {quantity_details} "
            f"- {_format_money(plan.currency, item.estimated_price)}"
        )

    estimated_total = _format_money(plan.currency, plan.estimated_total)
    lines.extend(("", f"Estimated total: {estimated_total}"))
    if plan.budget_balance is None:
        lines.append("No budget provided.")
    elif plan.budget_balance >= 0:
        budget_balance = _format_money(plan.currency, plan.budget_balance)
        lines.append(f"Budget balance: {budget_balance}")
    else:
        budget_shortfall = _format_money(plan.currency, abs(plan.budget_balance))
        lines.append(f"Budget shortfall: {budget_shortfall}")

    lines.append(f"Price source: {plan.price_description}")

    lines.extend(("", "PANTRY ITEMS USED"))
    if plan.pantry_usage:
        for usage in plan.pantry_usage:
            lines.append(f"- {usage}")
    else:
        lines.append("- No main ingredient from the plan was identified at home.")

    lines.extend(
        (
            "",
            "Important: the plan does not intentionally use dairy ingredients, "
            "but product labels must still be checked.",
        )
    )
    return "\n".join(lines)


def print_plan(plan: Plan) -> None:
    """Show the plan and its current estimated costs."""
    print(f"\n{format_plan(plan)}")


def optional_llm_meal_candidate_keys(
    request_data: ParsedRequest,
) -> tuple[str, ...] | None:
    """Ask the optional guarded LLM selector for known meal-template keys."""
    candidate_templates = select_meal_candidate_templates(request_data)
    return suggest_meal_candidate_keys(request_data, candidate_templates)


def _next_plan_path(directory: Path) -> Path:
    path = directory / "meal-plan.txt"
    number = 2
    while path.exists():
        path = directory / f"meal-plan-{number}.txt"
        number += 1
    return path


def save_plan(plan: Plan, output_directory: Path | None = None) -> Path:
    """Save a new plan without replacing an earlier result."""
    directory = output_directory or Path(__file__).resolve().parent / "outputs"
    directory.mkdir(parents=True, exist_ok=True)
    path = _next_plan_path(directory)
    path.write_text(f"{format_plan(plan)}\n", encoding="utf-8")
    return path


def _should_save_plan() -> bool:
    while True:
        response = input(
            "\nWould you like to save the plan and local Instacart preview? (y/n)\n> "
        ).strip().casefold()
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        print("Enter 'y' for yes or 'n' for no.")


def _should_use_household_profile() -> bool:
    while True:
        response = input(
            "\nA private household profile is available locally. "
            "Use its defaults and pantry items? (y/n)\n> "
        ).strip().casefold()
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        print("Enter 'y' for yes or 'n' for no.")


def _should_save_household_profile() -> bool:
    while True:
        response = input(
            "\nWould you like to save or update household defaults, pantry items, "
            "and food preferences locally? (y/n)\n> "
        ).strip().casefold()
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        print("Enter 'y' for yes or 'n' for no.")


def main() -> None:
    """Read a request, confirm it, and build the current local plan."""
    print("\nCARRINHO")
    print("Simple meal planning and grocery-cart preparation.")

    request_text = input("\nTell us about your situation:\n> ").strip()

    if not request_text:
        print("\nNo request was provided.")
        return

    try:
        load_local_catalogue()
    except ValueError as error:
        print(
            "\nThe private local catalogue needs attention: "
            f"{error} Open the browser interface and choose "
            "Manage local meals and foods."
        )
        return

    request_data = parse_request(request_text)
    try:
        household_profile = load_household_profile()
    except ValueError as error:
        print(f"\nSaved household profile was ignored: {error}")
        household_profile = None
    if household_profile is not None and _should_use_household_profile():
        request_data = apply_household_defaults(request_data, household_profile)

    request_data = review_request(complete_request(request_data))
    print("\nInformation confirmed.")

    try:
        meal_candidate_keys = optional_llm_meal_candidate_keys(request_data)
    except LLMSelectorError as error:
        print(f"\nOptional LLM meal selection is not available: {error}")
        return
    except ValueError:
        meal_candidate_keys = None

    plan = generate_plan(request_data, meal_candidate_keys=meal_candidate_keys)
    if plan is None:
        print(
            "\nThis version plans for 1 to 12 people over 1 to 14 days, "
            "in CAD, with no dietary restrictions or lactose intolerance only."
        )
        return

    print_plan(plan)
    if _should_save_household_profile():
        household_path = save_household_profile(request_data)
        print(f"\nHousehold profile saved locally to:\n{household_path}")
    if _should_save_plan():
        create_instacart_paste_list(plan)
        plan_path = save_plan(plan)
        instacart_path = save_instacart_payload(plan)
        paste_list_path = save_instacart_paste_list(plan)
        print(f"\nPlan saved to:\n{plan_path}")
        print(
            "\nInstacart preview saved locally - no data was sent:\n"
            f"{instacart_path}"
        )
        print(f"\nManual Instacart paste list saved to:\n{paste_list_path}")
        print(
            "Open the file in Windows, copy its contents, and send it to your "
            "iPhone through Notes, email, or a message. Then open Shopping List "
            "-> Paste items."
        )
        print(
            "Instacart may interpret a measurement as text. Review the retailer "
            "you select in Instacart, matched products, quantities, ingredients, "
            "and labels for your dietary needs before adding items to the cart."
        )


if __name__ == "__main__":
    main()
