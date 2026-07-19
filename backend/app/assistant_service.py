from dataclasses import dataclass
from datetime import UTC, datetime
import re

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings, get_settings
from app.llm_provider import LLMChatMessage, LLMProvider, get_llm_provider
from app.models import AssistantChatModel, AssistantMessageModel
from app.tool_modes import ToolModePolicy, resolve_tool_mode_policy

DEFAULT_CHAT_TITLE = 'Új beszélgetés'
CONTEXT_LIMIT_CODE = 'context_limit_exceeded'
MAX_REASONING_SAVE_CHARS = 100_000
REASONING_TRUNCATED_SUFFIX = '\n\n[... A gondolatmenet roviditve lett.]'
MAX_TOOL_ACTIVITY_SAVE_CHARS = 100_000
TOOL_ACTIVITY_TRUNCATED_SUFFIX = '\n\n[... Az eszkozhasznalat roviditve lett.]'
MAX_WORK_NARRATION_SAVE_CHARS = 100_000
WORK_NARRATION_TRUNCATED_SUFFIX = '\n\n[... A munkalepesek roviditve lettek.]'


@dataclass(frozen=True)
class PreparedAssistantStream:
    chat_id: int
    model: str
    messages: list[LLMChatMessage]
    assistant_sequence_index: int
    reasoning_mode: str
    temperature: float | None
    integrations: list[str]
    replace_message_id: int | None = None


class AssistantError(RuntimeError):
    pass


class AssistantNotFoundError(AssistantError):
    pass


class AssistantValidationError(AssistantError):
    pass


class AssistantModelNotLoadedError(AssistantError):
    pass


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
    reasoning_mode: str = 'normal',
    temperature: float | None = None,
) -> AssistantChatModel:
    chat = AssistantChatModel(
        title=DEFAULT_CHAT_TITLE,
        status='active',
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
            .where(AssistantChatModel.status == 'active')
            .order_by(AssistantChatModel.updated_at.desc(), AssistantChatModel.id.desc())
        )
    )


def get_chat(db: Session, chat_id: int) -> AssistantChatModel:
    return _get_active_chat(db, chat_id)


def rename_chat(db: Session, chat_id: int, title: str) -> AssistantChatModel:
    chat = _get_active_chat(db, chat_id)
    compact_title = _compact_whitespace(title)[:120]
    if compact_title == '':
        raise AssistantValidationError('A cím nem lehet üres.')
    chat.title = compact_title
    chat.updated_at = _now()
    db.commit()
    return _get_active_chat(db, chat.id)


