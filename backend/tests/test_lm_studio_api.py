from fastapi.testclient import TestClient

from app.config import get_settings
from app.llm_provider import LLMChatCompletion, LLMModel, LLMModelLoadResult, LLMModelUnloadResult, LLMProviderError
from app.main import create_app
from app.routers import lm_studio


class FakeProvider:
    def __init__(self, settings):
        self.settings = settings

    def smoke_check(self, selected_chat_model=None):
        return type(
            "Smoke",
            (),
            {
                "provider": "lm_studio_native",
                "base_url": "http://llm.local",
                "reachable": True,
                "model_ids": ["chat-model"],
                "configured_chat_model": "chat-model",
                "selected_chat_model": selected_chat_model or "chat-model",
                "configured_chat_model_available": True,
                "configured_chat_model_loaded": False,
                "selected_chat_model_available": True,
                "selected_chat_model_loaded": False,
                "loaded_model_ids": [],
                "error_message": None,
            },
        )()

    def list_models(self):
        return [LLMModel(id="chat-model")]

    def loaded_model_instance_ids(self):
        return ["chat-model:1"]

    def load_chat_model(self, model_id):
        assert model_id == "chat-model"
        return LLMModelLoadResult("llm", "chat-model:1", 1.0, "loaded", {"context_length": 61440})

    def unload_chat_model(self, model_id):
        assert model_id == "chat-model"
        return LLMModelUnloadResult("chat-model:1")

    def unload_model_instance(self, instance_id):
        assert instance_id == "chat-model:1"
        return LLMModelUnloadResult("chat-model:1")

    def chat_completion(self, model, messages, *, temperature=None, max_tokens=None, reasoning_mode="off"):
        assert model in {"chat-model", "qwen/qwen3.6-35b-a3b"}
        assert messages[0].role == "user"
        assert messages[0].content == "Szia"
        assert reasoning_mode == "off"
        return LLMChatCompletion(model="chat-model:1", content="Hello")


def test_lm_studio_routes(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setattr(lm_studio, "get_llm_provider", lambda settings: FakeProvider(settings))
    client = TestClient(create_app())

    health = client.get("/api/lm-studio/health")
    models = client.get("/api/lm-studio/models")
    select = client.post("/api/lm-studio/select-chat-model", json={"model_id": "chat-model"})
    load = client.post("/api/lm-studio/load-chat-model", json={"model_id": "chat-model"})
    unload = client.post("/api/lm-studio/unload-chat-model", json={"model_id": "chat-model"})
    chat = client.post("/api/lm-studio/chat", json={"messages": [{"role": "user", "content": "Szia"}]})

    assert health.status_code == 200
    assert health.json()["reachable"] is True
    assert health.json()["selected_chat_model"] == "qwen/qwen3.6-35b-a3b"
    assert models.json() == {
        "models": ["chat-model"],
        "loaded_model_ids": ["chat-model:1"],
        "configured_chat_model": "qwen/qwen3.6-35b-a3b",
        "selected_chat_model": "qwen/qwen3.6-35b-a3b",
    }
    assert select.json()["selected_chat_model"] == "chat-model"
    assert load.json()["instance_id"] == "chat-model:1"
    assert unload.json() == {"instance_id": "chat-model:1"}
    assert chat.json() == {"model": "chat-model:1", "content": "Hello"}


def test_lm_studio_chat_provider_error_maps_to_502(monkeypatch) -> None:
    class FailingProvider(FakeProvider):
        def chat_completion(self, *args, **kwargs):
            raise LLMProviderError("LM Studio unavailable")

    get_settings.cache_clear()
    monkeypatch.setattr(lm_studio, "get_llm_provider", lambda settings: FailingProvider(settings))
    client = TestClient(create_app())

    response = client.post("/api/lm-studio/chat", json={"messages": [{"role": "user", "content": "Szia"}]})

    assert response.status_code == 502
    assert response.json() == {"detail": "LM Studio unavailable"}
