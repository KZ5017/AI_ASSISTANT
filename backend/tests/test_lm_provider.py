import json

import httpx

from app.config import Settings
from app.llm_provider import (
    LLMChatMessage,
    LLMProviderError,
    LMStudioNativeProvider,
    LMStudioResponsesProvider,
    get_llm_provider,
    get_llm_provider_for_tool_mode,
)


def _settings(**overrides) -> Settings:
    values = {
        "llm_provider": "lm_studio_native",
        "lm_studio_base_url": "http://llm.local/v1",
        "lm_studio_chat_model": "chat-model",
        "lm_studio_auto_load_chat_model": True,
        "lm_studio_default_max_output_tokens": None,
        "lm_studio_mcp_execution_mode": "responses_remote",
        "lm_studio_responses_obsidian_mcp_url": None,
        "lm_studio_responses_obsidian_mcp_token": None,
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
            return httpx.Response(
                200, json={"models": [{"key": "chat-model", "loaded_instances": []}]}
            )
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "type": "llm",
                "instance_id": "chat-model:1",
                "load_time_seconds": 1.25,
                "status": "loaded",
            },
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioNativeProvider(_settings(), client)

    result = provider.load_configured_chat_model()

    assert paths == ["GET /api/v1/models", "POST /api/v1/models/load"]
    assert captured_payload == {
        "model": "chat-model",
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


def test_native_provider_does_not_auto_load_missing_configured_chat_model_before_chat() -> None:
    paths: list[str] = []
    captured_payloads: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(f"{request.method} {request.url.path}")
        payload = json.loads(request.content)
        captured_payloads.append(payload)
        return httpx.Response(200, json={"output": [{"type": "message", "content": "Szia"}]})

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioNativeProvider(_settings(), client)

    result = provider.chat_completion("chat-model", [LLMChatMessage(role="user", content="hello")])

    assert paths == ["POST /api/v1/chat"]
    assert captured_payloads[0]["model"] == "chat-model"
    assert result.model == "chat-model"
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


def test_native_provider_build_client_adds_authorization_header_when_token_is_configured() -> None:
    provider = LMStudioNativeProvider(
        _settings(lm_studio_api_token="test-token"),
    )

    client = provider._build_client()

    try:
        assert client.headers["authorization"] == "Bearer test-token"
    finally:
        client.close()


def test_native_provider_streams_message_reasoning_error_and_done_events() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        stream_body = "".join(
            [
                "event: chat.start\n",
                'data: {"type":"chat.start","model_instance_id":"chat-model"}\n\n',
                "event: reasoning.delta\n",
                'data: {"type":"reasoning.delta","content":"Gondolkodom"}\n\n',
                "event: message.delta\n",
                'data: {"type":"message.delta","content":"Szia"}\n\n',
                "event: message.delta\n",
                'data: {"type":"message.delta","content":"!"}\n\n',
                "event: error\n",
                'data: {"type":"error","error":{"message":"reszleges figyelmeztetes"}}\n\n',
                "event: chat.end\n",
                'data: {"type":"chat.end","result":{"model_instance_id":"chat-model:1","output":[{"type":"message","content":"Szia!"}],"stats":{"tokens_per_second":42}}}\n\n',
            ]
        )
        return httpx.Response(
            200, content=stream_body.encode(), headers={"content-type": "text/event-stream"}
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioNativeProvider(_settings(lm_studio_auto_load_chat_model=False), client)

    events = list(
        provider.chat_completion_stream(
            "chat-model", [LLMChatMessage(role="user", content="hello")]
        )
    )

    assert captured_payload["stream"] is True
    assert captured_payload["model"] == "chat-model"
    assert [event.type for event in events] == [
        "status",
        "reasoning_delta",
        "message_delta",
        "message_delta",
        "error",
        "done",
    ]
    assert events[1].content == "Gondolkodom"
    assert events[2].content == "Szia"
    assert events[3].content == "!"
    assert events[4].error_message == "reszleges figyelmeztetes"
    assert events[5].final_content == "Szia!"
    assert events[5].model == "chat-model:1"


def test_native_provider_stream_reuses_chat_payload_rules() -> None:
    captured_payloads: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payloads.append(json.loads(request.content))
        stream_body = (
            "event: chat.end\n"
            'data: {"type":"chat.end","result":{"model_instance_id":"qwen/qwen3","output":[{"type":"message","content":"ok"}]}}\n\n'
        )
        return httpx.Response(
            200, content=stream_body.encode(), headers={"content-type": "text/event-stream"}
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioNativeProvider(
        _settings(lm_studio_auto_load_chat_model=False, lm_studio_default_max_output_tokens=123),
        client,
    )

    events = list(
        provider.chat_completion_stream(
            "qwen/qwen3",
            [
                LLMChatMessage(role="system", content="Legyel rovid"),
                LLMChatMessage(role="user", content="hello"),
            ],
            temperature=0.2,
        )
    )

    assert len(events) == 1
    assert events[0].type == "done"
    assert captured_payloads == [
        {
            "model": "qwen/qwen3",
            "input": [{"type": "text", "content": "USER:\nhello"}],
            "system_prompt": "Legyel rovid",
            "temperature": 0.2,
            "store": False,
            "max_output_tokens": 123,
            "reasoning": "off",
            "stream": True,
        }
    ]


def test_native_provider_stream_maps_plugin_tool_events_to_tool_activity() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        separator = "\n\n"
        stream_body = "".join(
            [
                "event: tool_call.name\n",
                "data: "
                + json.dumps(
                    {
                        "type": "tool_call.name",
                        "tool_name": "get_workbook_metadata",
                        "provider_info": {"type": "plugin", "plugin_id": "mcp/excel"},
                    }
                )
                + separator,
                "event: tool_call.success\n",
                "data: "
                + json.dumps(
                    {
                        "type": "tool_call.success",
                        "tool": "get_workbook_metadata",
                        "arguments": {"filepath": "00-INDEX.xlsx"},
                        "output": "{}",
                        "provider_info": {"type": "plugin", "plugin_id": "mcp/excel"},
                    }
                )
                + separator,
                "event: chat.end\n",
                "data: "
                + json.dumps(
                    {
                        "type": "chat.end",
                        "result": {
                            "model_instance_id": "chat-model:1",
                            "output": [{"type": "message", "content": "ok"}],
                        },
                    }
                )
                + separator,
            ]
        )
        return httpx.Response(
            200, content=stream_body.encode(), headers={"content-type": "text/event-stream"}
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioNativeProvider(_settings(), client)

    events = list(
        provider.chat_completion_stream(
            "chat-model", [LLMChatMessage(role="user", content="hello")]
        )
    )

    assert [event.type for event in events] == ["tool_activity", "tool_activity", "done"]
    assert "Excel eszköz indult" in (events[0].content or "")
    assert "get_workbook_metadata" in (events[1].content or "")
    assert "00-INDEX.xlsx" in (events[1].content or "")


def test_native_provider_stream_raises_when_done_has_no_message_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        stream_body = 'event: chat.end\ndata: {"type":"chat.end","result":{"output":[{"type":"reasoning","content":"x"}]}}\n\n'
        return httpx.Response(
            200, content=stream_body.encode(), headers={"content-type": "text/event-stream"}
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioNativeProvider(_settings(lm_studio_auto_load_chat_model=False), client)

    try:
        list(
            provider.chat_completion_stream(
                "chat-model", [LLMChatMessage(role="user", content="hello")]
            )
        )
    except Exception as exc:
        assert "no message content" in str(exc)
    else:
        raise AssertionError("Expected provider error")


def test_provider_factory_defaults_to_native_provider() -> None:
    provider = get_llm_provider(_settings())

    assert isinstance(provider, LMStudioNativeProvider)
    assert provider.provider_name == "lm_studio_native"


def test_provider_factory_rejects_unknown_provider() -> None:
    settings = _settings(llm_provider="unknown")

    try:
        get_llm_provider(settings)
    except LLMProviderError as exc:
        assert "Unsupported LLM provider: unknown" in str(exc)
    else:
        raise AssertionError("Expected LLMProviderError")


def test_responses_obsidian_remote_mcp_empty_config_values_are_none() -> None:
    settings = _settings(
        lm_studio_responses_obsidian_mcp_url="",
        lm_studio_responses_obsidian_mcp_token="",
    )

    assert settings.lm_studio_responses_obsidian_mcp_url is None
    assert settings.lm_studio_responses_obsidian_mcp_token is None


def test_responses_obsidian_remote_mcp_token_config_can_be_set() -> None:
    settings = _settings(lm_studio_responses_obsidian_mcp_token="obsidian-token")

    assert settings.lm_studio_responses_obsidian_mcp_token == "obsidian-token"


def test_provider_factory_can_select_responses_provider() -> None:
    provider = get_llm_provider(_settings(llm_provider="lm_studio_responses"))

    assert isinstance(provider, LMStudioResponsesProvider)
    assert provider.provider_name == "lm_studio_responses"


def test_tool_mode_provider_uses_native_only_for_registered_mcp_modes() -> None:
    settings = _settings(
        llm_provider="lm_studio_responses",
        lm_studio_mcp_execution_mode="lmstudio_registered",
    )

    assert isinstance(get_llm_provider_for_tool_mode(settings, "excel"), LMStudioNativeProvider)
    assert isinstance(
        get_llm_provider_for_tool_mode(settings, "obsidian"), LMStudioNativeProvider
    )
    assert isinstance(get_llm_provider_for_tool_mode(settings, "none"), LMStudioResponsesProvider)
    assert isinstance(
        get_llm_provider_for_tool_mode(settings, "graphrag"), LMStudioResponsesProvider
    )


def test_tool_mode_provider_preserves_responses_remote_profile() -> None:
    settings = _settings(
        llm_provider="lm_studio_responses",
        lm_studio_mcp_execution_mode="responses_remote",
    )

    assert isinstance(get_llm_provider_for_tool_mode(settings, "excel"), LMStudioResponsesProvider)
    assert isinstance(
        get_llm_provider_for_tool_mode(settings, "obsidian"), LMStudioResponsesProvider
    )


def test_responses_provider_lists_openai_compatible_models() -> None:
    client = httpx.Client(
        base_url="http://llm.local",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"data": [{"id": "chat-model"}, {"id": "other-model"}]},
            )
        ),
    )
    provider = LMStudioResponsesProvider(_settings(), client)

    assert [model.id for model in provider.list_models()] == ["chat-model", "other-model"]


def test_responses_provider_smoke_check_reads_native_loaded_state() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "chat-model"}]})
        return httpx.Response(
            200,
            json={"models": [{"key": "chat-model", "loaded_instances": [{"id": "chat-model:1"}]}]},
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioResponsesProvider(_settings(), client)

    result = provider.smoke_check("chat-model")

    assert result.provider == "lm_studio_responses"
    assert result.base_url == "http://llm.local"
    assert result.reachable is True
    assert result.configured_chat_model_available is True
    assert result.configured_chat_model_loaded is True
    assert result.selected_chat_model_loaded is True
    assert result.loaded_model_ids == ["chat-model:1"]


def test_responses_provider_omits_reasoning_when_model_default_is_requested() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "ok"}],
                    }
                ]
            },
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioResponsesProvider(_settings(), client)

    provider.chat_completion(
        "chat-model",
        [LLMChatMessage(role="user", content="hello")],
        reasoning_mode="model_default",
    )

    assert "reasoning" not in captured_payload


