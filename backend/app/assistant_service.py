from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
import re
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings, get_settings
from app.graphrag_client import GraphRAGClient, get_graphrag_client
from app.graphrag_context import (
    NO_EVIDENCE_RESPONSE,
    PreparedGraphRAGContext,
    compile_graphrag_context,
)
from app.llm_provider import (
    LLMChatCompletion,
    LLMChatMessage,
    LLMProvider,
    get_llm_provider,
    get_llm_provider_for_tool_mode,
)
from app.models import AssistantChatModel, AssistantMessageModel
from app.sensitive_guard import (
    SENSITIVE_OUTPUT_BLOCK_CODE,
    SENSITIVE_OUTPUT_BLOCK_MESSAGE,
    SENSITIVE_REQUEST_BLOCK_CODE,
    SENSITIVE_REQUEST_BLOCK_MESSAGE,
    SensitiveOutputBlocked,
    SensitiveOutputGuard,
    SensitiveRequestGuard,
    SensitiveValueRegistry,
)
from app.tool_modes import (
    EXCEL_CALL_FRAME,
    EXCEL_TOOL_PROMPT,
    GRAPHRAG_TOOL_PROMPT,
    INTERNAL_INSTRUCTION_PROTECTION_RULE,
    OBSIDIAN_CALL_FRAME,
    OBSIDIAN_TOOL_PROMPT,
    ToolModePolicy,
    resolve_tool_mode_policy,
    tool_mode_supports_reasoning,
)

logger = logging.getLogger(__name__)

DEFAULT_CHAT_TITLE = "Új beszélgetés"
CONTEXT_LIMIT_CODE = "context_limit_exceeded"
MAX_REASONING_SAVE_CHARS = 100_000
REASONING_TRUNCATED_SUFFIX = "\n\n[... A gondolatmenet roviditve lett.]"
MAX_TOOL_ACTIVITY_SAVE_CHARS = 100_000
TOOL_ACTIVITY_TRUNCATED_SUFFIX = "\n\n[... Az eszkozhasznalat roviditve lett.]"
MAX_WORK_NARRATION_SAVE_CHARS = 100_000
WORK_NARRATION_TRUNCATED_SUFFIX = "\n\n[... A munkalepesek roviditve lettek.]"


@dataclass(frozen=True)
class PreparedAssistantStream:
    chat_id: int
    model: str
    messages: list[LLMChatMessage]
    assistant_sequence_index: int
    reasoning_mode: str
    temperature: float | None
    integrations: list[str]
    tool_mode: str
    message_metadata: dict = field(default_factory=dict)
    direct_final_content: str | None = None
    started_at: float = 0.0
    replace_message_id: int | None = None


class AssistantError(RuntimeError):
    pass


class AssistantNotFoundError(AssistantError):
    pass


class AssistantValidationError(AssistantError):
    pass


class AssistantModelNotLoadedError(AssistantError):
    pass


class AssistantSensitiveRequestError(AssistantError):
    def __init__(self, category: str) -> None:
        super().__init__(SENSITIVE_REQUEST_BLOCK_MESSAGE)
        self.code = SENSITIVE_REQUEST_BLOCK_CODE
        self.message = SENSITIVE_REQUEST_BLOCK_MESSAGE
        self.category = category


class AssistantSensitiveOutputError(AssistantError):
    def __init__(self, category: str) -> None:
        super().__init__(SENSITIVE_OUTPUT_BLOCK_MESSAGE)
        self.code = SENSITIVE_OUTPUT_BLOCK_CODE
        self.message = SENSITIVE_OUTPUT_BLOCK_MESSAGE
        self.category = category


class AssistantContextLimitError(AssistantError):
    def __init__(self, message: str, *, budget: int, actual: int) -> None:
        super().__init__(message)
        self.code = CONTEXT_LIMIT_CODE
        self.message = message
        self.budget = budget
        self.actual = actual


def create_chat(
    db: Session,
    *,
    reasoning_mode: str = "normal",
    temperature: float | None = None,
) -> AssistantChatModel:
    chat = AssistantChatModel(
        title=DEFAULT_CHAT_TITLE,
        status="active",
        reasoning_mode=reasoning_mode,
        temperature=temperature,
        chat_metadata={},
    )
    db.add(chat)
    db.commit()
    return _get_active_chat(db, chat.id)


