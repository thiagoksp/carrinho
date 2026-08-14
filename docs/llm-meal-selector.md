# Optional LLM meal selector

Carrinho can optionally use an LLM to suggest the order of known meal templates. This
feature is disabled by default and is not required for the terminal app, browser app, or
test suite.

## Boundary

The LLM may receive:

- household planning fields already provided to Carrinho;
- pantry item text;
- supported dietary restriction text;
- soft generic food preferences;
- a bounded list of allowed meal templates with stable keys, dish names, tags, and
  generic ingredient product keys.

The LLM may return only:

- an ordered `meal_template_keys` array containing known template keys.

The LLM must not decide or generate:

- dietary safety;
- ingredient quantities;
- package rounding;
- pantry deductions;
- price or cost estimates;
- retailer, SKU, availability, fee, or checkout data.

Local validation remains authoritative. Carrinho rejects unknown keys, duplicate keys,
unsupported hard restrictions, and templates that do not satisfy the current local
dietary tags.

## Structured output contract

Every LLM response uses a JSON Schema Structured Outputs contract:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["meal_template_keys"],
  "properties": {
    "meal_template_keys": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["known_template_key"]
      }
    }
  }
}
```

OpenAI documents Structured Outputs as schema-constrained model output and recommends
using it instead of JSON mode when possible. Carrinho uses the Responses API
`text.format` JSON Schema shape so future provider adapters can keep the same local
contract.

## Configuration

The selector is opt-in through environment variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `CARRINHO_LLM_SELECTOR_ENABLED` | `0` | Must be `1` to allow a network request. |
| `CARRINHO_LLM_PROVIDER` | `openai` | Provider adapter. Only `openai` is implemented. |
| `CARRINHO_LLM_MODEL` | `gpt-5.6-luna` | Model used by the OpenAI adapter. |
| `CARRINHO_LLM_TIMEOUT_SECONDS` | `10` | Request timeout, bounded from 1 to 30 seconds. |
| `CARRINHO_LLM_MAX_CANDIDATES` | `8` | Maximum meal candidates shown to the LLM. |
| `CARRINHO_LLM_MAX_OUTPUT_TOKENS` | `512` | Response budget, bounded from 128 to 2048. |
| `OPENAI_API_KEY` | unset | Required only when the selector is enabled. |

Example PowerShell session:

```powershell
$env:CARRINHO_LLM_SELECTOR_ENABLED = "1"
$env:OPENAI_API_KEY = "<your-api-key>"
.\.venv\Scripts\python.exe web_app.py
```

Do not save API keys in Git, Linear, chat, logs, generated files, or `.env` files that
could be shared. `.env` remains ignored by Git for local experiments.

## Cost guards

- The selector is disabled by default.
- Only a small candidate list is sent.
- Output length is capped.
- No retry is performed automatically.
- The response body is size-limited.
- Prompt and response bodies are not logged or saved by default.
- If enabled configuration is invalid or the provider call fails, Carrinho reports a
  friendly error instead of silently pretending the LLM ran.

## Provider strategy

CAR-13 introduces the adapter boundary but only implements the OpenAI Responses API
target. CAR-15 compares cheaper providers later against the same local eval and schema
contract. A second production provider should not be added until there is evidence that
cost, quality, reliability, or setup effort justifies it.
