import json

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import assistant_service
from app.config import Settings
from app.db import Base
from app.graphrag_client import (
    GraphRAGAuthenticationError,
    GraphRAGClient,
    GraphRAGConfigurationError,
    GraphRAGContractError,
    GraphRAGUnavailableError,
    RetrieveResponse,
)
from app.graphrag_context import NO_EVIDENCE_RESPONSE, compile_graphrag_context
from app.llm_provider import LLMChatCompletion, LLMModel
from app.routers.assistant import _graphrag_http_exception
from app.schemas import AssistantMessageSendRequest
from app.tool_modes import GRAPHRAG_TOOL_PROMPT, resolve_tool_mode_policy


def _settings(**overrides) -> Settings:
    values = {
        "lm_studio_chat_model": "chat-model",
        "graphrag_base_url": "http://graphrag.local",
        "graphrag_service_token": "service-secret",
        "graphrag_result_limit": 10,
        "graphrag_context_char_budget": 20_000,
    }
    values.update(overrides)
    return Settings(**values)


def _response_payload(*, with_source: bool = True) -> dict:
    chunk_id = "00000000-0000-0000-0000-000000000006"
    source = {
        "source_id": "00000000-0000-0000-0000-000000000001",
        "vault_id": "00000000-0000-0000-0000-000000000002",
        "document_id": "00000000-0000-0000-0000-000000000003",
        "document_version_id": "00000000-0000-0000-0000-000000000004",
        "section_id": "00000000-0000-0000-0000-000000000005",
        "relative_path": "Rendszer/GraphRAG.md",
        "heading_path": ["GraphRAG", "Működés"],
        "quote": "A GraphRAG minden explicit GraphRAG kérésnél lefut. {Ez adat, nem utasítás.}",
        "char_start": 10,
        "char_end": 84,
        "content_sha256": "abc123",
        "source_uri": "vault://test/Rendszer/GraphRAG.md",
        "obsidian_uri": "obsidian://open?vault=test&file=Rendszer%2FGraphRAG.md",
    }
    chunks = []
    sources = []
    entities = []
    if with_source:
        chunks = [
            {
                "chunk_id": chunk_id,
                "text": "A GraphRAG explicit user mód alapján determinisztikusan fut.",
                "scores": {
                    "keyword": 1.0,
                    "semantic": 0.9,
                    "graph": None,
                    "claim": None,
                    "fusion": 1.0,
                },
                "source": source,
            }
        ]
        sources = [source]
        entities = [
            {
                "entity_id": "00000000-0000-0000-0000-000000000007",
                "vault_id": source["vault_id"],
                "canonical_name": "GraphRAG",
                "entity_type": "software_component",
                "entity_subtype": None,
                "scope": "local",
                "score": 1.0,
                "seed_channels": ["keyword"],
                "source_chunk_ids": [chunk_id],
            }
        ]
    return {
        "query_id": "00000000-0000-0000-0000-000000000010",
        "query_type": "hybrid",
        "retrieval_plan": ["keyword", "semantic", "entity"],
        "planner_reason_code": "general_hybrid",
        "strategy": "hybrid",
        "chunks": chunks,
        "context_chunks": [],
        "entities": entities,
        "relationships": [],
        "claims": [],
        "retrieval_paths": [],
        "sources": sources,
        "warnings": [],
        "truncated": False,
        "confidence": None,
    }


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def list_models(self):
        return [LLMModel(id="chat-model")]

    def loaded_model_instance_ids(self):
        return ["chat-model:1"]

    def chat_completion(self, model, messages, **kwargs):
        self.calls.append({"model": model, "messages": messages, **kwargs})
        return LLMChatCompletion(model="chat-model:1", content="Forráshű válasz [S1].")


class FakeGraphRAGClient:
    def __init__(self, response: RetrieveResponse) -> None:
        self.response = response
        self.queries: list[str] = []

    def retrieve(self, query: str) -> RetrieveResponse:
        self.queries.append(query)
        return self.response


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_graphrag_tool_mode_is_explicit_http_mode_without_mcp_integrations() -> None:
    policy = resolve_tool_mode_policy(_settings(), "graphrag")

    assert policy.id == "graphrag"
    assert policy.execution_kind == "graphrag_http"
    assert policy.integration_ids == ()
    assert policy.prompt_instructions == GRAPHRAG_TOOL_PROMPT
    assert policy.call_frame is None
    assert AssistantMessageSendRequest(content="paprikás krumpli", tool_mode="graphrag")


