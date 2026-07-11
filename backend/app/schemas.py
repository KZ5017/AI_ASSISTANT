from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ReasoningMode = Literal['normal', 'model_default']
MessageRole = Literal['user', 'assistant', 'system']


class AssistantChatCreateRequest(BaseModel):
    reasoning_mode: ReasoningMode = 'normal'
    temperature: float | None = Field(default=None, ge=0, le=2)


class AssistantChatUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class AssistantMessageSendRequest(BaseModel):
    content: str = Field(min_length=1, max_length=120000)
    reasoning_mode: ReasoningMode | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)


class AssistantMessageRegenerateRequest(BaseModel):
    reasoning_mode: ReasoningMode | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)


class AssistantMessageUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=120000)


class AssistantMessageResponse(BaseModel):
    id: int
    role: MessageRole
    content: str
    reasoning_content: str | None = None
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
