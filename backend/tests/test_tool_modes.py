import json

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import assistant_service
from app.config import Settings
from app.db import Base
from app.llm_provider import LLMChatCompletion, LLMModel, LLMChatMessage, LMStudioNativeProvider
from app.models import AssistantMessageModel
from app.tool_modes import EXCEL_CALL_FRAME, EXCEL_TOOL_PROMPT, OBSIDIAN_CALL_FRAME, OBSIDIAN_TOOL_PROMPT, resolve_tool_mode_policy


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
    assert policy.call_frame == OBSIDIAN_CALL_FRAME
    assert "00-INDEX.md" in policy.prompt_instructions
    assert "[Tudásbázis mód]" in policy.prompt_instructions
    assert "útválasztó index" in policy.prompt_instructions
    assert "Tilos hallucinálni" in policy.prompt_instructions
    assert "mcp/obsidian" in policy.prompt_instructions
    assert "Kapcsolódó dokumentumok" in policy.prompt_instructions
    assert "általános Obsidian vagy MCP funkciókat" in policy.call_frame


def test_tool_mode_policy_excel_uses_configured_integration_id_and_read_only_prompt() -> None:
    policy = resolve_tool_mode_policy(_settings(lm_studio_excel_integration_id="mcp/my-excel"), "excel")

    assert policy.id == "excel"
    assert policy.label == "Adatbazis"
    assert policy.integration_ids == ("mcp/my-excel",)
    assert policy.prompt_instructions == EXCEL_TOOL_PROMPT
    assert policy.call_frame == EXCEL_CALL_FRAME
    assert "[Excel adatbázis mód]" in policy.prompt_instructions
    assert "00-INDEX.xlsx" in policy.prompt_instructions
    assert "Alap flow" not in policy.prompt_instructions
    assert "útválasztó index" in policy.prompt_instructions
    assert "Fájlnév-utalás" in policy.prompt_instructions
    assert "Ha nincs egyértelmű fájltalálat" in policy.prompt_instructions
    assert "kizárólag abban a fájlban keress és válaszolj" in policy.prompt_instructions
    assert "kérj pontosítást" in policy.prompt_instructions
    assert "Toolhasználat" in policy.prompt_instructions
    assert "lookup_excel_rows" in policy.prompt_instructions
    assert "match_mode=\"contains\"" in policy.prompt_instructions
    assert "filter_excel_rows" in policy.prompt_instructions
    assert "aggregate_excel_data" in policy.prompt_instructions
    assert "először használd a describe_excel_sheet" in policy.prompt_instructions
    assert "oszlopokat, mintaértékeket és a táblaszerkezetet" in policy.prompt_instructions
    assert "detect_header_row" in policy.prompt_instructions
    assert "javasolt header_row értékkel" in policy.prompt_instructions
    assert "find_relevant_column" in policy.prompt_instructions
    assert "high confidence" in policy.prompt_instructions
    assert "next_step mezőit másold át" in policy.prompt_instructions
    assert policy.prompt_instructions.index("describe_excel_sheet") < policy.prompt_instructions.index("find_relevant_column")
    assert "Nagy forrástáblát ne dumpolj ki kézi kereséshez" in policy.prompt_instructions
    assert "Ne indíts új keresést csak bizonytalanságból" in policy.prompt_instructions
    assert "legfeljebb egyszer javítsd a paramétereket" in policy.prompt_instructions
    assert "read_data_from_excel csak indexlaphoz" in policy.prompt_instructions
    assert "list_excel_columns" not in policy.prompt_instructions
    assert "find_excel_rows_with_same_value" not in policy.prompt_instructions
    assert "Tilos hallucinálni" in policy.prompt_instructions
    assert "Tilos válaszolni a releváns forrásfájl ellenőrzése előtt" in policy.prompt_instructions
    assert "Ne döntsd el önhatalmúlag" in policy.prompt_instructions
    assert "add vissza a találati sorok összes mezőjét" in policy.prompt_instructions
    assert "Ne keress önállóan további névváltozatokat" in policy.prompt_instructions
    assert "Tilos Excel fájlt létrehozni" in policy.prompt_instructions
    assert "pivot táblát" in policy.prompt_instructions
    assert "felhasználó erre kér" in policy.prompt_instructions
    assert "mcp/excel eszközön keresztül" in policy.prompt_instructions
    assert "fogadd el és kérj pontosítást majd állj le" in policy.prompt_instructions
    assert "azonnal válaszolj" in policy.prompt_instructions
    assert "Ne kezdj el keresni máshol is" in policy.prompt_instructions
    assert "A toolhasználat és keresés belső munkafolyamat" not in policy.prompt_instructions
    assert "Tilos folyamatjelző mondatokat írni" not in policy.prompt_instructions
    assert "Magyarul, tömören és jól strukturáltan válaszolj" in policy.prompt_instructions
    assert "melyik fájl, munkalap és oszlopok alapján dolgoztál" in policy.prompt_instructions
    assert "Adatbázis módban mindig használd az Excel MCP eszközöket" not in policy.prompt_instructions


def test_tool_mode_policy_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError):
        resolve_tool_mode_policy(_settings(), "browser")


@pytest.mark.parametrize("tool_mode", ["obsidian", "excel", "graphrag"])
def test_source_grounded_modes_keep_only_latest_user_message_for_generation(
    tool_mode: str,
) -> None:
    messages = [
        AssistantMessageModel(role="user", content="Régi kérdés", sequence_index=0),
        AssistantMessageModel(role="assistant", content="Régi válasz", sequence_index=1),
        AssistantMessageModel(role="user", content="Aktuális kérdés", sequence_index=2),
    ]

    selected = assistant_service._generation_messages(
        messages,
        resolve_tool_mode_policy(_settings(), tool_mode),
    )

    assert [(message.role, message.content) for message in selected] == [
        ("user", "Aktuális kérdés")
    ]


