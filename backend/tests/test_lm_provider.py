import json

import httpx

from app.config import Settings
from app.llm_provider import LLMChatMessage, LMStudioNativeProvider


def _settings(**overrides) -> Settings:
    values = {
        "lm_studio_base_url": "http://llm.local/v1",
        "lm_studio_chat_model": "chat-model",
        "lm_studio_chat_context_length": 112640,
        "lm_studio_eval_batch_size": 4096,
        "lm_studio_flash_attention": True,
        "lm_studio_offload_kv_cache_to_gpu": True,
        "lm_studio_auto_load_chat_model": True,
        "lm_studio_default_max_output_tokens": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_native_provider_lists_model_keys_and_loaded_model_instances() -> None:
    client = httpx.Client(
        base_url="http://llm.local",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "models": [
                        {"key": "fallback-model", "loaded_instances": [{"id": "chat-model:1"}]},
                        {"key": "available-model"},
                    ]
                },
            )
        ),
    )

    provider = LMStudioNativeProvider(_settings(), client)

    assert [model.id for model in provider.list_models()] == ["fallback-model", "available-model"]
    assert provider.loaded_model_instance_ids() == ["chat-model:1"]


def test_native_provider_loads_configured_chat_model_with_profile() -> None:
    paths: list[str] = []
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(f"{request.method} {request.url.path}")
        if request.method == "GET" and request.url.path == "/api/v1/models":
            return httpx.Response(200, json={"models": [{"key": "chat-model", "loaded_instances": []}]})
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "type": "llm",
                "instance_id": "chat-model:1",
                "load_time_seconds": 1.25,
                "status": "loaded",
                "load_config": {"context_length": 112640},
            },
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioNativeProvider(_settings(), client)

    result = provider.load_configured_chat_model()

    assert paths == ["GET /api/v1/models", "POST /api/v1/models/load"]
    assert captured_payload == {
        "model": "chat-model",
        "context_length": 112640,
        "eval_batch_size": 4096,
        "flash_attention": True,
        "offload_kv_cache_to_gpu": True,
        "echo_load_config": True,
    }
    assert result.instance_id == "chat-model:1"
    assert result.status == "loaded"


def test_native_provider_unloads_model_instance() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        return httpx.Response(200, json={"instance_id": "chat-model:1"})

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioNativeProvider(_settings(), client)

    result = provider.unload_model_instance("chat-model:1")

    assert captured_payload == {"instance_id": "chat-model:1"}
    assert result.instance_id == "chat-model:1"


def test_native_provider_auto_loads_missing_configured_chat_model_before_chat() -> None:
    paths: list[str] = []
    captured_payloads: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(f"{request.method} {request.url.path}")
        if request.method == "GET" and request.url.path == "/api/v1/models":
            return httpx.Response(200, json={"models": [{"key": "chat-model", "loaded_instances": []}]})
        payload = json.loads(request.content)
        captured_payloads.append(payload)
        if request.url.path == "/api/v1/models/load":
            return httpx.Response(200, json={"type": "llm", "instance_id": "chat-model:4", "status": "loaded"})
        return httpx.Response(200, json={"output": [{"type": "message", "content": "Szia"}]})

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioNativeProvider(_settings(), client)

    result = provider.chat_completion("chat-model", [LLMChatMessage(role="user", content="hello")])

    assert paths == ["GET /api/v1/models", "POST /api/v1/models/load", "POST /api/v1/chat"]
    assert captured_payloads[0]["model"] == "chat-model"
    assert captured_payloads[1]["model"] == "chat-model:4"
    assert result.model == "chat-model:4"
    assert result.content == "Szia"


def test_native_provider_sends_reasoning_off_only_for_qwen_models() -> None:
    captured_payloads: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"output": [{"type": "message", "content": "ok"}]})

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioNativeProvider(_settings(lm_studio_auto_load_chat_model=False), client)

    provider.chat_completion("qwen/qwen3", [LLMChatMessage(role="user", content="hello")])
    provider.chat_completion("llama", [LLMChatMessage(role="user", content="hello")])
    provider.chat_completion(
        "qwen/qwen3",
        [LLMChatMessage(role="user", content="hello")],
        reasoning_mode="model_default",
    )

    assert captured_payloads[0]["reasoning"] == "off"
    assert "reasoning" not in captured_payloads[1]
    assert "reasoning" not in captured_payloads[2]


def test_native_provider_omits_max_output_tokens_when_unset() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        return httpx.Response(200, json={"output": [{"type": "message", "content": "ok"}]})

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioNativeProvider(_settings(lm_studio_auto_load_chat_model=False), client)

    provider.chat_completion("chat-model", [LLMChatMessage(role="user", content="hello")])

    assert "max_output_tokens" not in captured_payload
