from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ReasoningMode = Literal['normal', 'model_default']
ToolMode = Literal['none', 'obsidian', 'excel', 'graphrag']
MessageRole = Literal['user', 'assistant', 'system']


class AssistantChatCreateRequest(BaseModel):
    reasoning_mode: ReasoningMode = 'normal'
    temperature: float | None = Field(default=None, ge=0, le=2)


class AssistantChatUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class AssistantMessageSendRequest(BaseModel):
    content: str = Field(min_length=1, max_length=120000)
    tool_mode: ToolMode = 'none'
    reasoning_mode: ReasoningMode | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)


class AssistantMessageRegenerateRequest(BaseModel):
    tool_mode: ToolMode = 'none'
    reasoning_mode: ReasoningMode | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)


class AssistantMessageUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=120000)


class GraphRAGSourceResponse(BaseModel):
    source_id: str
    relative_path: str
    heading_path: list[str] = Field(default_factory=list)
    source_uri: str | None = None
    obsidian_uri: str | None = None


class GraphRAGWarningResponse(BaseModel):
    code: str
    message: str


class GraphRAGProvenanceResponse(BaseModel):
    query_id: str
    query_type: str
    planner_reason_code: str
    warnings: list[GraphRAGWarningResponse] = Field(default_factory=list)
    truncated: bool = False
    sources: list[GraphRAGSourceResponse] = Field(default_factory=list)


class AssistantMessageResponse(BaseModel):
    id: int
    role: MessageRole
    content: str
    reasoning_content: str | None = None
    tool_activity_content: str | None = None
    work_narration_content: str | None = None
    generation_duration_ms: int | None = None
    graphrag: GraphRAGProvenanceResponse | None = None
    sequence_index: int
    model: str | None
    reasoning_mode: str | None
    created_at: datetime

    model_config = {'from_attributes': True}


class AssistantChatSummaryResponse(BaseModel):
    id: int
    title: str
    status: str
    reasoning_mode: str
    temperature: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}


class AssistantChatDetailResponse(AssistantChatSummaryResponse):
    messages: list[AssistantMessageResponse]


class AssistantChatListResponse(BaseModel):
    chats: list[AssistantChatSummaryResponse]


class ContextLimitDetail(BaseModel):
    code: str
    message: str
    budget: int
    actual: int