def test_responses_provider_sends_responses_payload_and_reads_output_text() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": "Szia"},
                            {"type": "output_text", "text": "!"},
                        ],
                    }
                ]
            },
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioResponsesProvider(
        _settings(lm_studio_auto_load_chat_model=True, lm_studio_default_max_output_tokens=321),
        client,
    )

    result = provider.chat_completion(
        "chat-model",
        [
            LLMChatMessage(role="system", content="Legyel rovid"),
            LLMChatMessage(role="user", content="hello"),
        ],
        temperature=0.2,
    )

    assert captured_payload == {
        "model": "chat-model",
        "input": [{"role": "user", "content": [{"type": "input_text", "text": "hello"}]}],
        "temperature": 0.2,
        "store": False,
        "instructions": "Legyel rovid",
        "reasoning": {"effort": "none"},
        "max_output_tokens": 321,
    }
    assert result.model == "chat-model"
    assert result.content == "Szia\n!"


def test_responses_provider_sends_assistant_history_as_output_text() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "masodik"}],
                    }
                ]
            },
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioResponsesProvider(_settings(), client)

    provider.chat_completion(
        "chat-model",
        [
            LLMChatMessage(role="user", content="elso"),
            LLMChatMessage(role="assistant", content="valasz"),
            LLMChatMessage(role="user", content="masodik kerdes"),
        ],
    )

    assert captured_payload["input"] == [
        {"role": "user", "content": [{"type": "input_text", "text": "elso"}]},
        {"role": "assistant", "content": [{"type": "output_text", "text": "valasz"}]},
        {"role": "user", "content": [{"type": "input_text", "text": "masodik kerdes"}]},
    ]


