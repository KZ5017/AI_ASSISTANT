from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.config import get_settings
from app.llm_provider import (
    LLMChatMessage,
    LLMModelAlreadyLoadedError,
    LLMProviderError,
    get_llm_provider,
)
from app.model_runtime import get_selected_chat_model, set_selected_chat_model

router = APIRouter(prefix="/lm-studio", tags=["lm-studio"])


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
    result = get_llm_provider(settings).smoke_check(get_selected_chat_model(settings))
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
            "selected_chat_model": get_selected_chat_model(settings),
        }
    except LLMProviderError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/select-chat-model")
def select_lm_studio_chat_model(payload: ChatModelRequest) -> dict:
    settings = get_settings()
    selected_model = set_selected_chat_model(payload.model_id)
    result = get_llm_provider(settings).smoke_check(selected_model)
    return {
        "selected_chat_model": selected_model,
        "selected_chat_model_available": result.selected_chat_model_available,
        "selected_chat_model_loaded": result.selected_chat_model_loaded,
        "loaded_model_ids": result.loaded_model_ids,
    }


@router.post("/load-chat-model")
def load_lm_studio_chat_model(payload: ChatModelLoadRequest | None = None) -> dict:
    settings = get_settings()
    model_id = payload.model_id if payload and payload.model_id else get_selected_chat_model(settings)
    set_selected_chat_model(model_id)
    try:
        result = get_llm_provider(settings).load_chat_model(model_id)
    except LLMModelAlreadyLoadedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {
        "type": result.type,
        "instance_id": result.instance_id,
        "load_time_seconds": result.load_time_seconds,
        "status": result.status,
        "load_config": result.load_config,
        "selected_chat_model": model_id,
    }


@router.post("/unload-chat-model")
def unload_lm_studio_chat_model(payload: ChatModelUnloadRequest | None = None) -> dict:
    settings = get_settings()
    provider = get_llm_provider(settings)
    try:
        if payload and payload.instance_id:
            result = provider.unload_model_instance(payload.instance_id)
        else:
            model_id = payload.model_id if payload and payload.model_id else get_selected_chat_model(settings)
            result = provider.unload_chat_model(model_id)
    except LLMProviderError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"instance_id": result.instance_id}


@router.post("/chat")
def lm_studio_chat(payload: ChatCompletionRequest) -> dict:
    settings = get_settings()
    model_id = payload.model or get_selected_chat_model(settings)
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
