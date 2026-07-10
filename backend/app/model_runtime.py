from app.config import Settings

_selected_chat_model: str | None = None


def get_selected_chat_model(settings: Settings) -> str:
    return _selected_chat_model or settings.lm_studio_chat_model


def set_selected_chat_model(model_id: str) -> str:
    global _selected_chat_model
    normalized = model_id.strip()
    if normalized == "":
        raise ValueError("Chat model id is required")
    _selected_chat_model = normalized
    return normalized


def reset_selected_chat_model() -> None:
    global _selected_chat_model
    _selected_chat_model = None