def list_chats(db: Session) -> list[AssistantChatModel]:
    return list(
        db.scalars(
            select(AssistantChatModel)
            .where(AssistantChatModel.status == "active")
            .order_by(AssistantChatModel.updated_at.desc(), AssistantChatModel.id.desc())
        )
    )


def get_chat(db: Session, chat_id: int) -> AssistantChatModel:
    return _get_active_chat(db, chat_id)


def rename_chat(db: Session, chat_id: int, title: str) -> AssistantChatModel:
    chat = _get_active_chat(db, chat_id)
    compact_title = _compact_whitespace(title)[:120]
    if compact_title == "":
        raise AssistantValidationError("A cím nem lehet üres.")
    chat.title = compact_title
    chat.updated_at = _now()
    db.commit()
    return _get_active_chat(db, chat.id)


def delete_chat(db: Session, chat_id: int, *, mode: str = "hard") -> None:
    if mode == "soft":
        soft_delete_chat(db, chat_id)
        return
    if mode == "hard":
        hard_delete_chat(db, chat_id)
        return
    raise AssistantValidationError("Ismeretlen beszélgetés törlési mód.")


def hard_delete_chat(db: Session, chat_id: int) -> None:
    chat = _get_active_chat(db, chat_id)
    db.delete(chat)
    db.commit()


def soft_delete_chat(db: Session, chat_id: int) -> None:
    chat = _get_active_chat(db, chat_id)
    chat.status = "deleted"
    chat.deleted_at = _now()
    chat.updated_at = _now()
    db.commit()


def send_message(
    db: Session,
    chat_id: int,
    content: str,
    *,
    reasoning_mode: str | None = None,
    temperature: float | None = None,
    tool_mode: str | None = None,
    settings: Settings | None = None,
    provider: LLMProvider | None = None,
    graphrag_client: GraphRAGClient | None = None,
) -> AssistantChatModel:
    settings = settings or get_settings()
    chat = _get_active_chat(db, chat_id)
    user_content = content.strip()
    if user_content == "":
        raise AssistantValidationError("Az üzenet nem lehet üres.")

    effective_temperature = temperature if temperature is not None else chat.temperature
    tool_policy = _resolve_tool_mode_policy(settings, tool_mode)
    effective_reasoning = _resolve_effective_reasoning_mode(
        reasoning_mode, chat.reasoning_mode, tool_policy
    )
    _enforce_sensitive_request(
        settings,
        user_content,
        chat_id=chat.id,
        tool_mode=tool_policy.id,
        route="send_non_stream",
    )
    next_sequence = _next_sequence_index(chat)
    pending_messages = [*chat.messages, _pending_message("user", user_content, next_sequence)]
    _ensure_context_budget(settings, _generation_messages(pending_messages, tool_policy))
    chat_model = _resolve_configured_chat_model(settings, provider)
    graphrag_context = _prepare_graphrag_context(
        settings,
        tool_policy,
        user_content,
        graphrag_client,
    )

    user_message = AssistantMessageModel(
        chat_id=chat.id,
        role="user",
        content=user_content,
        sequence_index=next_sequence,
        reasoning_mode=effective_reasoning,
        message_metadata={},
    )
    db.add(user_message)
    if len(chat.messages) == 0 and chat.title == DEFAULT_CHAT_TITLE:
        chat.title = _title_from_content(user_content)
    chat.reasoning_mode = effective_reasoning
    chat.temperature = effective_temperature
    chat.updated_at = _now()
    db.flush()

    if graphrag_context is not None and not graphrag_context.has_evidence:
        completion = LLMChatCompletion(
            model=chat_model,
            content=NO_EVIDENCE_RESPONSE,
            generation_duration_ms=0,
        )
    else:
        completion = _complete_chat(
            settings,
            provider,
            [*chat.messages, user_message],
            reasoning_mode=effective_reasoning,
            temperature=effective_temperature,
            tool_policy=tool_policy,
            graphrag_context=graphrag_context,
        )
    try:
        _ensure_sensitive_output(
            settings,
            (completion.content, completion.work_narration_content),
            chat_id=chat.id,
            tool_mode=tool_policy.id,
            route="send_non_stream",
        )
    except AssistantSensitiveOutputError:
        db.commit()
        raise
    db.add(
        AssistantMessageModel(
            chat_id=chat.id,
            role="assistant",
            content=completion.content,
            work_narration_content=_normalize_work_narration_content(
                completion.work_narration_content
            ),
            generation_duration_ms=completion.generation_duration_ms,
            sequence_index=next_sequence + 1,
            model=completion.model,
            reasoning_mode=effective_reasoning,
            message_metadata=_graphrag_message_metadata(graphrag_context),
        )
    )
    chat.updated_at = _now()
    db.commit()
    return _get_active_chat(db, chat.id)