def test_responses_provider_maps_excel_integration_to_remote_mcp_tool() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "ok"}],
                    }
                ]
            },
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioResponsesProvider(_settings(), client)

    result = provider.chat_completion(
        "chat-model",
        [LLMChatMessage(role="user", content="hello")],
        integrations=["mcp/excel"],
    )

    assert result.content == "ok"
    assert captured_payload["tools"] == [
        {
            "type": "mcp",
            "server_label": "excel",
            "server_url": "http://127.0.0.1:8017/mcp",
            "allowed_tools": [
                "get_workbook_metadata",
                "list_excel_sheets",
                "list_excel_columns",
                "read_data_from_excel",
                "describe_excel_sheet",
                "detect_header_row",
                "find_relevant_column",
                "lookup_excel_rows",
                "filter_excel_rows",
                "find_excel_rows_with_same_value",
                "aggregate_excel_data",
            ],
        }
    ]


def test_responses_provider_maps_obsidian_integration_to_remote_mcp_tool_without_token() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "ok"}],
                    }
                ]
            },
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioResponsesProvider(
        _settings(lm_studio_responses_obsidian_mcp_url="https://127.0.0.1:27124/mcp/"),
        client,
    )

    result = provider.chat_completion(
        "chat-model",
        [LLMChatMessage(role="user", content="hello")],
        integrations=["mcp/obsidian"],
    )

    assert result.content == "ok"
    assert captured_payload["tools"] == [
        {
            "type": "mcp",
            "server_label": "obsidian",
            "server_url": "https://127.0.0.1:27124/mcp/",
            "allowed_tools": [
                "vault_list",
                "vault_read",
                "vault_get_document_map",
                "search_query",
                "search_simple",
                "tag_list",
            ],
        }
    ]