def soft_delete_chat(db: Session, chat_id: int) -> None:
    chat = _get_active_chat(db, chat_id)
    chat.status = 'deleted'
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
) -> AssistantChatModel:
    settings = settings or get_settings()
    chat = _get_active_chat(db, chat_id)
    user_content = content.strip()
    if user_content == '':
        raise AssistantValidationError('Az üzenet nem lehet üres.')

    effective_reasoning = reasoning_mode or chat.reasoning_mode
    effective_temperature = temperature if temperature is not None else chat.temperature
    tool_policy = _resolve_tool_mode_policy(settings, tool_mode)
    next_sequence = _next_sequence_index(chat)
    pending_messages = [*chat.messages, _pending_message('user', user_content, next_sequence)]
    _ensure_context_budget(settings, pending_messages)
    _resolve_configured_chat_model(settings, provider)

    user_message = AssistantMessageModel(
        chat_id=chat.id,
        role='user',
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

    completion = _complete_chat(
        settings,
        provider,
        [*chat.messages, user_message],
        reasoning_mode=effective_reasoning,
        temperature=effective_temperature,
        tool_policy=tool_policy,
    )
    db.add(
        AssistantMessageModel(
            chat_id=chat.id,
            role='assistant',
            content=completion.content,
            work_narration_content=_normalize_work_narration_content(completion.work_narration_content),
            sequence_index=next_sequence + 1,
            model=completion.model,
            reasoning_mode=effective_reasoning,
            message_metadata={},
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
) -> PreparedAssistantStream:
    settings = settings or get_settings()
    chat = _get_active_chat(db, chat_id)
    user_content = content.strip()
    if user_content == '':
        raise AssistantValidationError('Az üzenet nem lehet üres.')

    effective_reasoning = reasoning_mode or chat.reasoning_mode
    effective_temperature = temperature if temperature is not None else chat.temperature
    tool_policy = _resolve_tool_mode_policy(settings, tool_mode)
    next_sequence = _next_sequence_index(chat)
    pending_messages = [*chat.messages, _pending_message('user', user_content, next_sequence)]
    _ensure_context_budget(settings, pending_messages)
    chat_model = _resolve_configured_chat_model(settings)

    user_message = AssistantMessageModel(
        chat_id=chat.id,
        role='user',
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

    llm_messages = _to_llm_messages(settings, [*chat.messages, user_message], tool_policy.prompt_instructions, tool_policy.call_frame)
    prepared = PreparedAssistantStream(
        chat_id=chat.id,
        model=chat_model,
        messages=llm_messages,
        assistant_sequence_index=next_sequence + 1,
        reasoning_mode=effective_reasoning,
        temperature=effective_temperature,
        integrations=list(tool_policy.integration_ids),
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
) -> AssistantChatModel:
    chat = _get_active_chat(db, prepared.chat_id)
    if prepared.replace_message_id is not None:
        existing = db.get(AssistantMessageModel, prepared.replace_message_id)
        if existing is not None and existing.chat_id == chat.id and existing.role == 'assistant':
            db.delete(existing)
            db.flush()
    db.add(
        AssistantMessageModel(
            chat_id=chat.id,
            role='assistant',
            content=content,
            reasoning_content=_normalize_reasoning_content(reasoning_content),
            tool_activity_content=_normalize_tool_activity_content(tool_activity_content),
            work_narration_content=_normalize_work_narration_content(work_narration_content),
            sequence_index=prepared.assistant_sequence_index,
            model=model,
            reasoning_mode=prepared.reasoning_mode,
            message_metadata={},
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
) -> AssistantChatModel:
    settings = settings or get_settings()
    chat = _get_active_chat(db, chat_id)
    if len(chat.messages) < 2:
        raise AssistantValidationError('Nincs újragenerálható assistant válasz.')
    latest = chat.messages[-1]
    previous = chat.messages[-2]
    if latest.role != 'assistant' or previous.role != 'user':
        raise AssistantValidationError('Csak a legutolsó assistant válasz generálható újra.')

    effective_reasoning = reasoning_mode or chat.reasoning_mode
    effective_temperature = temperature if temperature is not None else chat.temperature
    tool_policy = _resolve_tool_mode_policy(settings, tool_mode)
    context_messages = chat.messages[:-1]
    _ensure_context_budget(settings, context_messages)
    _resolve_configured_chat_model(settings, provider)

    replacement_sequence = latest.sequence_index
    db.delete(latest)
    chat.reasoning_mode = effective_reasoning
    chat.temperature = effective_temperature
    chat.updated_at = _now()
    db.flush()

    completion = _complete_chat(
        settings,
        provider,
        context_messages,
        reasoning_mode=effective_reasoning,
        temperature=effective_temperature,
        tool_policy=tool_policy,
    )
    db.add(
        AssistantMessageModel(
            chat_id=chat.id,
            role='assistant',
            content=completion.content,
            work_narration_content=_normalize_work_narration_content(completion.work_narration_content),
            sequence_index=replacement_sequence,
            model=completion.model,
            reasoning_mode=effective_reasoning,
            message_metadata={},
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
) -> PreparedAssistantStream:
    settings = settings or get_settings()
    chat = _get_active_chat(db, chat_id)
    if len(chat.messages) < 2:
        raise AssistantValidationError('Nincs újragenerálható assistant válasz.')
    latest = chat.messages[-1]
    previous = chat.messages[-2]
    if latest.role != 'assistant' or previous.role != 'user':
        raise AssistantValidationError('Csak a legutolsó assistant válasz generálható újra.')

    effective_reasoning = reasoning_mode or chat.reasoning_mode
    effective_temperature = temperature if temperature is not None else chat.temperature
    tool_policy = _resolve_tool_mode_policy(settings, tool_mode)
    context_messages = list(chat.messages[:-1])
    _ensure_context_budget(settings, context_messages)
    chat_model = _resolve_configured_chat_model(settings)

    prepared = PreparedAssistantStream(
        chat_id=chat.id,
        model=chat_model,
        messages=_to_llm_messages(settings, context_messages, tool_policy.prompt_instructions, tool_policy.call_frame),
        assistant_sequence_index=latest.sequence_index,
        reasoning_mode=effective_reasoning,
        temperature=effective_temperature,
        integrations=list(tool_policy.integration_ids),
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

    pending_messages = [*chat.messages[:-1], _pending_message("user", user_content, latest.sequence_index)]
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
) -> PreparedAssistantStream:
    settings = settings or get_settings()
    chat = _get_active_chat(db, chat_id)
    if len(chat.messages) == 0:
        raise AssistantValidationError('Nincs újraküldhető user üzenet.')
    latest = chat.messages[-1]
    if latest.role != 'user':
        raise AssistantValidationError('Csak megválaszolatlan utolsó user üzenet küldhető újra.')

    effective_reasoning = reasoning_mode or chat.reasoning_mode
    effective_temperature = temperature if temperature is not None else chat.temperature
    tool_policy = _resolve_tool_mode_policy(settings, tool_mode)
    context_messages = list(chat.messages)
    _ensure_context_budget(settings, context_messages)
    chat_model = _resolve_configured_chat_model(settings)

    prepared = PreparedAssistantStream(
        chat_id=chat.id,
        model=chat_model,
        messages=_to_llm_messages(settings, context_messages, tool_policy.prompt_instructions, tool_policy.call_frame),
        assistant_sequence_index=latest.sequence_index + 1,
        reasoning_mode=effective_reasoning,
        temperature=effective_temperature,
        integrations=list(tool_policy.integration_ids),
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
):
    provider = provider or get_llm_provider(settings)
    chat_kwargs = {
        'temperature': temperature,
        'max_tokens': settings.lm_studio_default_max_output_tokens,
        'reasoning_mode': _llm_reasoning_mode(reasoning_mode),
    }
    if tool_policy.integration_ids:
        chat_kwargs['integrations'] = list(tool_policy.integration_ids)
    chat_model = _resolve_configured_chat_model(settings, provider)
    return provider.chat_completion(
        chat_model,
        _to_llm_messages(settings, messages, tool_policy.prompt_instructions, tool_policy.call_frame),
        **chat_kwargs,
    )


def _resolve_configured_chat_model(settings: Settings, provider: LLMProvider | None = None) -> str:
    model_id = settings.lm_studio_chat_model.strip()
    if model_id == "":
        raise AssistantModelNotLoadedError("Nincs beállított chat modell az alkalmazás konfigurációjában.")
    provider = provider or get_llm_provider(settings)
    available_model_ids = [model.id for model in provider.list_models()]
    if model_id not in available_model_ids:
        raise AssistantModelNotLoadedError(
            f"Az alkalmazásban beállított chat modell nem található az LM Studio listában: {model_id}"
        )
    loaded_model_ids = provider.loaded_model_instance_ids()
    if not any(_is_loaded_model_instance(instance_id, model_id) for instance_id in loaded_model_ids):
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
        .where(AssistantChatModel.id == chat_id, AssistantChatModel.status == 'active')
        .execution_options(populate_existing=True)
    )
    if chat is None:
        raise AssistantNotFoundError('A beszélgetés nem található.')
    return chat


def _to_llm_messages(
    settings: Settings,
    messages: list[AssistantMessageModel],
    tool_prompt: str | None = None,
    call_frame: str | None = None,
) -> list[LLMChatMessage]:
    system_prompt = settings.assistant_system_prompt
    if tool_prompt:
        system_prompt = system_prompt.rstrip() + "\n\n" + tool_prompt.strip()
    llm_messages = [LLMChatMessage(role=message.role, content=message.content) for message in messages]
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
    actual = len(settings.assistant_system_prompt) + sum(len(message.content) for message in messages)
    if actual > settings.assistant_context_char_budget:
        raise AssistantContextLimitError(
            "A beszélgetés meghaladja a 120000 karakteres kontextuskeretet.",
            budget=settings.assistant_context_char_budget,
            actual=actual,
        )

def _normalize_reasoning_content(reasoning_content: str | None) -> str | None:
    if reasoning_content is None:
        return None
    compact = reasoning_content.strip()
    if compact == '':
        return None
    if len(compact) <= MAX_REASONING_SAVE_CHARS:
        return compact
    return compact[:MAX_REASONING_SAVE_CHARS].rstrip() + REASONING_TRUNCATED_SUFFIX


def _normalize_tool_activity_content(tool_activity_content: str | None) -> str | None:
    if tool_activity_content is None:
        return None
    compact = tool_activity_content.strip()
    if compact == '':
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


def _resolve_tool_mode_policy(settings: Settings, tool_mode: str | None) -> ToolModePolicy:
    try:
        return resolve_tool_mode_policy(settings, tool_mode)
    except ValueError as exc:
        raise AssistantValidationError(str(exc)) from exc


def _llm_reasoning_mode(reasoning_mode: str) -> str:
    if reasoning_mode == 'model_default':
        return 'model_default'
    return 'off'


def _next_sequence_index(chat: AssistantChatModel) -> int:
    if not chat.messages:
        return 0
    return max(message.sequence_index for message in chat.messages) + 1


def _title_from_content(content: str) -> str:
    title = _compact_whitespace(content)[:60].strip()
    return title or DEFAULT_CHAT_TITLE


def _compact_whitespace(value: str) -> str:
    return re.sub(r'\s+', ' ', value).strip()


def _now() -> datetime:
    return datetime.now(UTC)


def _pending_message(role: str, content: str, sequence_index: int) -> AssistantMessageModel:
    return AssistantMessageModel(role=role, content=content, sequence_index=sequence_index, message_metadata={})