def prepare_send_message_stream(
    db: Session,
    chat_id: int,
    content: str,
    *,
    reasoning_mode: str | None = None,
    temperature: float | None = None,
    tool_mode: str | None = None,
    settings: Settings | None = None,
    graphrag_client: GraphRAGClient | None = None,
) -> PreparedAssistantStream:
    settings = settings or get_settings()
    chat = _get_active_chat(db, chat_id)
    user_content = content.strip()
    if user_content == "":
        raise AssistantValidationError("Az üzenet nem lehet üres.")

    effective_temperature = temperature if temperature is not None else chat.temperature
    tool_policy = _resolve_tool_mode_policy(settings, tool_mode)
    effective_reasoning = _resolve_effective_reasoning_mode(
        reasoning_mode, chat.reasoning_mode, tool_policy
    )
    _enforce_sensitive_request(
        settings,
        user_content,
        chat_id=chat.id,
        tool_mode=tool_policy.id,
        route="send_stream",
    )
    next_sequence = _next_sequence_index(chat)
    pending_messages = [*chat.messages, _pending_message("user", user_content, next_sequence)]
    _ensure_context_budget(settings, _generation_messages(pending_messages, tool_policy))
    chat_model = _resolve_configured_chat_model(settings)
    graphrag_context = _prepare_graphrag_context(
        settings,
        tool_policy,
        user_content,
        graphrag_client,
    )

    user_message = AssistantMessageModel(
        chat_id=chat.id,
        role="user",
        content=user_content,
        sequence_index=next_sequence,
        reasoning_mode=effective_reasoning,
        message_metadata={},
    )
    db.add(user_message)
    if len(chat.messages) == 0 and chat.title == DEFAULT_CHAT_TITLE:
        chat.title = _title_from_content(user_content)
    chat.reasoning_mode = effective_reasoning
    chat.temperature = effective_temperature
    chat.updated_at = _now()
    db.flush()

    tool_prompt, call_frame = _prompt_parts(tool_policy, graphrag_context)
    llm_messages = _to_llm_messages(
        settings,
        _generation_messages([*chat.messages, user_message], tool_policy),
        tool_prompt,
        call_frame,
    )
    _ensure_llm_context_budget(settings, llm_messages)
    prepared = PreparedAssistantStream(
        chat_id=chat.id,
        model=chat_model,
        messages=llm_messages,
        assistant_sequence_index=next_sequence + 1,
        reasoning_mode=effective_reasoning,
        temperature=effective_temperature,
        integrations=list(tool_policy.integration_ids),
        tool_mode=tool_policy.id,
        message_metadata=_graphrag_message_metadata(graphrag_context),
        direct_final_content=(
            NO_EVIDENCE_RESPONSE
            if graphrag_context is not None and not graphrag_context.has_evidence
            else None
        ),
        started_at=perf_counter(),
    )
    db.commit()
    return prepared


