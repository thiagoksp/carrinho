from dataclasses import replace
import json
import unittest
from unittest.mock import Mock, patch

import llm_selector
from llm_selector import (
    DEFAULT_MODEL,
    LLMSelectorConfigError,
    LLMSelectorResponseError,
    create_openai_responses_payload,
    load_llm_selector_config,
    suggest_meal_candidate_keys,
)
from meal_catalogue import MealCatalogue, load_default_meal_catalogue
from request_parser import ParsedRequest


def _request() -> ParsedRequest:
    return ParsedRequest(
        budget=80,
        currency="CAD",
        people=2,
        days=4,
        cooking_energy="low",
        pantry_items=["rice", "7 eggs"],
        dietary_restrictions=["lactose intolerance"],
        avoided_product_keys=[],
        preferred_product_keys=["chicken"],
    )


def _candidates():
    return load_default_meal_catalogue().templates[:3]


def _response(keys: list[str]) -> bytes:
    return json.dumps(
        {
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps({"meal_template_keys": keys}),
                        },
                    ],
                },
            ],
        }
    ).encode("utf-8")


class TestLLMSelector(unittest.TestCase):
    def test_disabled_by_default_and_does_not_call_transport(self) -> None:
        transport = Mock(side_effect=AssertionError("network not allowed"))

        result = suggest_meal_candidate_keys(
            _request(),
            _candidates(),
            environment={},
            transport=transport,
        )

        self.assertIsNone(result)
        transport.assert_not_called()

    def test_rejects_invalid_configuration_before_transport(self) -> None:
        cases = (
            (
                {"CARRINHO_LLM_SELECTOR_ENABLED": "yes"},
                "must be 0 or 1",
            ),
            (
                {"CARRINHO_LLM_SELECTOR_ENABLED": "1"},
                "OPENAI_API_KEY is required",
            ),
            (
                {
                    "CARRINHO_LLM_SELECTOR_ENABLED": "1",
                    "OPENAI_API_KEY": "Bearer test",
                },
                "OPENAI_API_KEY is invalid",
            ),
            (
                {
                    "CARRINHO_LLM_SELECTOR_ENABLED": "1",
                    "OPENAI_API_KEY": "sk-test\rbad",
                },
                "OPENAI_API_KEY is invalid",
            ),
            (
                {
                    "CARRINHO_LLM_SELECTOR_ENABLED": "1",
                    "CARRINHO_LLM_PROVIDER": "other",
                    "OPENAI_API_KEY": "sk-test",
                },
                "Only the openai",
            ),
        )
        for environment, message in cases:
            with self.subTest(message=message):
                transport = Mock()
                with self.assertRaisesRegex(LLMSelectorConfigError, message):
                    suggest_meal_candidate_keys(
                        _request(),
                        _candidates(),
                        environment=environment,
                        transport=transport,
                    )
                transport.assert_not_called()

    def test_payload_uses_structured_outputs_and_candidate_enums(self) -> None:
        config = load_llm_selector_config(
            {
                "CARRINHO_LLM_SELECTOR_ENABLED": "1",
                "OPENAI_API_KEY": "sk-test",
            }
        )
        payload = create_openai_responses_payload(_request(), _candidates(), config)
        serialized = json.dumps(payload, ensure_ascii=False)
        schema = payload["text"]["format"]["schema"]

        self.assertEqual(payload["model"], DEFAULT_MODEL)
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["required"], ["meal_template_keys"])
        self.assertEqual(
            schema["properties"]["meal_template_keys"]["items"]["enum"],
            [template.key for template in _candidates()],
        )
        for forbidden_text in (
            "CAD$",
            "price",
            "retailer",
            "Authorization",
            "OPENAI_API_KEY",
            "api_key",
            "sk-test",
        ):
            self.assertNotIn(forbidden_text, serialized)

    def test_accepts_valid_structured_response_after_local_validation(self) -> None:
        keys = [_candidates()[1].key, _candidates()[0].key]
        transport = Mock(return_value=(200, _response(keys)))

        result = suggest_meal_candidate_keys(
            _request(),
            _candidates(),
            environment={
                "CARRINHO_LLM_SELECTOR_ENABLED": "1",
                "OPENAI_API_KEY": "sk-test",
            },
            transport=transport,
        )

        self.assertEqual(result, tuple(keys))
        payload, config = transport.call_args.args
        self.assertEqual(config.model, DEFAULT_MODEL)
        self.assertEqual(config.timeout_seconds, 10)
        self.assertIn("json_schema", json.dumps(payload))

    def test_rejects_unknown_duplicate_and_incompatible_meal_keys(self) -> None:
        catalogue = load_default_meal_catalogue()
        unsafe_template = replace(catalogue.templates[0], dietary_tags=())
        unsafe_catalogue = MealCatalogue(
            description=catalogue.description,
            templates=(unsafe_template,),
        )
        cases = (
            (_response(["invented_meal"]), "Unknown meal candidate key"),
            (_response([_candidates()[0].key, _candidates()[0].key]), "duplicates"),
        )
        for body, message in cases:
            with self.subTest(message=message):
                transport = Mock(return_value=(200, body))
                with self.assertRaisesRegex(ValueError, message):
                    suggest_meal_candidate_keys(
                        _request(),
                        _candidates(),
                        environment={
                            "CARRINHO_LLM_SELECTOR_ENABLED": "1",
                            "OPENAI_API_KEY": "sk-test",
                        },
                        transport=transport,
                    )

        transport = Mock(return_value=(200, _response([unsafe_template.key])))
        with self.assertRaisesRegex(ValueError, "dietary restrictions"):
            suggest_meal_candidate_keys(
                _request(),
                (unsafe_template,),
                meal_catalogue=unsafe_catalogue,
                environment={
                    "CARRINHO_LLM_SELECTOR_ENABLED": "1",
                    "OPENAI_API_KEY": "sk-test",
                },
                transport=transport,
            )

    def test_response_errors_are_sanitized(self) -> None:
        cases = (
            (Mock(return_value=(401, b'{"error":"secret body"}')), "HTTP 401"),
            (Mock(return_value=(200, b"not-json")), "not valid JSON"),
            (
                Mock(return_value=(200, json.dumps({"output": []}).encode("utf-8"))),
                "did not include text",
            ),
            (
                Mock(return_value=(200, _response([]))),
                "must not be empty",
            ),
        )
        for transport, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(Exception, message) as context:
                    suggest_meal_candidate_keys(
                        _request(),
                        _candidates(),
                        environment={
                            "CARRINHO_LLM_SELECTOR_ENABLED": "1",
                            "OPENAI_API_KEY": "sk-secret",
                        },
                        transport=transport,
                    )
                error_text = str(context.exception)
                self.assertNotIn("sk-secret", error_text)
                self.assertNotIn("secret body", error_text)

    def test_real_transport_is_not_used_when_disabled(self) -> None:
        with (
            patch("socket.socket", side_effect=AssertionError("network not allowed")),
            patch(
                "socket.create_connection",
                side_effect=AssertionError("network not allowed"),
            ),
            patch("socket.getaddrinfo", side_effect=AssertionError("network not allowed")),
        ):
            result = suggest_meal_candidate_keys(
                _request(),
                _candidates(),
                environment={},
            )

        self.assertIsNone(result)

    def test_openai_transport_uses_dev_safe_headers_and_limits_response(self) -> None:
        class FakeResponse:
            status = 200

            def read(self, amount: int) -> bytes:
                self.amount = amount
                return b'{"output_text":"{\\"meal_template_keys\\":[\\"x\\"]}"}'

        class FakeConnection:
            def __init__(self, host: str, timeout: float) -> None:
                self.host = host
                self.timeout = timeout
                self.closed = False

            def request(
                self,
                method: str,
                path: str,
                body: bytes,
                headers: dict[str, str],
            ) -> None:
                self.method = method
                self.path = path
                self.body = body
                self.headers = headers

            def getresponse(self) -> FakeResponse:
                self.response = FakeResponse()
                return self.response

            def close(self) -> None:
                self.closed = True

        holder: dict[str, FakeConnection] = {}

        def fake_connection(host: str, timeout: float) -> FakeConnection:
            holder["connection"] = FakeConnection(host, timeout)
            return holder["connection"]

        config = load_llm_selector_config(
            {
                "CARRINHO_LLM_SELECTOR_ENABLED": "1",
                "OPENAI_API_KEY": "sk-test",
            }
        )
        payload = {"model": DEFAULT_MODEL}

        with patch("http.client.HTTPSConnection", side_effect=fake_connection):
            status, body = llm_selector._post_openai_responses(payload, config)

        connection = holder["connection"]
        self.assertEqual(status, 200)
        self.assertIn(b"meal_template_keys", body)
        self.assertEqual(connection.host, "api.openai.com")
        self.assertEqual(connection.timeout, 10)
        self.assertEqual(connection.method, "POST")
        self.assertEqual(connection.path, "/v1/responses")
        self.assertEqual(connection.headers["Authorization"], "Bearer sk-test")
        self.assertEqual(connection.headers["Content-Type"], "application/json")
        self.assertEqual(connection.response.amount, llm_selector.MAX_RESPONSE_BYTES + 1)
        self.assertTrue(connection.closed)


if __name__ == "__main__":
    unittest.main()