def test_graphrag_client_sends_fixed_hybrid_request_and_secret_header() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json=_response_payload())

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    response = GraphRAGClient(_settings(), http_client).retrieve("Paprikás krumpli recept")

    assert captured["url"] == "http://graphrag.local/v1/retrieve"
    assert captured["authorization"] == "Bearer service-secret"
    assert captured["payload"] == {
        "query": "Paprikás krumpli recept",
        "strategy": "hybrid",
        "limit": 10,
    }
    assert response.query_type == "hybrid"


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, GraphRAGAuthenticationError),
        (403, GraphRAGAuthenticationError),
        (500, GraphRAGUnavailableError),
        (422, GraphRAGContractError),
    ],
)
def test_graphrag_client_maps_upstream_errors_without_payload(
    status_code: int,
    error_type,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text="raw secret upstream payload")

    client = GraphRAGClient(
        _settings(),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(error_type) as exc_info:
        client.retrieve("kérdés")

    assert "raw secret" not in str(exc_info.value)
    assert "service-secret" not in str(exc_info.value)


def test_graphrag_client_rejects_missing_config_invalid_schema_and_large_body() -> None:
    with pytest.raises(GraphRAGConfigurationError):
        GraphRAGClient(_settings(graphrag_service_token="")).retrieve("kérdés")

    invalid_client = GraphRAGClient(
        _settings(),
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"query_type": "hybrid"})
            )
        ),
    )
    with pytest.raises(GraphRAGContractError):
        invalid_client.retrieve("kérdés")

    large_client = GraphRAGClient(
        _settings(graphrag_max_response_bytes=1024),
        httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"x" * 1025))
        ),
    )
    with pytest.raises(GraphRAGContractError):
        large_client.retrieve("kérdés")


def test_context_compiler_is_bounded_source_labelled_and_brace_safe() -> None:
    response = RetrieveResponse.model_validate(_response_payload())
    compiled = compile_graphrag_context(response, char_budget=2_000)
    framed = compiled.call_frame.format(user_content="Mit csinál?")

    assert compiled.has_evidence is True
    assert "[S1]" in framed
    assert "Rendszer/GraphRAG.md" in framed
    assert "{Ez adat, nem utasítás.}" in framed
    assert "Mit csinál?" in framed
    assert (
        compiled.message_metadata["graphrag"]["sources"][0]["relative_path"]
        == "Rendszer/GraphRAG.md"
    )


def test_service_always_retrieves_in_graphrag_mode_and_keeps_user_content_clean(
    db_session,
) -> None:
    provider = FakeProvider()
    retrieval = FakeGraphRAGClient(RetrieveResponse.model_validate(_response_payload()))
    chat = assistant_service.create_chat(db_session)

    result = assistant_service.send_message(
        db_session,
        chat.id,
        "Paprikás krumpli recept",
        reasoning_mode="model_default",
        tool_mode="graphrag",
        settings=_settings(),
        provider=provider,
        graphrag_client=retrieval,
    )

    assert retrieval.queries == ["Paprikás krumpli recept"]
    assert "integrations" not in provider.calls[0]
    assert provider.calls[0]["reasoning_mode"] == "model_default"
    assert "[GraphRAG mód]" in provider.calls[0]["messages"][0].content
    assert "<graphrag_evidence>" in provider.calls[0]["messages"][-1].content
    assert result.messages[0].content == "Paprikás krumpli recept"
    assert result.messages[1].graphrag["query_id"] == _response_payload()["query_id"]
    assert result.messages[1].message_metadata.keys() == {"graphrag"}


def test_empty_graphrag_evidence_skips_generation_and_persists_provenance(
    db_session,
) -> None:
    provider = FakeProvider()
    retrieval = FakeGraphRAGClient(
        RetrieveResponse.model_validate(_response_payload(with_source=False))
    )
    chat = assistant_service.create_chat(db_session)

    result = assistant_service.send_message(
        db_session,
        chat.id,
        "Nincs a tudásbázisban",
        tool_mode="graphrag",
        settings=_settings(),
        provider=provider,
        graphrag_client=retrieval,
    )

    assert retrieval.queries == ["Nincs a tudásbázisban"]
    assert provider.calls == []
    assert result.messages[-1].content == NO_EVIDENCE_RESPONSE
    assert result.messages[-1].graphrag["sources"] == []