def finalize_streamed_assistant_message(
    db: Session,
    prepared: PreparedAssistantStream,
    *,
    content: str,
    model: str,
    reasoning_content: str | None = None,
    tool_activity_content: str | None = None,
    work_narration_content: str | None = None,
    generation_duration_ms: int | None = None,
    settings: Settings | None = None,
) -> AssistantChatModel:
    settings = settings or get_settings()
    chat = _get_active_chat(db, prepared.chat_id)
    _ensure_sensitive_output(
        settings,
        (content, reasoning_content, tool_activity_content, work_narration_content),
        chat_id=chat.id,
        tool_mode=prepared.tool_mode,
        route="stream_finalize",
    )
    if prepared.replace_message_id is not None:
        existing = db.get(AssistantMessageModel, prepared.replace_message_id)
        if existing is not None and existing.chat_id == chat.id and existing.role == "assistant":
            db.delete(existing)
            db.flush()
    measured_generation_duration_ms = (
        generation_duration_ms
        if generation_duration_ms is not None
        else _duration_ms_since(prepared.started_at)
    )
    db.add(
        AssistantMessageModel(
            chat_id=chat.id,
            role="assistant",
            content=content,
            reasoning_content=_normalize_reasoning_content(reasoning_content),
            tool_activity_content=_normalize_tool_activity_content(tool_activity_content),
            work_narration_content=_normalize_work_narration_content(work_narration_content),
            generation_duration_ms=measured_generation_duration_ms,
            sequence_index=prepared.assistant_sequence_index,
            model=model,
            reasoning_mode=prepared.reasoning_mode,
            message_metadata=prepared.message_metadata or {},
        )
    )
    chat.updated_at = _now()
    db.commit()
    return _get_active_chat(db, chat.id)


def regenerate_latest_assistant_message(
    db: Session,
    chat_id: int,
    *,
    reasoning_mode: str | None = None,
    temperature: float | None = None,
    tool_mode: str | None = None,
    settings: Settings | None = None,
    provider: LLMProvider | None = None,
    graphrag_client: GraphRAGClient | None = None,
) -> AssistantChatModel:
    settings = settings or get_settings()
    chat = _get_active_chat(db, chat_id)
    if len(chat.messages) < 2:
        raise AssistantValidationError("Nincs újragenerálható assistant válasz.")
    latest = chat.messages[-1]
    previous = chat.messages[-2]
    if latest.role != "assistant" or previous.role != "user":
        raise AssistantValidationError("Csak a legutolsó assistant válasz generálható újra.")

    effective_temperature = temperature if temperature is not None else chat.temperature
    tool_policy = _resolve_tool_mode_policy(settings, tool_mode)
    effective_reasoning = _resolve_effective_reasoning_mode(
        reasoning_mode, chat.reasoning_mode, tool_policy
    )
    _enforce_sensitive_request(
        settings,
        previous.content,
        chat_id=chat.id,
        tool_mode=tool_policy.id,
        route="regenerate_non_stream",
    )
    context_messages = chat.messages[:-1]
    _ensure_context_budget(settings, _generation_messages(context_messages, tool_policy))
    chat_model = _resolve_configured_chat_model(settings, provider)
    graphrag_context = _prepare_graphrag_context(
        settings,
        tool_policy,
        previous.content,
        graphrag_client,
    )

    replacement_sequence = latest.sequence_index

    if graphrag_context is not None and not graphrag_context.has_evidence:
        completion = LLMChatCompletion(
            model=chat_model,
            content=NO_EVIDENCE_RESPONSE,
            generation_duration_ms=0,
        )
    else:
        completion = _complete_chat(
            settings,
            provider,
            context_messages,
            reasoning_mode=effective_reasoning,
            temperature=effective_temperature,
            tool_policy=tool_policy,
            graphrag_context=graphrag_context,
        )
    _ensure_sensitive_output(
        settings,
        (completion.content, completion.work_narration_content),
        chat_id=chat.id,
        tool_mode=tool_policy.id,
        route="regenerate_non_stream",
    )
    db.delete(latest)
    chat.reasoning_mode = effective_reasoning
    chat.temperature = effective_temperature
    chat.updated_at = _now()
    db.flush()
    db.add(
        AssistantMessageModel(
            chat_id=chat.id,
            role="assistant",
            content=completion.content,
            work_narration_content=_normalize_work_narration_content(
                completion.work_narration_content
            ),
            generation_duration_ms=completion.generation_duration_ms,
            sequence_index=replacement_sequence,
            model=completion.model,
            reasoning_mode=effective_reasoning,
            message_metadata=_graphrag_message_metadata(graphrag_context),
        )
    )
    chat.updated_at = _now()
    db.commit()
    return _get_active_chat(db, chat.id)


