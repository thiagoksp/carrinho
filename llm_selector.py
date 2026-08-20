"""Optional guarded LLM meal-template selector."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
import http.client
import json
import math
import os
import socket

from meal_catalogue import MealCatalogue, MealTemplate, load_default_meal_catalogue
from planning import validate_meal_candidate_keys
from request_parser import ParsedRequest


OPENAI_RESPONSES_HOST = "api.openai.com"
OPENAI_RESPONSES_PATH = "/v1/responses"
DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_CANDIDATES = 8
DEFAULT_MAX_OUTPUT_TOKENS = 512
MAX_RESPONSE_BYTES = 128 * 1024


class LLMSelectorError(RuntimeError):
    """Base error for optional LLM meal selection."""


class LLMSelectorConfigError(LLMSelectorError):
    """Raised when optional LLM configuration is invalid."""


class LLMSelectorTransportError(LLMSelectorError):
    """Raised when the optional LLM request cannot complete."""


class LLMSelectorResponseError(LLMSelectorError):
    """Raised when the optional LLM response is not usable."""


@dataclass(frozen=True)
class LLMSelectorConfig:
    """Runtime configuration for the optional meal selector."""

    enabled: bool
    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_candidates: int = DEFAULT_MAX_CANDIDATES
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    api_key: str | None = field(default=None, repr=False)


Transport = Callable[[dict[str, object], LLMSelectorConfig], tuple[int, bytes]]


def _environment(
    environment: Mapping[str, str] | None,
) -> Mapping[str, str]:
    return environment if environment is not None else os.environ


def _has_control_character(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _read_flag(environment: Mapping[str, str]) -> bool:
    value = environment.get("CARRINHO_LLM_SELECTOR_ENABLED", "0").strip()
    if value == "0":
        return False
    if value == "1":
        return True
    raise LLMSelectorConfigError(
        "CARRINHO_LLM_SELECTOR_ENABLED must be 0 or 1."
    )


def _read_positive_int(
    environment: Mapping[str, str],
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw_value = environment.get(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as error:
        raise LLMSelectorConfigError(f"{name} must be an integer.") from error
    if not minimum <= value <= maximum:
        raise LLMSelectorConfigError(
            f"{name} must be between {minimum} and {maximum}."
        )
    return value


def _read_timeout(environment: Mapping[str, str]) -> float:
    raw_value = environment.get(
        "CARRINHO_LLM_TIMEOUT_SECONDS",
        str(DEFAULT_TIMEOUT_SECONDS),
    ).strip()
    try:
        value = float(raw_value)
    except ValueError as error:
        raise LLMSelectorConfigError(
            "CARRINHO_LLM_TIMEOUT_SECONDS must be a number."
        ) from error
    if not math.isfinite(value) or not 1 <= value <= 30:
        raise LLMSelectorConfigError(
            "CARRINHO_LLM_TIMEOUT_SECONDS must be between 1 and 30."
        )
    return value


def load_llm_selector_config(
    environment: Mapping[str, str] | None = None,
) -> LLMSelectorConfig:
    """Load optional LLM selector settings from environment values."""
    env = _environment(environment)
    enabled = _read_flag(env)
    provider = env.get("CARRINHO_LLM_PROVIDER", DEFAULT_PROVIDER).strip()
    model = env.get("CARRINHO_LLM_MODEL", DEFAULT_MODEL).strip()
    timeout_seconds = _read_timeout(env)
    max_candidates = _read_positive_int(
        env,
        "CARRINHO_LLM_MAX_CANDIDATES",
        DEFAULT_MAX_CANDIDATES,
        1,
        12,
    )
    max_output_tokens = _read_positive_int(
        env,
        "CARRINHO_LLM_MAX_OUTPUT_TOKENS",
        DEFAULT_MAX_OUTPUT_TOKENS,
        128,
        2048,
    )
    if not enabled:
        return LLMSelectorConfig(
            enabled=False,
            provider=provider or DEFAULT_PROVIDER,
            model=model or DEFAULT_MODEL,
            timeout_seconds=timeout_seconds,
            max_candidates=max_candidates,
            max_output_tokens=max_output_tokens,
        )

    if provider != DEFAULT_PROVIDER:
        raise LLMSelectorConfigError("Only the openai LLM provider is supported.")
    if not model or _has_control_character(model):
        raise LLMSelectorConfigError("CARRINHO_LLM_MODEL is invalid.")

    api_key = env.get("OPENAI_API_KEY", "")
    if not api_key.strip():
        raise LLMSelectorConfigError("OPENAI_API_KEY is required when LLM is enabled.")
    if api_key.startswith("Bearer ") or _has_control_character(api_key):
        raise LLMSelectorConfigError("OPENAI_API_KEY is invalid.")

    return LLMSelectorConfig(
        enabled=True,
        provider=provider,
        model=model,
        timeout_seconds=timeout_seconds,
        max_candidates=max_candidates,
        max_output_tokens=max_output_tokens,
        api_key=api_key,
    )


def _candidate_context(template: MealTemplate) -> dict[str, object]:
    return {
        "key": template.key,
        "dish": template.dish,
        "catalogue_tier": template.catalogue_tier,
        "cooking_energy": template.cooking_energy,
        "cuisine": template.cuisine,
        "dietary_tags": list(template.dietary_tags),
        "selection_tags": list(template.selection_tags),
        "product_keys": [
            ingredient.product_key for ingredient in template.ingredients
        ],
    }


def _request_context(request: ParsedRequest) -> dict[str, object]:
    return {
        "people": request.people,
        "days": request.days,
        "cooking_energy": request.cooking_energy or "normal",
        "pantry_items": request.pantry_items or [],
        "dietary_restrictions": request.dietary_restrictions or [],
        "foods_to_use_less_often": request.avoided_product_keys or [],
        "foods_to_use_more_often": request.preferred_product_keys or [],
    }


def _selection_schema(candidate_keys: Sequence[str]) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["meal_template_keys"],
        "properties": {
            "meal_template_keys": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": list(candidate_keys),
                },
            },
        },
    }


def create_openai_responses_payload(
    request: ParsedRequest,
    candidate_templates: Sequence[MealTemplate],
    config: LLMSelectorConfig,
) -> dict[str, object]:
    """Build the Responses API payload using Structured Outputs."""
    if not candidate_templates:
        raise LLMSelectorConfigError("At least one meal candidate is required.")
    limited_templates = tuple(candidate_templates[: config.max_candidates])
    candidate_keys = [template.key for template in limited_templates]
    context = {
        "household_request": _request_context(request),
        "allowed_meal_templates": [
            _candidate_context(template) for template in limited_templates
        ],
        "rules": [
            "Return only known meal_template keys from allowed_meal_templates.",
            "Return the best meal order for this household.",
            "Do not invent recipes, products, quantities, costs, or store data.",
        ],
    }
    return {
        "model": config.model,
        "input": [
            {
                "role": "system",
                "content": (
                    "You are Carrinho's optional meal-order selector. "
                    "Suggest only ordered known meal-template keys. "
                    "Carrinho's local code validates safety and calculates all "
                    "quantities, packages, cost estimates, and shopping output."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(context, ensure_ascii=True),
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "carrinho_meal_selection",
                "strict": True,
                "schema": _selection_schema(candidate_keys),
            },
        },
        "max_output_tokens": config.max_output_tokens,
    }


def _post_openai_responses(
    payload: dict[str, object],
    config: LLMSelectorConfig,
) -> tuple[int, bytes]:
    if config.api_key is None:
        raise LLMSelectorConfigError("OPENAI_API_KEY is required when LLM is enabled.")
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    connection = http.client.HTTPSConnection(
        OPENAI_RESPONSES_HOST,
        timeout=config.timeout_seconds,
    )
    try:
        connection.request(
            "POST",
            OPENAI_RESPONSES_PATH,
            body=body,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        response = connection.getresponse()
        response_body = response.read(MAX_RESPONSE_BYTES + 1)
    except (OSError, TimeoutError, socket.timeout) as error:
        raise LLMSelectorTransportError(
            "The optional LLM meal selector could not be reached."
        ) from error
    finally:
        connection.close()

    if len(response_body) > MAX_RESPONSE_BYTES:
        raise LLMSelectorResponseError("The optional LLM response was too large.")
    return response.status, response_body


def _extract_response_text(data: object) -> str:
    if not isinstance(data, dict):
        raise LLMSelectorResponseError("The optional LLM response was invalid.")
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = data.get("output")
    if isinstance(output, list):
        for output_item in output:
            if not isinstance(output_item, dict):
                continue
            content = output_item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if not isinstance(content_item, dict):
                    continue
                text = content_item.get("text")
                if isinstance(text, str) and text.strip():
                    return text

    raise LLMSelectorResponseError("The optional LLM response did not include text.")


def _parse_meal_keys(response_body: bytes) -> tuple[str, ...]:
    try:
        data = json.loads(response_body.decode("utf-8"))
        response_text = _extract_response_text(data)
        structured_data = json.loads(response_text)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LLMSelectorResponseError(
            "The optional LLM response was not valid JSON."
        ) from error

    if not isinstance(structured_data, dict) or set(structured_data) != {
        "meal_template_keys",
    }:
        raise LLMSelectorResponseError(
            "The optional LLM response did not match the expected schema."
        )
    meal_template_keys = structured_data["meal_template_keys"]
    if not isinstance(meal_template_keys, list):
        raise LLMSelectorResponseError(
            "The optional LLM response did not match the expected schema."
        )
    if any(not isinstance(key, str) for key in meal_template_keys):
        raise LLMSelectorResponseError(
            "The optional LLM response did not match the expected schema."
        )
    return tuple(meal_template_keys)


def suggest_meal_candidate_keys(
    request: ParsedRequest,
    candidate_templates: Sequence[MealTemplate],
    *,
    meal_catalogue: MealCatalogue | None = None,
    environment: Mapping[str, str] | None = None,
    transport: Transport | None = None,
) -> tuple[str, ...] | None:
    """Return validated LLM-suggested meal keys, or None when disabled."""
    config = load_llm_selector_config(environment)
    if not config.enabled:
        return None

    selected_transport = transport or _post_openai_responses
    payload = create_openai_responses_payload(request, candidate_templates, config)
    status, response_body = selected_transport(payload, config)
    if status != 200:
        raise LLMSelectorResponseError(
            f"OpenAI Responses API returned HTTP {status}."
        )

    meal_template_keys = _parse_meal_keys(response_body)
    selected_catalogue = meal_catalogue or load_default_meal_catalogue()
    validate_meal_candidate_keys(
        meal_template_keys,
        request,
        selected_catalogue,
    )
    return meal_template_keys