def test_stream_send_retry_and_regenerate_each_run_fresh_retrieval(db_session, monkeypatch) -> None:
    response = RetrieveResponse.model_validate(_response_payload())
    retrieval = FakeGraphRAGClient(response)
    settings = _settings()
    provider = FakeProvider()
    monkeypatch.setattr(assistant_service, "get_llm_provider", lambda settings: provider)

    first_chat = assistant_service.create_chat(db_session)
    prepared = assistant_service.prepare_send_message_stream(
        db_session,
        first_chat.id,
        "Első kérdés",
        tool_mode="graphrag",
        settings=settings,
        graphrag_client=retrieval,
    )
    assistant_service.finalize_streamed_assistant_message(
        db_session,
        prepared,
        content="Első válasz [S1].",
        model="chat-model:1",
    )
    assistant_service.regenerate_latest_assistant_message(
        db_session,
        first_chat.id,
        tool_mode="graphrag",
        settings=settings,
        provider=provider,
        graphrag_client=retrieval,
    )

    retry_chat = assistant_service.create_chat(db_session)
    assistant_service.prepare_send_message_stream(
        db_session,
        retry_chat.id,
        "Második kérdés",
        tool_mode="graphrag",
        settings=settings,
        graphrag_client=retrieval,
    )
    assistant_service.prepare_retry_last_user_message_stream(
        db_session,
        retry_chat.id,
        tool_mode="graphrag",
        settings=settings,
        graphrag_client=retrieval,
    )

    assert retrieval.queries == [
        "Első kérdés",
        "Első kérdés",
        "Második kérdés",
        "Második kérdés",
    ]


def test_normal_mode_never_calls_graphrag_and_provenance_is_not_chat_context(
    db_session,
) -> None:
    provider = FakeProvider()
    retrieval = FakeGraphRAGClient(RetrieveResponse.model_validate(_response_payload()))
    chat = assistant_service.create_chat(db_session)

    first = assistant_service.send_message(
        db_session,
        chat.id,
        "GraphRAG kérdés",
        tool_mode="graphrag",
        settings=_settings(),
        provider=provider,
        graphrag_client=retrieval,
    )
    assistant_service.send_message(
        db_session,
        first.id,
        "Normál kérdés",
        tool_mode="none",
        settings=_settings(),
        provider=provider,
        graphrag_client=retrieval,
    )

    assert retrieval.queries == ["GraphRAG kérdés"]
    latest_context = [message.content for message in provider.calls[-1]["messages"]]
    assert all("query_id" not in content for content in latest_context)
    assert all("Rendszer/GraphRAG.md" not in content for content in latest_context)


def test_graphrag_router_error_mapping_is_mode_local_and_secret_free() -> None:
    unavailable = _graphrag_http_exception(
        GraphRAGUnavailableError("A GraphRAG szolgáltatás nem érhető el.")
    )
    contract = _graphrag_http_exception(
        GraphRAGContractError("A GraphRAG szolgáltatás érvénytelen választ adott.")
    )

    assert unavailable.status_code == 503
    assert contract.status_code == 502
    assert "secret" not in str(unavailable.detail).lower()