def prepare_regenerate_message_stream(
    db: Session,
    chat_id: int,
    *,
    reasoning_mode: str | None = None,
    temperature: float | None = None,
    tool_mode: str | None = None,
    settings: Settings | None = None,
    graphrag_client: GraphRAGClient | None = None,
) -> PreparedAssistantStream:
    settings = settings or get_settings()
    chat = _get_active_chat(db, chat_id)
    if len(chat.messages) < 2:
        raise AssistantValidationError("Nincs újragenerálható assistant válasz.")
    latest = chat.messages[-1]
    previous = chat.messages[-2]
    if latest.role != "assistant" or previous.role != "user":
        raise AssistantValidationError("Csak a legutolsó assistant válasz generálható újra.")

    effective_temperature = temperature if temperature is not None else chat.temperature
    tool_policy = _resolve_tool_mode_policy(settings, tool_mode)
    effective_reasoning = _resolve_effective_reasoning_mode(
        reasoning_mode, chat.reasoning_mode, tool_policy
    )
    _enforce_sensitive_request(
        settings,
        previous.content,
        chat_id=chat.id,
        tool_mode=tool_policy.id,
        route="regenerate_stream",
    )
    context_messages = list(chat.messages[:-1])
    _ensure_context_budget(settings, _generation_messages(context_messages, tool_policy))
    chat_model = _resolve_configured_chat_model(settings)
    graphrag_context = _prepare_graphrag_context(
        settings,
        tool_policy,
        previous.content,
        graphrag_client,
    )
    tool_prompt, call_frame = _prompt_parts(tool_policy, graphrag_context)
    llm_messages = _to_llm_messages(
        settings,
        _generation_messages(context_messages, tool_policy),
        tool_prompt,
        call_frame,
    )
    _ensure_llm_context_budget(settings, llm_messages)

    prepared = PreparedAssistantStream(
        chat_id=chat.id,
        model=chat_model,
        messages=llm_messages,
        assistant_sequence_index=latest.sequence_index,
        reasoning_mode=effective_reasoning,
        temperature=effective_temperature,
        integrations=list(tool_policy.integration_ids),
        tool_mode=tool_policy.id,
        message_metadata=_graphrag_message_metadata(graphrag_context),
        direct_final_content=(
            NO_EVIDENCE_RESPONSE
            if graphrag_context is not None and not graphrag_context.has_evidence
            else None
        ),
        started_at=perf_counter(),
        replace_message_id=latest.id,
    )
    chat.reasoning_mode = effective_reasoning
    chat.temperature = effective_temperature
    chat.updated_at = _now()
    db.commit()
    return prepared


def update_unanswered_last_user_message(
    db: Session,
    chat_id: int,
    message_id: int,
    content: str,
    *,
    settings: Settings | None = None,
) -> AssistantChatModel:
    settings = settings or get_settings()
    chat = _get_active_chat(db, chat_id)
    if len(chat.messages) == 0:
        raise AssistantValidationError("Nincs szerkeszthető user üzenet.")

    latest = chat.messages[-1]
    if latest.role != "user" or latest.id != message_id:
        raise AssistantValidationError("Csak a megválaszolatlan utolsó user üzenet szerkeszthető.")

    user_content = content.strip()
    if user_content == "":
        raise AssistantValidationError("Az üzenet nem lehet üres.")
    _enforce_sensitive_request(
        settings,
        user_content,
        chat_id=chat.id,
        tool_mode="unknown",
        route="edit_unanswered_user",
    )

    pending_messages = [
        *chat.messages[:-1],
        _pending_message("user", user_content, latest.sequence_index),
    ]
    _ensure_context_budget(settings, pending_messages)

    latest.content = user_content
    if len(chat.messages) == 1 and chat.title == DEFAULT_CHAT_TITLE:
        chat.title = _title_from_content(user_content)
    chat.updated_at = _now()
    db.commit()
    return _get_active_chat(db, chat.id)


