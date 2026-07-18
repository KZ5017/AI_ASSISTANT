from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.config import get_settings
from app.llm_provider import (
    LLMChatMessage,
    LLMProviderError,
    get_llm_provider,
)

router = APIRouter(prefix="/lm-studio", tags=["lm-studio"])

MODEL_LIFECYCLE_DISABLED_MESSAGE = "A modell betöltését, leválasztását és kiválasztását az LM Studio kezeli."


class ChatMessageRequest(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ChatCompletionRequest(BaseModel):
    messages: list[ChatMessageRequest] = Field(min_length=1)
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    reasoning_mode: Literal["off", "model_default"] | None = "off"


class ChatModelRequest(BaseModel):
    model_id: str = Field(min_length=1)


class ChatModelLoadRequest(BaseModel):
    model_id: str | None = Field(default=None, min_length=1)


class ChatModelUnloadRequest(BaseModel):
    model_id: str | None = Field(default=None, min_length=1)
    instance_id: str | None = Field(default=None, min_length=1)


@router.get("/health")
def lm_studio_health() -> dict:
    settings = get_settings()
    result = get_llm_provider(settings).smoke_check(settings.lm_studio_chat_model)
    return {
        "provider": result.provider,
        "base_url": result.base_url,
        "reachable": result.reachable,
        "model_ids": result.model_ids,
        "configured_chat_model": result.configured_chat_model,
        "selected_chat_model": result.selected_chat_model,
        "configured_chat_model_available": result.configured_chat_model_available,
        "configured_chat_model_loaded": result.configured_chat_model_loaded,
        "selected_chat_model_available": result.selected_chat_model_available,
        "selected_chat_model_loaded": result.selected_chat_model_loaded,
        "loaded_model_ids": result.loaded_model_ids,
        "error_message": result.error_message,
    }


@router.get("/models")
def list_lm_studio_models() -> dict:
    settings = get_settings()
    try:
        provider = get_llm_provider(settings)
        return {
            "models": [model.id for model in provider.list_models()],
            "loaded_model_ids": provider.loaded_model_instance_ids(),
            "configured_chat_model": settings.lm_studio_chat_model,
            "selected_chat_model": settings.lm_studio_chat_model,
        }
    except LLMProviderError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/select-chat-model")
def select_lm_studio_chat_model(payload: ChatModelRequest) -> dict:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=MODEL_LIFECYCLE_DISABLED_MESSAGE)


@router.post("/load-chat-model")
def load_lm_studio_chat_model(payload: ChatModelLoadRequest | None = None) -> dict:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=MODEL_LIFECYCLE_DISABLED_MESSAGE)


@router.post("/unload-chat-model")
def unload_lm_studio_chat_model(payload: ChatModelUnloadRequest | None = None) -> dict:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=MODEL_LIFECYCLE_DISABLED_MESSAGE)


@router.post("/chat")
def lm_studio_chat(payload: ChatCompletionRequest) -> dict:
    settings = get_settings()
    model_id = payload.model or settings.lm_studio_chat_model
    try:
        completion = get_llm_provider(settings).chat_completion(
            model_id,
            [LLMChatMessage(role=message.role, content=message.content) for message in payload.messages],
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            reasoning_mode=payload.reasoning_mode,
        )
    except LLMProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return {"model": completion.model, "content": completion.content}
