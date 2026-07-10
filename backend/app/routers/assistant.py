from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import assistant_service as service
from app.config import get_settings
from app.db import get_db
from app.llm_provider import LLMProviderError
from app.schemas import (
    AssistantChatCreateRequest,
    AssistantChatDetailResponse,
    AssistantChatListResponse,
    AssistantChatUpdateRequest,
    AssistantMessageRegenerateRequest,
    AssistantMessageSendRequest,
)

router = APIRouter(prefix='/assistant', tags=['assistant'])


@router.get('/status')
def assistant_status() -> dict[str, str | int]:
    settings = get_settings()
    return {'status': 'ready', 'context_char_budget': settings.assistant_context_char_budget}


@router.get('/chats', response_model=AssistantChatListResponse)
def list_assistant_chats(db: Session = Depends(get_db)) -> dict:
    return {'chats': service.list_chats(db)}


@router.post('/chats', response_model=AssistantChatDetailResponse, status_code=status.HTTP_201_CREATED)
def create_assistant_chat(payload: AssistantChatCreateRequest, db: Session = Depends(get_db)):
    return service.create_chat(db, reasoning_mode=payload.reasoning_mode, temperature=payload.temperature)


@router.get('/chats/{chat_id}', response_model=AssistantChatDetailResponse)
def get_assistant_chat(chat_id: int, db: Session = Depends(get_db)):
    try:
        return service.get_chat(db, chat_id)
    except service.AssistantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch('/chats/{chat_id}', response_model=AssistantChatDetailResponse)
def rename_assistant_chat(chat_id: int, payload: AssistantChatUpdateRequest, db: Session = Depends(get_db)):
    try:
        return service.rename_chat(db, chat_id, payload.title)
    except service.AssistantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except service.AssistantValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete('/chats/{chat_id}')
def delete_assistant_chat(chat_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        service.soft_delete_chat(db, chat_id)
    except service.AssistantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {'status': 'deleted'}


@router.post('/chats/{chat_id}/messages', response_model=AssistantChatDetailResponse)
def send_assistant_message(chat_id: int, payload: AssistantMessageSendRequest, db: Session = Depends(get_db)):
    try:
        return service.send_message(
            db,
            chat_id,
            payload.content,
            reasoning_mode=payload.reasoning_mode,
            temperature=payload.temperature,
        )
    except service.AssistantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except service.AssistantContextLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'code': exc.code, 'message': exc.message, 'budget': exc.budget, 'actual': exc.actual},
        ) from exc
    except service.AssistantValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post('/chats/{chat_id}/regenerate', response_model=AssistantChatDetailResponse)
def regenerate_assistant_message(
    chat_id: int,
    payload: AssistantMessageRegenerateRequest,
    db: Session = Depends(get_db),
):
    try:
        return service.regenerate_latest_assistant_message(
            db,
            chat_id,
            reasoning_mode=payload.reasoning_mode,
            temperature=payload.temperature,
        )
    except service.AssistantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except service.AssistantContextLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'code': exc.code, 'message': exc.message, 'budget': exc.budget, 'actual': exc.actual},
        ) from exc
    except service.AssistantValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