def prepare_retry_last_user_message_stream(
    db: Session,
    chat_id: int,
    *,
    reasoning_mode: str | None = None,
    temperature: float | None = None,
    tool_mode: str | None = None,
    settings: Settings | None = None,
    graphrag_client: GraphRAGClient | None = None,
) -> PreparedAssistantStream:
    settings = settings or get_settings()
    chat = _get_active_chat(db, chat_id)
    if len(chat.messages) == 0:
        raise AssistantValidationError("Nincs újraküldhető user üzenet.")
    latest = chat.messages[-1]
    if latest.role != "user":
        raise AssistantValidationError("Csak megválaszolatlan utolsó user üzenet küldhető újra.")

    effective_temperature = temperature if temperature is not None else chat.temperature
    tool_policy = _resolve_tool_mode_policy(settings, tool_mode)
    effective_reasoning = _resolve_effective_reasoning_mode(
        reasoning_mode, chat.reasoning_mode, tool_policy
    )
    _enforce_sensitive_request(
        settings,
        latest.content,
        chat_id=chat.id,
        tool_mode=tool_policy.id,
        route="retry_stream",
    )
    context_messages = list(chat.messages)
    _ensure_context_budget(settings, _generation_messages(context_messages, tool_policy))
    chat_model = _resolve_configured_chat_model(settings)
    graphrag_context = _prepare_graphrag_context(
        settings,
        tool_policy,
        latest.content,
        graphrag_client,
    )
    tool_prompt, call_frame = _prompt_parts(tool_policy, graphrag_context)
    llm_messages = _to_llm_messages(
        settings,
        _generation_messages(context_messages, tool_policy),
        tool_prompt,
        call_frame,
    )
    _ensure_llm_context_budget(settings, llm_messages)

    prepared = PreparedAssistantStream(
        chat_id=chat.id,
        model=chat_model,
        messages=llm_messages,
        assistant_sequence_index=latest.sequence_index + 1,
        reasoning_mode=effective_reasoning,
        temperature=effective_temperature,
        integrations=list(tool_policy.integration_ids),
        tool_mode=tool_policy.id,
        message_metadata=_graphrag_message_metadata(graphrag_context),
        direct_final_content=(
            NO_EVIDENCE_RESPONSE
            if graphrag_context is not None and not graphrag_context.has_evidence
            else None
        ),
        started_at=perf_counter(),
    )
    chat.reasoning_mode = effective_reasoning
    chat.temperature = effective_temperature
    chat.updated_at = _now()
    db.commit()
    return prepared


def _complete_chat(
    settings: Settings,
    provider: LLMProvider | None,
    messages: list[AssistantMessageModel],
    *,
    reasoning_mode: str,
    temperature: float | None,
    tool_policy: ToolModePolicy,
    graphrag_context: PreparedGraphRAGContext | None = None,
) -> LLMChatCompletion:
    provider = provider or get_llm_provider_for_tool_mode(settings, tool_policy.id)
    chat_kwargs = {
        "temperature": temperature,
        "max_tokens": settings.lm_studio_default_max_output_tokens,
        "reasoning_mode": _llm_reasoning_mode(reasoning_mode),
    }
    if tool_policy.integration_ids:
        chat_kwargs["integrations"] = list(tool_policy.integration_ids)
    chat_model = _resolve_configured_chat_model(settings, provider)
    tool_prompt, call_frame = _prompt_parts(tool_policy, graphrag_context)
    llm_messages = _to_llm_messages(
        settings,
        _generation_messages(messages, tool_policy),
        tool_prompt,
        call_frame,
    )
    _ensure_llm_context_budget(settings, llm_messages)
    started_at = perf_counter()
    completion = provider.chat_completion(
        chat_model,
        llm_messages,
        **chat_kwargs,
    )
    return LLMChatCompletion(
        model=completion.model,
        content=completion.content,
        work_narration_content=completion.work_narration_content,
        generation_duration_ms=_duration_ms_since(started_at),
    )


def _resolve_configured_chat_model(settings: Settings, provider: LLMProvider | None = None) -> str:
    model_id = settings.lm_studio_chat_model.strip()
    if model_id == "":
        raise AssistantModelNotLoadedError(
            "Nincs beállított chat modell az alkalmazás konfigurációjában."
        )
    provider = provider or get_llm_provider(settings)
    available_model_ids = [model.id for model in provider.list_models()]
    if model_id not in available_model_ids:
        raise AssistantModelNotLoadedError(
            f"Az alkalmazásban beállított chat modell nem található az LM Studio listában: {model_id}"
        )
    loaded_model_ids = provider.loaded_model_instance_ids()
    if not any(
        _is_loaded_model_instance(instance_id, model_id) for instance_id in loaded_model_ids
    ):
        raise AssistantModelNotLoadedError(
            f"Az alkalmazásban beállított chat modell nincs betöltve az LM Studio-ban: {model_id}"
        )
    return model_id


def _is_loaded_model_instance(instance_id: str, model_id: str) -> bool:
    return instance_id == model_id or instance_id.startswith(model_id + ":")