def test_responses_provider_maps_obsidian_integration_to_remote_mcp_tool_with_token() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "ok"}],
                    }
                ]
            },
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioResponsesProvider(
        _settings(
            lm_studio_responses_obsidian_mcp_url="https://127.0.0.1:27124/mcp/",
            lm_studio_responses_obsidian_mcp_token="obsidian-token",
        ),
        client,
    )

    result = provider.chat_completion(
        "chat-model",
        [LLMChatMessage(role="user", content="hello")],
        integrations=["mcp/obsidian"],
    )

    assert result.content == "ok"
    assert captured_payload["tools"] == [
        {
            "type": "mcp",
            "server_label": "obsidian",
            "server_url": "https://127.0.0.1:27124/mcp/",
            "headers": {"Authorization": "Bearer obsidian-token"},
            "allowed_tools": [
                "vault_list",
                "vault_read",
                "vault_get_document_map",
                "search_query",
                "search_simple",
                "tag_list",
            ],
        }
    ]


def test_responses_provider_rejects_unconfigured_obsidian_remote_mcp_url() -> None:
    provider = LMStudioResponsesProvider(_settings())

    try:
        provider.chat_completion(
            "chat-model",
            [LLMChatMessage(role="user", content="hello")],
            integrations=["mcp/obsidian"],
        )
    except LLMProviderError as exc:
        assert "Responses Obsidian MCP URL is not configured" in str(exc)
    else:
        raise AssertionError("Expected LLMProviderError")