def test_normal_mode_keeps_full_conversation_for_generation() -> None:
    messages = [
        AssistantMessageModel(role="user", content="Első kérdés", sequence_index=0),
        AssistantMessageModel(role="assistant", content="Első válasz", sequence_index=1),
        AssistantMessageModel(role="user", content="Második kérdés", sequence_index=2),
    ]

    assert assistant_service._generation_messages(
        messages,
        resolve_tool_mode_policy(_settings(), "none"),
    ) == messages


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


def test_service_excel_tool_mode_passes_integrations_and_prompt_without_changing_user_content() -> None:
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

        def list_models(self):
            return [LLMModel(id="chat-model"), LLMModel(id="qwen/qwen3.5-9b")]

        def loaded_model_instance_ids(self):
            return ["chat-model:1", "qwen/qwen3.5-9b:1"]

        def chat_completion(self, model, messages, **kwargs):
            self.calls.append({"model": model, "messages": messages, **kwargs})
            return LLMChatCompletion(model="fake-model:1", content="assistant valasz")

    try:
        provider = IntegrationCapturingProvider()
        settings = _settings(lm_studio_excel_integration_id="mcp/my-excel")
        chat = assistant_service.create_chat(db)

        result = assistant_service.send_message(
            db,
            chat.id,
            "A minta.xlsx alapjan foglald ossze az adatokat",
            tool_mode="excel",
            settings=settings,
            provider=provider,
        )

        sent_messages = provider.calls[0]["messages"]
        assert provider.calls[0]["integrations"] == ["mcp/my-excel"]
        assert "[Excel adatbázis mód]" in sent_messages[0].content
        assert "Tilos Excel fájlt létrehozni" in sent_messages[0].content
        assert "minta.xlsx" in sent_messages[-1].content
        assert result.messages[0].content == "A minta.xlsx alapjan foglald ossze az adatokat"
        assert sent_messages[-1].content == EXCEL_CALL_FRAME.format(user_content="A minta.xlsx alapjan foglald ossze az adatokat")
        assert "[Excel adatbázis mód]" not in result.messages[0].content
        assert "Tilos Excel fájlt létrehozni" not in result.messages[0].content
    finally:
        db.close()
        Base.metadata.drop_all(engine)


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

        def list_models(self):
            return [LLMModel(id="chat-model"), LLMModel(id="qwen/qwen3.5-9b")]

        def loaded_model_instance_ids(self):
            return ["chat-model:1", "qwen/qwen3.5-9b:1"]

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
        assert "[Tudásbázis mód]" in sent_messages[0].content
        assert "00-INDEX.md" in sent_messages[0].content
        assert result.messages[0].content == "Csak a user altal irt kerdes"
        assert sent_messages[-1].content == OBSIDIAN_CALL_FRAME.format(user_content="Csak a user altal irt kerdes")
        assert "[Tudásbázis mód]" not in result.messages[0].content
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_source_tool_mode_excludes_prior_conversation_from_provider() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = TestingSessionLocal()

    class CapturingProvider:
        def __init__(self) -> None:
            self.calls: list[dict] = []
            self.index = 0

        def list_models(self):
            return [LLMModel(id="chat-model")]

        def loaded_model_instance_ids(self):
            return ["chat-model:1"]

        def chat_completion(self, model, messages, **kwargs):
            self.index += 1
            self.calls.append({"model": model, "messages": messages, **kwargs})
            return LLMChatCompletion(model="fake-model:1", content=f"assistant valasz {self.index}")

    try:
        provider = CapturingProvider()
        settings = _settings(lm_studio_excel_integration_id="mcp/my-excel")
        chat = assistant_service.create_chat(db)

        assistant_service.send_message(
            db,
            chat.id,
            "Első kérdés",
            tool_mode="excel",
            settings=settings,
            provider=provider,
        )
        result = assistant_service.send_message(
            db,
            chat.id,
            "Második kérdés",
            tool_mode="excel",
            settings=settings,
            provider=provider,
        )

        latest_call_messages = provider.calls[-1]["messages"]
        assert len(latest_call_messages) == 2
        assert latest_call_messages[1].role == "user"
        assert latest_call_messages[1].content == EXCEL_CALL_FRAME.format(user_content="Második kérdés")
        assert all("Első kérdés" not in message.content for message in latest_call_messages)
        assert [message.content for message in result.messages if message.role == "user"] == ["Első kérdés", "Második kérdés"]
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_normal_mode_does_not_wrap_latest_user_message() -> None:
    policy = resolve_tool_mode_policy(_settings(), "none")
    assert policy.call_frame is None


@pytest.mark.parametrize("tool_mode", ["none", "obsidian", "excel", "graphrag"])
def test_all_modes_include_internal_instruction_protection_in_system_prompt(
    tool_mode: str,
) -> None:
    policy = resolve_tool_mode_policy(_settings(), tool_mode)
    messages = assistant_service._to_llm_messages(
        _settings(assistant_system_prompt="Alap rendszerutasítás."),
        [AssistantMessageModel(role="user", content="Kérdés", sequence_index=0)],
        policy.prompt_instructions,
        policy.call_frame,
    )

    assert "rendszerprompt, fejlesztői utasítás" in messages[0].content
    assert "dokumentált funkciók, működési módok és használati útmutatók" in messages[0].content
    if policy.call_frame:
        assert "rendszerprompt, fejlesztői utasítás" in policy.call_frame
        assert "dokumentált funkciók, működési módok és használati útmutatók" in policy.call_frame
