import json

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import assistant_service
from app.config import Settings
from app.db import Base
from app.llm_provider import LLMChatCompletion, LLMChatMessage, LMStudioNativeProvider
from app.tool_modes import OBSIDIAN_TOOL_PROMPT, resolve_tool_mode_policy


def _settings(**overrides) -> Settings:
    values = {
        "lm_studio_base_url": "http://llm.local/v1",
        "lm_studio_chat_model": "chat-model",
        "lm_studio_auto_load_chat_model": False,
        "lm_studio_default_max_output_tokens": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_tool_mode_policy_none_has_no_integrations() -> None:
    policy = resolve_tool_mode_policy(_settings(), "none")

    assert policy.id == "none"
    assert policy.integration_ids == ()
    assert policy.prompt_instructions is None


def test_tool_mode_policy_obsidian_uses_configured_integration_id() -> None:
    policy = resolve_tool_mode_policy(_settings(lm_studio_obsidian_integration_id="mcp/my-obsidian"), "obsidian")

    assert policy.id == "obsidian"
    assert policy.integration_ids == ("mcp/my-obsidian",)
    assert policy.prompt_instructions == OBSIDIAN_TOOL_PROMPT
    assert "00-INDEX.md" in policy.prompt_instructions


def test_tool_mode_policy_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError):
        resolve_tool_mode_policy(_settings(), "browser")


def test_native_provider_omits_empty_integrations_and_sends_configured_integrations() -> None:
    captured_payloads: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"output": [{"type": "message", "content": "ok"}]})

    client = httpx.Client(base_url="http://llm.local", transport=httpx.MockTransport(handler))
    provider = LMStudioNativeProvider(_settings(), client)

    provider.chat_completion("chat-model", [LLMChatMessage(role="user", content="hello")], integrations=[])
    provider.chat_completion(
        "chat-model",
        [LLMChatMessage(role="user", content="hello")],
        integrations=["mcp/obsidian"],
    )

    assert "integrations" not in captured_payloads[0]
    assert captured_payloads[1]["integrations"] == ["mcp/obsidian"]


def test_service_obsidian_tool_mode_passes_integrations_and_prompt_without_changing_user_content() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = TestingSessionLocal()

    class IntegrationCapturingProvider:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def chat_completion(self, model, messages, **kwargs):
            self.calls.append({"model": model, "messages": messages, **kwargs})
            return LLMChatCompletion(model="fake-model:1", content="assistant valasz")

    try:
        provider = IntegrationCapturingProvider()
        settings = _settings(lm_studio_obsidian_integration_id="mcp/my-obsidian")
        chat = assistant_service.create_chat(db)

        result = assistant_service.send_message(
            db,
            chat.id,
            "Csak a user altal irt kerdes",
            tool_mode="obsidian",
            settings=settings,
            provider=provider,
        )

        sent_messages = provider.calls[0]["messages"]
        assert provider.calls[0]["integrations"] == ["mcp/my-obsidian"]
        assert "[Obsidian tool mode]" in sent_messages[0].content
        assert "00-INDEX.md" in sent_messages[0].content
        assert result.messages[0].content == "Csak a user altal irt kerdes"
        assert sent_messages[-1].content == "Csak a user altal irt kerdes"
        assert "[Obsidian tool mode]" not in result.messages[0].content
    finally:
        db.close()
        Base.metadata.drop_all(engine)