def test_responses_provider_rejects_unknown_remote_mcp_integration() -> None:
    provider = LMStudioResponsesProvider(_settings())

    try:
        provider.chat_completion(
            "chat-model",
            [LLMChatMessage(role="user", content="hello")],
            integrations=["mcp/unknown"],
        )
    except LLMProviderError as exc:
        assert "Unsupported Responses MCP integration: mcp/unknown" in str(exc)
    else:
        raise AssertionError("Expected LLMProviderError")


def test_responses_provider_rejects_load_unload_for_now() -> None:
    provider = LMStudioResponsesProvider(_settings())

    for action in (
        lambda: provider.load_chat_model("chat-model"),
        lambda: provider.unload_chat_model("chat-model"),
        lambda: provider.unload_model_instance("chat-model:1"),
    ):
        try:
            action()
        except LLMProviderError as exc:
            assert "not supported" in str(exc)
        else:
            raise AssertionError("Expected LLMProviderError")


def test_responses_provider_streams_reasoning_message_status_and_done_events() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        stream_body = "".join(
            [
                "event: response.created\n",
                'data: {"type":"response.created","response":{"id":"resp_1","model":"chat-model"}}\n\n',
                "event: response.reasoning_text.delta\n",
                'data: {"type":"response.reasoning_text.delta","delta":"Gondolkodom"}\n\n',
                "event: response.output_item.added\n",
                'data: {"type":"response.output_item.added","item":{"type":"mcp_list_tools","server_label":"excel"}}\n\n',
                "event: response.output_item.done\n",
                'data: {"type":"response.output_item.done","item":{"type":"mcp_list_tools","server_label":"excel","tools":[{"name":"lookup_excel_rows"}]}}\n\n',
                "event: response.output_item.added\n",
                'data: {"type":"response.output_item.added","item":{"type":"mcp_call","server_label":"excel","name":"lookup_excel_rows","status":"in_progress"}}\n\n',
                "event: response.output_item.done\n",
                'data: {"type":"response.output_item.done","item":{"type":"mcp_call","server_label":"excel","name":"lookup_excel_rows","status":"completed","arguments":"{\\"filepath\\":\\"adat.xlsx\\",\\"sheet_name\\":\\"Data\\",\\"lookup_column\\":\\"Name\\",\\"lookup_value\\":\\"HBO\\",\\"match_mode\\":\\"contains\\"}","output":"[{\\"type\\":\\"text\\",\\"text\\":\\"{\\\\\\"matches\\\\\\":3,\\\\\\"rows\\\\\\":[]}\\"}]"}}\n\n',
                "event: response.output_text.delta\n",
                'data: {"type":"response.output_text.delta","delta":"Szia"}\n\n',
                "event: response.output_text.delta\n",
                'data: {"type":"response.output_text.delta","delta":"!"}\n\n',
                "event: response.completed\n",
                'data: {"type":"response.completed","response":{"model":"chat-model","output":[{"type":"message","content":[{"type":"output_text","text":"Szia!"}]}]}}\n\n',
            ]
        )
        return httpx.Response(
            200, content=stream_body.encode(), headers={"content-type": "text/event-stream"}
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioResponsesProvider(
        _settings(lm_studio_default_max_output_tokens=123),
        client,
    )

    events = list(
        provider.chat_completion_stream(
            "chat-model",
            [
                LLMChatMessage(role="system", content="Legyel rovid"),
                LLMChatMessage(role="user", content="hello"),
            ],
            temperature=0.2,
        )
    )

    assert captured_payload == {
        "model": "chat-model",
        "input": [{"role": "user", "content": [{"type": "input_text", "text": "hello"}]}],
        "temperature": 0.2,
        "store": False,
        "instructions": "Legyel rovid",
        "reasoning": {"effort": "none"},
        "max_output_tokens": 123,
        "stream": True,
    }
    assert [event.type for event in events] == [
        "status",
        "reasoning_delta",
        "tool_activity",
        "tool_activity",
        "tool_activity",
        "tool_activity",
        "message_delta",
        "message_delta",
        "done",
    ]
    assert events[1].content == "Gondolkodom"
    assert events[2].content == "- *Excel eszközlista lekérése*"
    assert events[3].content == "- **Excel eszközlista elérhető**"
    assert events[4].content == "- *Excel eszköz indult:* `lookup_excel_rows`"
    assert (
        events[5].content
        == "- **Excel eszköz:** `lookup_excel_rows`\n  - Fájl: `adat.xlsx`, munkalap: `Data`\n  - Keresés: `Name = HBO` (részszöveg)\n  - Találat: **3 sor**"
    )
    assert events[6].content == "Szia"
    assert events[7].content == "!"
    assert events[8].final_content == "Szia!"
    assert events[8].model == "chat-model"


def test_responses_provider_stream_maps_failed_and_incomplete_to_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        stream_body = "".join(
            [
                "event: response.failed\n",
                'data: {"type":"response.failed","response":{"status":"failed","error":{"message":"stream failed"}}}\n\n',
                "event: response.incomplete\n",
                'data: {"type":"response.incomplete","response":{"status":"incomplete"}}\n\n',
            ]
        )
        return httpx.Response(
            200, content=stream_body.encode(), headers={"content-type": "text/event-stream"}
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioResponsesProvider(_settings(), client)

    events = list(
        provider.chat_completion_stream(
            "chat-model", [LLMChatMessage(role="user", content="hello")]
        )
    )

    assert [event.type for event in events] == ["error", "error"]
    assert events[0].error_message == "stream failed"
    assert events[1].error_message == "LM Studio Responses API stream ended with status: incomplete"


def test_responses_provider_stream_maps_excel_integration_to_remote_mcp_tool() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        stream_body = (
            "event: response.completed\n"
            'data: {"type":"response.completed","response":{"model":"chat-model","output":[{"type":"message","content":[{"type":"output_text","text":"ok"}]}]}}\n\n'
        )
        return httpx.Response(
            200, content=stream_body.encode(), headers={"content-type": "text/event-stream"}
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioResponsesProvider(_settings(), client)

    events = list(
        provider.chat_completion_stream(
            "chat-model",
            [LLMChatMessage(role="user", content="hello")],
            integrations=["mcp/excel"],
        )
    )

    assert events[-1].type == "done"
    assert captured_payload["stream"] is True
    assert captured_payload["tools"][0]["server_label"] == "excel"
    assert captured_payload["tools"][0]["server_url"] == "http://127.0.0.1:8017/mcp"


def test_responses_provider_separates_work_narration_from_final_answer() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Megnezem az indexet."}],
                    },
                    {"type": "mcp_call", "name": "read_data_from_excel"},
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Ellenorzom a forrast."}],
                    },
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Ez a vegso valasz."}],
                    },
                ]
            },
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioResponsesProvider(_settings(), client)

    result = provider.chat_completion("chat-model", [LLMChatMessage(role="user", content="hello")])

    assert result.content == "Ez a vegso valasz."
    assert result.work_narration_content == "Megnezem az indexet.\n\nEllenorzom a forrast."


