from __future__ import annotations

import json
from typing import Literal
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.config import Settings


class GraphRAGResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RetrievalScores(GraphRAGResponseModel):
    keyword: float | None
    semantic: float | None
    graph: float | None
    claim: float | None
    fusion: float | None


class RetrievalSource(GraphRAGResponseModel):
    source_id: UUID
    vault_id: UUID
    document_id: UUID
    document_version_id: UUID
    section_id: UUID
    chunk_id: UUID | None = None
    relative_path: str
    heading_path: list[str]
    quote: str
    char_start: int
    char_end: int
    content_sha256: str
    source_uri: str
    obsidian_uri: str | None


class RetrievalChunk(GraphRAGResponseModel):
    chunk_id: UUID
    text: str
    scores: RetrievalScores
    source: RetrievalSource


class RetrievalEntity(GraphRAGResponseModel):
    entity_id: UUID
    vault_id: UUID
    canonical_name: str
    entity_type: str
    entity_subtype: str | None
    scope: str
    score: float
    seed_channels: list[str]
    source_chunk_ids: list[UUID]


class RetrievalRelationship(GraphRAGResponseModel):
    assertion_id: UUID
    subject_entity_id: UUID
    object_entity_id: UUID
    predicate: str
    assertion_kind: str
    review_status: str
    evidence_id: UUID
    source_chunk_id: UUID
    quote: str
    char_start: int
    char_end: int


class RetrievalClaim(GraphRAGResponseModel):
    claim_id: UUID
    text: str
    assertion_kind: str
    review_status: str
    evidence_id: UUID
    source_chunk_id: UUID
    quote: str
    char_start: int
    char_end: int
    score: float
    seed_channels: list[str]


class RetrievalPath(GraphRAGResponseModel):
    entity_ids: list[UUID]
    assertion_ids: list[UUID]
    source_chunk_ids: list[UUID]
    hops: int


class RetrievalWarning(GraphRAGResponseModel):
    code: str
    message: str


class RetrieveResponse(GraphRAGResponseModel):
    query_id: UUID
    query_type: Literal["keyword", "semantic", "hybrid", "entity", "graph"]
    retrieval_plan: list[str]
    planner_reason_code: str
    strategy: Literal["keyword", "semantic", "hybrid"]
    chunks: list[RetrievalChunk]
    context_chunks: list[RetrievalChunk]
    entities: list[RetrievalEntity]
    relationships: list[RetrievalRelationship]
    claims: list[RetrievalClaim]
    retrieval_paths: list[RetrievalPath]
    sources: list[RetrievalSource]
    warnings: list[RetrievalWarning]
    truncated: bool
    confidence: None = None


class GraphRAGError(RuntimeError):
    pass


class GraphRAGConfigurationError(GraphRAGError):
    pass


class GraphRAGUnavailableError(GraphRAGError):
    pass


class GraphRAGAuthenticationError(GraphRAGError):
    pass


class GraphRAGContractError(GraphRAGError):
    pass


class GraphRAGClient:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.Client()

    def retrieve(self, query: str) -> RetrieveResponse:
        base_url = (self._settings.graphrag_base_url or "").strip().rstrip("/")
        token = self._settings.graphrag_service_token
        if base_url == "" or token is None or token.get_secret_value().strip() == "":
            raise GraphRAGConfigurationError("A GraphRAG mód nincs konfigurálva.")

        payload: dict[str, str | int] = {
            "query": query,
            "strategy": "hybrid",
            "limit": self._settings.graphrag_result_limit,
        }
        if self._settings.graphrag_vault_id:
            payload["vault_id"] = self._settings.graphrag_vault_id

        headers = {"Authorization": f"Bearer {token.get_secret_value()}"}
        try:
            with self._client.stream(
                "POST",
                f"{base_url}/v1/retrieve",
                json=payload,
                headers=headers,
                timeout=self._settings.graphrag_request_timeout_seconds,
            ) as response:
                self._raise_for_status(response)
                body = self._read_limited_body(response)
        except httpx.TimeoutException as exc:
            raise GraphRAGUnavailableError("A GraphRAG szolgáltatás nem érhető el.") from exc
        except httpx.RequestError as exc:
            raise GraphRAGUnavailableError("A GraphRAG szolgáltatás nem érhető el.") from exc

        try:
            return RetrieveResponse.model_validate_json(body)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            raise GraphRAGContractError(
                "A GraphRAG szolgáltatás érvénytelen választ adott."
            ) from exc

    def _read_limited_body(self, response: httpx.Response) -> bytes:
        maximum = self._settings.graphrag_max_response_bytes
        content_length = response.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > maximum:
                    raise GraphRAGContractError(
                        "A GraphRAG szolgáltatás válasza meghaladta a méretkorlátot."
                    )
            except ValueError:
                pass

        body = bytearray()
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if len(body) > maximum:
                raise GraphRAGContractError(
                    "A GraphRAG szolgáltatás válasza meghaladta a méretkorlátot."
                )
        return bytes(body)

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code in {401, 403}:
            raise GraphRAGAuthenticationError("A GraphRAG szolgáltatás hitelesítése sikertelen.")
        if response.status_code >= 500:
            raise GraphRAGUnavailableError("A GraphRAG szolgáltatás nem érhető el.")
        if response.status_code >= 400:
            raise GraphRAGContractError("A GraphRAG szolgáltatás elutasította a retrieval kérést.")


def get_graphrag_client(settings: Settings) -> GraphRAGClient:
    return GraphRAGClient(settings)
