import pytest

from app.model_runtime import reset_selected_chat_model


@pytest.fixture(autouse=True)
def reset_runtime_selected_chat_model():
    reset_selected_chat_model()
    yield
    reset_selected_chat_model()
