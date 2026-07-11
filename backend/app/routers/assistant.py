from collections.abc import Iterator
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import assistant_service as service
from app.config import get_settings
from app.db import get_db
from app.llm_provider import LLMProviderError, LMStudioNativeProvider
from app.schemas import (
    AssistantChatCreateRequest,
    AssistantChatDetailResponse,
    AssistantChatListResponse,
    AssistantChatUpdateRequest,
    AssistantMessageRegenerateRequest,
    AssistantMessageSendRequest,
    AssistantMessageUpdateRequest,
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
            tool_mode=payload.tool_mode,
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


@router.patch('/chats/{chat_id}/messages/{message_id}', response_model=AssistantChatDetailResponse)
def update_unanswered_last_user_message(
    chat_id: int,
    message_id: int,
    payload: AssistantMessageUpdateRequest,
    db: Session = Depends(get_db),
):
    try:
        return service.update_unanswered_last_user_message(db, chat_id, message_id, payload.content)
    except service.AssistantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except service.AssistantContextLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'code': exc.code, 'message': exc.message, 'budget': exc.budget, 'actual': exc.actual},
        ) from exc
    except service.AssistantValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post('/chats/{chat_id}/messages/stream')
def stream_assistant_message(chat_id: int, payload: AssistantMessageSendRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    try:
        prepared = service.prepare_send_message_stream(
            db,
            chat_id,
            payload.content,
            reasoning_mode=payload.reasoning_mode,
            temperature=payload.temperature,
            tool_mode=payload.tool_mode,
            settings=settings,
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

    return _stream_prepared_assistant_response(db, settings, prepared)


@router.post('/chats/{chat_id}/retry-last-user/stream')
def stream_retry_last_user_message(
    chat_id: int,
    payload: AssistantMessageRegenerateRequest,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    try:
        prepared = service.prepare_retry_last_user_message_stream(
            db,
            chat_id,
            reasoning_mode=payload.reasoning_mode,
            temperature=payload.temperature,
            tool_mode=payload.tool_mode,
            settings=settings,
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

    return _stream_prepared_assistant_response(db, settings, prepared)


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
            tool_mode=payload.tool_mode,
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


@router.post('/chats/{chat_id}/regenerate/stream')
def stream_regenerate_assistant_message(
    chat_id: int,
    payload: AssistantMessageRegenerateRequest,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    try:
        prepared = service.prepare_regenerate_message_stream(
            db,
            chat_id,
            reasoning_mode=payload.reasoning_mode,
            temperature=payload.temperature,
            tool_mode=payload.tool_mode,
            settings=settings,
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

    return _stream_prepared_assistant_response(db, settings, prepared)


def _stream_prepared_assistant_response(db: Session, settings, prepared: service.PreparedAssistantStream) -> StreamingResponse:
    provider = LMStudioNativeProvider(settings)

    def event_generator() -> Iterator[str]:
        reasoning_chunks: list[str] = []
        yield _sse_event('start', {'chat_id': prepared.chat_id})
        try:
            for stream_event in provider.chat_completion_stream(
                prepared.model,
                prepared.messages,
                temperature=prepared.temperature,
                max_tokens=settings.lm_studio_default_max_output_tokens,
                reasoning_mode=service._llm_reasoning_mode(prepared.reasoning_mode),
                **({'integrations': prepared.integrations} if prepared.integrations else {}),
            ):
                if stream_event.type == 'message_delta':
                    yield _sse_event('delta', {'content': stream_event.content or ''})
                elif stream_event.type == 'reasoning_delta':
                    reasoning_content = stream_event.content or ''
                    reasoning_chunks.append(reasoning_content)
                    yield _sse_event('reasoning_delta', {'content': reasoning_content})
                elif stream_event.type == 'status':
                    yield _sse_event('status', {'raw': stream_event.raw})
                elif stream_event.type == 'error':
                    yield _sse_event('error', {'message': stream_event.error_message or 'LM Studio streaming error'})
                elif stream_event.type == 'done':
                    final_content = stream_event.final_content or ''
                    if final_content == '':
                        yield _sse_event('error', {'message': 'LM Studio nem adott vissza végleges assistant választ.'})
                        return
                    chat = service.finalize_streamed_assistant_message(
                        db,
                        prepared,
                        content=final_content,
                        model=stream_event.model or prepared.model,
                        reasoning_content=''.join(reasoning_chunks),
                    )
                    yield _sse_event('done', {'chat': _chat_detail_payload(chat)})
                    return
        except LLMProviderError as exc:
            yield _sse_event('error', {'message': str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _chat_detail_payload(chat) -> dict[str, Any]:
    return AssistantChatDetailResponse.model_validate(chat).model_dump(mode='json')