def test_responses_provider_stream_done_separates_work_narration_from_final_answer() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        completed_payload = {
            "type": "response.completed",
            "response": {
                "model": "chat-model",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Megnezem a forrast."}],
                    },
                    {"type": "mcp_call", "name": "read_data_from_excel"},
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Ez a vegso valasz."}],
                    },
                ],
            },
        }
        separator = chr(10) + chr(10)
        stream_body = "".join(
            [
                "event: response.output_text.delta" + chr(10),
                "data: "
                + json.dumps({"type": "response.output_text.delta", "delta": "Megnezem"})
                + separator,
                "event: response.output_text.delta" + chr(10),
                "data: "
                + json.dumps({"type": "response.output_text.delta", "delta": " a forrast"})
                + separator,
                "event: response.completed" + chr(10),
                "data: " + json.dumps(completed_payload) + separator,
            ]
        )
        return httpx.Response(
            200, content=stream_body.encode(), headers={"content-type": "text/event-stream"}
        )

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioResponsesProvider(_settings(), client)

    events = list(
        provider.chat_completion_stream(
            "chat-model", [LLMChatMessage(role="user", content="hello")]
        )
    )

    assert [event.type for event in events] == ["message_delta", "message_delta", "done"]
    assert events[-1].final_content == "Ez a vegso valasz."
    assert events[-1].work_narration_content == "Megnezem a forrast."
