"""Store private Carrinho household defaults outside the repository."""

from dataclasses import dataclass
import json
from pathlib import Path

from request_parser import ParsedRequest


HOUSEHOLD_PROFILE_SCHEMA = "carrinho.household-profile.v1"
DEFAULT_LOCAL_DATA_DIRECTORY = Path(__file__).resolve().parent / "local-data"
PROFILE_FILENAME = "household-profile.json"
COOKING_ENERGY_VALUES = {"low", "normal", "high"}


@dataclass(frozen=True)
class HouseholdProfile:
    people: int
    cooking_energy: str
    pantry_items: tuple[str, ...]
    dietary_restrictions: tuple[str, ...]


def _profile_path(local_data_directory: Path | None = None) -> Path:
    directory = local_data_directory or DEFAULT_LOCAL_DATA_DIRECTORY
    return directory / PROFILE_FILENAME


def _text_items(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"The household profile has invalid {field}.")
    return tuple(item.strip() for item in value)


def _validate_profile(data: object) -> HouseholdProfile:
    if not isinstance(data, dict):
        raise ValueError("The household profile must be a JSON object.")
    if data.get("schema") != HOUSEHOLD_PROFILE_SCHEMA:
        raise ValueError("The household profile has an unsupported schema.")

    people = data.get("people")
    if not isinstance(people, int) or isinstance(people, bool) or not 1 <= people <= 12:
        raise ValueError("The household profile has an invalid people value.")

    cooking_energy = data.get("cooking_energy")
    if not isinstance(cooking_energy, str) or cooking_energy not in COOKING_ENERGY_VALUES:
        raise ValueError("The household profile has an invalid cooking energy value.")

    pantry_items = _text_items(data.get("pantry_items"), "pantry items")
    dietary_restrictions = _text_items(
        data.get("dietary_restrictions"),
        "dietary restrictions",
    )
    if any("lactose" not in restriction.casefold() for restriction in dietary_restrictions):
        raise ValueError("The household profile has unsupported dietary restrictions.")

    return HouseholdProfile(
        people=people,
        cooking_energy=cooking_energy,
        pantry_items=pantry_items,
        dietary_restrictions=dietary_restrictions,
    )


def load_household_profile(
    local_data_directory: Path | None = None,
) -> HouseholdProfile | None:
    """Load the optional private household profile without creating a file."""
    path = _profile_path(local_data_directory)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("The household profile could not be read.") from error
    return _validate_profile(data)


def _profile_from_request(request_data: ParsedRequest) -> HouseholdProfile:
    if request_data.people is None:
        raise ValueError("A household profile requires people.")
    if request_data.cooking_energy is None:
        raise ValueError("A household profile requires cooking energy.")
    if request_data.pantry_items is None:
        raise ValueError("A household profile requires pantry items.")
    if request_data.dietary_restrictions is None:
        raise ValueError("A household profile requires dietary restrictions.")

    return _validate_profile(
        {
            "schema": HOUSEHOLD_PROFILE_SCHEMA,
            "people": request_data.people,
            "cooking_energy": request_data.cooking_energy,
            "pantry_items": request_data.pantry_items,
            "dietary_restrictions": request_data.dietary_restrictions,
        }
    )


def save_household_profile(
    request_data: ParsedRequest,
    local_data_directory: Path | None = None,
) -> Path:
    """Save or replace private household defaults after explicit confirmation."""
    profile = _profile_from_request(request_data)
    path = _profile_path(local_data_directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": HOUSEHOLD_PROFILE_SCHEMA,
        "people": profile.people,
        "cooking_energy": profile.cooking_energy,
        "pantry_items": list(profile.pantry_items),
        "dietary_restrictions": list(profile.dietary_restrictions),
    }
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)
    return path


def apply_household_defaults(
    request_data: ParsedRequest,
    profile: HouseholdProfile,
) -> ParsedRequest:
    """Fill only request fields the user did not provide in the current request."""
    if request_data.people is None:
        request_data.people = profile.people
    if request_data.cooking_energy is None:
        request_data.cooking_energy = profile.cooking_energy
    if request_data.pantry_items is None:
        request_data.pantry_items = list(profile.pantry_items)
    if request_data.dietary_restrictions is None:
        request_data.dietary_restrictions = list(profile.dietary_restrictions)
    return request_data