def _get_active_chat(db: Session, chat_id: int) -> AssistantChatModel:
    chat = db.scalar(
        select(AssistantChatModel)
        .options(selectinload(AssistantChatModel.messages))
        .where(AssistantChatModel.id == chat_id, AssistantChatModel.status == "active")
        .execution_options(populate_existing=True)
    )
    if chat is None:
        raise AssistantNotFoundError("A beszélgetés nem található.")
    return chat


def _generation_messages(
    messages: list[AssistantMessageModel],
    tool_policy: ToolModePolicy,
) -> list[AssistantMessageModel]:
    if tool_policy.id == "none":
        return messages
    for message in reversed(messages):
        if message.role == "user":
            return [message]
    raise AssistantValidationError(
        "A forrásalapú válaszhoz nem található aktuális felhasználói üzenet."
    )


def _to_llm_messages(
    settings: Settings,
    messages: list[AssistantMessageModel],
    tool_prompt: str | None = None,
    call_frame: str | None = None,
) -> list[LLMChatMessage]:
    system_prompt = (
        settings.assistant_system_prompt.rstrip() + "\n\n" + INTERNAL_INSTRUCTION_PROTECTION_RULE
    )
    if tool_prompt:
        system_prompt = system_prompt.rstrip() + "\n\n" + tool_prompt.strip()
    llm_messages = [
        LLMChatMessage(role=message.role, content=message.content) for message in messages
    ]
    if call_frame:
        llm_messages = _apply_call_frame_to_latest_user_message(llm_messages, call_frame)
    return [LLMChatMessage(role="system", content=system_prompt), *llm_messages]


def _apply_call_frame_to_latest_user_message(
    messages: list[LLMChatMessage],
    call_frame: str,
) -> list[LLMChatMessage]:
    framed_messages = list(messages)
    for index in range(len(framed_messages) - 1, -1, -1):
        message = framed_messages[index]
        if message.role != "user":
            continue
        framed_messages[index] = LLMChatMessage(
            role=message.role,
            content=call_frame.format(user_content=message.content),
        )
        break
    return framed_messages


def _ensure_context_budget(settings: Settings, messages: list[AssistantMessageModel]) -> None:
    actual = len(settings.assistant_system_prompt) + sum(
        len(message.content) for message in messages
    )
    if actual > settings.assistant_context_char_budget:
        raise AssistantContextLimitError(
            "A beszélgetés meghaladja a 120000 karakteres kontextuskeretet.",
            budget=settings.assistant_context_char_budget,
            actual=actual,
        )


def _ensure_llm_context_budget(settings: Settings, messages: list[LLMChatMessage]) -> None:
    actual = sum(len(message.content) for message in messages)
    if actual > settings.assistant_context_char_budget:
        raise AssistantContextLimitError(
            "Az összeállított kérés meghaladja a konfigurált kontextuskeretet.",
            budget=settings.assistant_context_char_budget,
            actual=actual,
        )


def _prepare_graphrag_context(
    settings: Settings,
    tool_policy: ToolModePolicy,
    user_content: str,
    client: GraphRAGClient | None,
) -> PreparedGraphRAGContext | None:
    if tool_policy.execution_kind != "graphrag_http":
        return None
    response = (client or get_graphrag_client(settings)).retrieve(user_content)
    return compile_graphrag_context(
        response,
        char_budget=settings.graphrag_context_char_budget,
    )


def _prompt_parts(
    tool_policy: ToolModePolicy,
    graphrag_context: PreparedGraphRAGContext | None,
) -> tuple[str | None, str | None]:
    if graphrag_context is None:
        return tool_policy.prompt_instructions, tool_policy.call_frame
    return tool_policy.prompt_instructions, graphrag_context.call_frame


def _graphrag_message_metadata(
    graphrag_context: PreparedGraphRAGContext | None,
) -> dict:
    if graphrag_context is None:
        return {}
    return graphrag_context.message_metadata


def build_sensitive_output_guard(settings: Settings) -> SensitiveOutputGuard:
    return SensitiveOutputGuard(
        SensitiveValueRegistry.from_settings(settings),
        protected_instructions=(
            settings.assistant_system_prompt,
            INTERNAL_INSTRUCTION_PROTECTION_RULE,
            GRAPHRAG_TOOL_PROMPT,
            OBSIDIAN_TOOL_PROMPT,
            OBSIDIAN_CALL_FRAME,
            EXCEL_TOOL_PROMPT,
            EXCEL_CALL_FRAME,
        ),
    )