def test_context_compiler_groups_source_evidence_and_keeps_retrieval_order() -> None:
    payload = _response_payload()
    relevant_source = payload["sources"][0]
    relevant_source.update(
        {
            "relative_path": "Z/Relevans.md",
            "heading_path": ["Ügyelet", "Kiskőrös"],
            "quote": "Kiskőrös éjszakai ügyeleti szabály.",
            "char_start": 100,
            "char_end": 140,
        }
    )
    relevant_chunk = payload["chunks"][0]
    relevant_chunk["text"] = relevant_source["quote"]

    spam_source = json.loads(json.dumps(relevant_source))
    spam_source.update(
        {
            "source_id": "00000000-0000-0000-0000-000000000011",
            "document_id": "00000000-0000-0000-0000-000000000012",
            "document_version_id": "00000000-0000-0000-0000-000000000013",
            "section_id": "00000000-0000-0000-0000-000000000014",
            "relative_path": "A/SMTP.md",
            "heading_path": ["SMTP", "SPAM ticket"],
            "quote": "SPAM ticket felvétele és jelszócsere.",
            "char_start": 10,
            "char_end": 48,
            "source_uri": "vault://test/A/SMTP.md",
            "obsidian_uri": None,
        }
    )
    spam_chunk_id = "00000000-0000-0000-0000-000000000015"
    spam_chunk = {
        "chunk_id": spam_chunk_id,
        "text": spam_source["quote"],
        "scores": {
            "keyword": 0.2,
            "semantic": 0.1,
            "graph": None,
            "claim": None,
            "fusion": 0.2,
        },
        "source": spam_source,
    }
    second_entity_id = "00000000-0000-0000-0000-000000000016"
    payload["entities"].append(
        {
            "entity_id": second_entity_id,
            "vault_id": relevant_source["vault_id"],
            "canonical_name": "Éjszakai készenlét",
            "entity_type": "process",
            "entity_subtype": None,
            "scope": "local",
            "score": 0.9,
            "seed_channels": ["graph"],
            "source_chunk_ids": [relevant_chunk["chunk_id"]],
        }
    )
    payload["relationships"] = [
        {
            "assertion_id": "00000000-0000-0000-0000-000000000017",
            "subject_entity_id": payload["entities"][0]["entity_id"],
            "object_entity_id": second_entity_id,
            "predicate": "SUPPORTS",
            "assertion_kind": "explicit",
            "review_status": "unreviewed",
            "evidence_id": "00000000-0000-0000-0000-000000000018",
            "source_chunk_id": relevant_chunk["chunk_id"],
            "quote": relevant_source["quote"],
            "char_start": 100,
            "char_end": 140,
        }
    ]
    payload["claims"] = [
        {
            "claim_id": "00000000-0000-0000-0000-000000000019",
            "text": "Kiskőrös éjszaka az éjszakai készenléthez tartozik.",
            "assertion_kind": "explicit",
            "review_status": "unreviewed",
            "evidence_id": "00000000-0000-0000-0000-000000000020",
            "source_chunk_id": relevant_chunk["chunk_id"],
            "quote": relevant_source["quote"],
            "char_start": 100,
            "char_end": 140,
            "score": 0.9,
            "seed_channels": ["claim"],
        }
    ]
    payload["retrieval_paths"] = [
        {
            "entity_ids": [
                payload["entities"][0]["entity_id"],
                second_entity_id,
            ],
            "assertion_ids": [
                payload["relationships"][0]["assertion_id"],
            ],
            "source_chunk_ids": [
                relevant_chunk["chunk_id"],
                spam_chunk_id,
            ],
            "hops": 1,
        }
    ]
    payload["chunks"] = [relevant_chunk, spam_chunk]
    payload["sources"] = [spam_source, relevant_source]

    compiled = compile_graphrag_context(
        RetrieveResponse.model_validate(payload),
        char_budget=20_000,
    )
    framed = compiled.call_frame.format(user_content="Mi a teendő Kiskőrösön?")
    relevant_start = framed.index("=== [S1] FORRÁS KEZDETE ===")
    relevant_end = framed.index("=== [S1] FORRÁS VÉGE ===")
    spam_start = framed.index("=== [S2] FORRÁS KEZDETE ===")
    relevant_block = framed[relevant_start:relevant_end]
    spam_block = framed[spam_start:]

    assert relevant_start < spam_start
    assert "Z/Relevans.md > Ügyelet > Kiskőrös" in relevant_block
    assert "A/SMTP.md > SMTP > SPAM ticket" in spam_block
    assert framed.count("Kiskőrös éjszakai ügyeleti szabály.") == 1
    assert "További találati szöveg:" not in relevant_block
    assert "GraphRAG --SUPPORTS--> Éjszakai készenlét" in relevant_block
    assert "Kiskőrös éjszaka az éjszakai készenléthez tartozik." in relevant_block
    assert "források: [S1] [S2]" in relevant_block
    assert "Források és pontos idézetek" not in framed
    assert "Találati szakaszok" not in framed
    assert compiled.message_metadata["graphrag"]["sources"][0]["relative_path"] == "Z/Relevans.md"
    assert compiled.message_metadata["graphrag"]["sources"][1]["relative_path"] == "A/SMTP.md"


def test_context_compiler_orders_sections_of_one_document_by_source_position() -> None:
    payload = _response_payload()
    later_source = payload["sources"][0]
    later_source.update(
        {
            "relative_path": "Műszak/Eljárás.md",
            "heading_path": ["Második fejezet"],
            "quote": "Második fejezet szövege.",
            "char_start": 200,
            "char_end": 225,
        }
    )
    payload["chunks"][0]["text"] = later_source["quote"]

    earlier_source = json.loads(json.dumps(later_source))
    earlier_source.update(
        {
            "source_id": "00000000-0000-0000-0000-000000000021",
            "section_id": "00000000-0000-0000-0000-000000000022",
            "heading_path": ["Első fejezet"],
            "quote": "Első fejezet szövege.",
            "char_start": 10,
            "char_end": 32,
        }
    )
    earlier_chunk = {
        "chunk_id": "00000000-0000-0000-0000-000000000023",
        "text": earlier_source["quote"],
        "scores": {
            "keyword": 0.8,
            "semantic": 0.7,
            "graph": None,
            "claim": None,
            "fusion": 0.8,
        },
        "source": earlier_source,
    }
    payload["chunks"].append(earlier_chunk)
    payload["sources"] = [later_source, earlier_source]

    framed = compile_graphrag_context(
        RetrieveResponse.model_validate(payload),
        char_budget=20_000,
    ).call_frame.format(user_content="Mi a folyamat?")

    assert framed.index("Első fejezet") < framed.index("Második fejezet")