def _enforce_sensitive_request(
    settings: Settings,
    content: str,
    *,
    chat_id: int,
    tool_mode: str,
    route: str,
) -> None:
    if not settings.sensitive_request_guard_enabled:
        return
    decision = SensitiveRequestGuard().evaluate(content)
    if not decision.blocked or decision.category is None:
        return
    logger.warning(
        "sensitive_guard blocked input category=%s chat_id=%s tool_mode=%s route=%s",
        decision.category.value,
        chat_id,
        tool_mode,
        route,
    )
    raise AssistantSensitiveRequestError(decision.category.value)


def _ensure_sensitive_output(
    settings: Settings,
    contents: tuple[str | None, ...],
    *,
    chat_id: int,
    tool_mode: str,
    route: str,
) -> None:
    if not settings.sensitive_output_guard_enabled:
        return
    guard = build_sensitive_output_guard(settings)
    try:
        for content in contents:
            if content:
                guard.ensure_safe(content)
    except SensitiveOutputBlocked as exc:
        category = exc.match.category.value
        logger.warning(
            "sensitive_guard blocked output category=%s chat_id=%s tool_mode=%s route=%s",
            category,
            chat_id,
            tool_mode,
            route,
        )
        raise AssistantSensitiveOutputError(category) from exc


def _normalize_reasoning_content(reasoning_content: str | None) -> str | None:
    if reasoning_content is None:
        return None
    compact = reasoning_content.strip()
    if compact == "":
        return None
    if len(compact) <= MAX_REASONING_SAVE_CHARS:
        return compact
    return compact[:MAX_REASONING_SAVE_CHARS].rstrip() + REASONING_TRUNCATED_SUFFIX


def _normalize_tool_activity_content(tool_activity_content: str | None) -> str | None:
    if tool_activity_content is None:
        return None
    compact = tool_activity_content.strip()
    if compact == "":
        return None
    if len(compact) <= MAX_TOOL_ACTIVITY_SAVE_CHARS:
        return compact
    return compact[:MAX_TOOL_ACTIVITY_SAVE_CHARS].rstrip() + TOOL_ACTIVITY_TRUNCATED_SUFFIX


def _normalize_work_narration_content(work_narration_content: str | None) -> str | None:
    if work_narration_content is None:
        return None
    compact = work_narration_content.strip()
    if compact == "":
        return None
    if len(compact) <= MAX_WORK_NARRATION_SAVE_CHARS:
        return compact
    return compact[:MAX_WORK_NARRATION_SAVE_CHARS].rstrip() + WORK_NARRATION_TRUNCATED_SUFFIX


def _resolve_effective_reasoning_mode(
    requested_reasoning_mode: str | None,
    stored_reasoning_mode: str,
    tool_policy: ToolModePolicy,
) -> str:
    if not tool_mode_supports_reasoning(tool_policy.id):
        return "normal"
    return requested_reasoning_mode or stored_reasoning_mode


def _resolve_tool_mode_policy(settings: Settings, tool_mode: str | None) -> ToolModePolicy:
    try:
        return resolve_tool_mode_policy(settings, tool_mode)
    except ValueError as exc:
        raise AssistantValidationError(str(exc)) from exc


def _llm_reasoning_mode(reasoning_mode: str) -> str:
    if reasoning_mode == "model_default":
        return "model_default"
    return "off"


def _next_sequence_index(chat: AssistantChatModel) -> int:
    if not chat.messages:
        return 0
    return max(message.sequence_index for message in chat.messages) + 1


def _title_from_content(content: str) -> str:
    title = _compact_whitespace(content)[:60].strip()
    return title or DEFAULT_CHAT_TITLE


def _compact_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _now() -> datetime:
    return datetime.now(UTC)


def _duration_ms_since(started_at: float | None) -> int | None:
    if not started_at:
        return None
    return max(0, round((perf_counter() - started_at) * 1000))


def _pending_message(role: str, content: str, sequence_index: int) -> AssistantMessageModel:
    return AssistantMessageModel(
        role=role, content=content, sequence_index=sequence_index, message_metadata={}
    )
