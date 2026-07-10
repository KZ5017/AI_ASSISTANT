import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import assistant_service
from app.config import Settings, get_settings
from app.db import Base, get_db
from app.llm_provider import LLMChatCompletion, LLMProviderError, LLMStreamEvent
from app.main import create_app
from app.routers import assistant as assistant_router


class FakeProvider:
    def __init__(self, content: str = 'assistant válasz') -> None:
        self.content = content
        self.calls = []

    def chat_completion(self, model, messages, *, temperature=None, max_tokens=None, reasoning_mode='off'):
        self.calls.append(
            {
                'model': model,
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'reasoning_mode': reasoning_mode,
            }
        )
        return LLMChatCompletion(model='fake-model:1', content=self.content)


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    app = create_app()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def test_create_chat_defaults(db_session: Session) -> None:
    chat = assistant_service.create_chat(db_session)

    assert chat.title == 'Új beszélgetés'
    assert chat.status == 'active'
    assert chat.reasoning_mode == 'normal'
    assert chat.messages == []


def test_send_message_persists_user_and_assistant_and_auto_titles(db_session: Session) -> None:
    provider = FakeProvider()
    settings = Settings(lm_studio_chat_model="chat-model")
    chat = assistant_service.create_chat(db_session)

    result = assistant_service.send_message(
        db_session,
        chat.id,
        '  Első kérdésem\n a modellhez.  ',
        reasoning_mode='model_default',
        temperature=0.4,
        settings=settings,
        provider=provider,
    )

    assert result.title == 'Első kérdésem a modellhez.'
    assert result.reasoning_mode == 'model_default'
    assert result.temperature == 0.4
    assert [(message.role, message.sequence_index) for message in result.messages] == [('user', 0), ('assistant', 1)]
    assert result.messages[0].content == 'Első kérdésem\n a modellhez.'
    assert result.messages[1].content == 'assistant válasz'
    assert provider.calls[0]['reasoning_mode'] == 'model_default'
    assert provider.calls[0]['messages'][0].role == 'system'
    assert provider.calls[0]['messages'][1].role == 'user'


def test_context_limit_rejects_oversized_send(db_session: Session) -> None:
    chat = assistant_service.create_chat(db_session)
    settings = Settings(assistant_context_char_budget=12, assistant_system_prompt='system')

    with pytest.raises(assistant_service.AssistantContextLimitError) as exc_info:
        assistant_service.send_message(
            db_session,
            chat.id,
            'túl hosszú üzenet',
            settings=settings,
            provider=FakeProvider(),
        )

    assert exc_info.value.code == 'context_limit_exceeded'
    assert exc_info.value.budget == 12


def test_regenerate_replaces_only_latest_assistant_message(db_session: Session) -> None:
    provider = FakeProvider('első válasz')
    chat = assistant_service.create_chat(db_session)
    assistant_service.send_message(db_session, chat.id, 'Szia', provider=provider)

    provider.content = 'második válasz'
    regenerated = assistant_service.regenerate_latest_assistant_message(
        db_session,
        chat.id,
        reasoning_mode='normal',
        provider=provider,
    )

    assert [(message.role, message.sequence_index) for message in regenerated.messages] == [('user', 0), ('assistant', 1)]
    assert regenerated.messages[-1].content == 'második válasz'
    assert provider.calls[-1]['reasoning_mode'] == 'off'


def test_soft_delete_hides_chat_from_list(db_session: Session) -> None:
    chat = assistant_service.create_chat(db_session)

    assistant_service.soft_delete_chat(db_session, chat.id)

    assert assistant_service.list_chats(db_session) == []
    with pytest.raises(assistant_service.AssistantNotFoundError):
        assistant_service.get_chat(db_session, chat.id)


def test_assistant_api_create_rename_delete(client: TestClient) -> None:
    created = client.post('/api/assistant/chats', json={}).json()
    chat_id = created['id']

    renamed = client.patch(f'/api/assistant/chats/{chat_id}', json={'title': ' Teszt chat  '})
    listed = client.get('/api/assistant/chats')
    deleted = client.delete(f'/api/assistant/chats/{chat_id}')

    assert renamed.status_code == 200
    assert renamed.json()['title'] == 'Teszt chat'
    assert listed.json()['chats'][0]['id'] == chat_id
    assert deleted.json() == {'status': 'deleted'}
    assert client.get('/api/assistant/chats').json() == {'chats': []}



def test_assistant_api_context_limit_detail(db_session: Session, monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("AI_ASSISTANT_ASSISTANT_CONTEXT_CHAR_BUDGET", "10")
    app = create_app()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    chat_id = client.post("/api/assistant/chats", json={}).json()["id"]

    response = client.post(f"/api/assistant/chats/{chat_id}/messages", json={"content": "nagyon hosszú"})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "context_limit_exceeded"
    get_settings.cache_clear()



def test_assistant_api_stream_message_persists_done_chat(db_session: Session, monkeypatch) -> None:
    class StreamingProvider:
        def __init__(self, settings):
            self.settings = settings

        def chat_completion_stream(self, model, messages, *, temperature=None, max_tokens=None, reasoning_mode='off'):
            assert model == get_settings().lm_studio_chat_model
            assert messages[0].role == 'system'
            assert messages[1].role == 'user'
            assert messages[1].content == 'Szia stream'
            assert reasoning_mode == 'model_default'
            yield LLMStreamEvent(type='reasoning_delta', content='Gondolkodom')
            yield LLMStreamEvent(type='message_delta', content='Szia')
            yield LLMStreamEvent(type='message_delta', content='!')
            yield LLMStreamEvent(type='done', final_content='Szia!', model='chat-model:stream')

    monkeypatch.setattr(assistant_router, 'LMStudioNativeProvider', StreamingProvider)
    chat = assistant_service.create_chat(db_session)
    app = create_app()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    response = client.post(
        f'/api/assistant/chats/{chat.id}/messages/stream',
        json={'content': 'Szia stream', 'reasoning_mode': 'model_default'},
    )

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/event-stream')
    body = response.text
    assert 'event: start' in body
    assert 'event: reasoning_delta' in body
    assert 'data: {"content": "Gondolkodom"}' in body
    assert 'event: delta' in body
    assert 'data: {"content": "Szia"}' in body
    assert 'event: done' in body

    persisted = assistant_service.get_chat(db_session, chat.id)
    assert [(message.role, message.sequence_index) for message in persisted.messages] == [('user', 0), ('assistant', 1)]
    assert persisted.messages[0].content == 'Szia stream'
    assert persisted.messages[1].content == 'Szia!'
    assert persisted.messages[1].model == 'chat-model:stream'


def test_assistant_api_stream_provider_error_does_not_persist_assistant(db_session: Session, monkeypatch) -> None:
    class FailingStreamingProvider:
        def __init__(self, settings):
            self.settings = settings

        def chat_completion_stream(self, *args, **kwargs):
            yield LLMStreamEvent(type='message_delta', content='fél')
            raise LLMProviderError("stream megszakadt")

    monkeypatch.setattr(assistant_router, 'LMStudioNativeProvider', FailingStreamingProvider)
    chat = assistant_service.create_chat(db_session)
    app = create_app()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    response = client.post(f'/api/assistant/chats/{chat.id}/messages/stream', json={'content': 'Szia'})

    assert response.status_code == 200
    assert 'event: delta' in response.text
    assert 'event: error' in response.text
    persisted = assistant_service.get_chat(db_session, chat.id)
    assert [(message.role, message.sequence_index) for message in persisted.messages] == [('user', 0)]



def test_assistant_api_stream_regenerate_replaces_latest_assistant(db_session: Session, monkeypatch) -> None:
    chat = assistant_service.create_chat(db_session)
    assistant_service.send_message(db_session, chat.id, 'Szia', settings=Settings(lm_studio_chat_model='chat-model'), provider=FakeProvider('régi válasz'))

    class StreamingProvider:
        def __init__(self, settings):
            self.settings = settings

        def chat_completion_stream(self, model, messages, *, temperature=None, max_tokens=None, reasoning_mode='off'):
            assert messages[-1].role == 'user'
            assert messages[-1].content == 'Szia'
            yield LLMStreamEvent(type='message_delta', content='új')
            yield LLMStreamEvent(type='message_delta', content=' válasz')
            yield LLMStreamEvent(type='done', final_content='új válasz', model='chat-model:regen')

    monkeypatch.setattr(assistant_router, 'LMStudioNativeProvider', StreamingProvider)
    app = create_app()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    response = client.post(f'/api/assistant/chats/{chat.id}/regenerate/stream', json={'reasoning_mode': 'normal'})

    assert response.status_code == 200
    assert 'event: delta' in response.text
    assert 'event: done' in response.text
    persisted = assistant_service.get_chat(db_session, chat.id)
    assert [(message.role, message.sequence_index) for message in persisted.messages] == [('user', 0), ('assistant', 1)]
    assert persisted.messages[-1].content == 'új válasz'
    assert persisted.messages[-1].model == 'chat-model:regen'


def test_assistant_api_stream_regenerate_provider_error_keeps_old_assistant(db_session: Session, monkeypatch) -> None:
    chat = assistant_service.create_chat(db_session)
    assistant_service.send_message(db_session, chat.id, 'Szia', settings=Settings(lm_studio_chat_model='chat-model'), provider=FakeProvider('régi válasz'))

    class FailingStreamingProvider:
        def __init__(self, settings):
            self.settings = settings

        def chat_completion_stream(self, *args, **kwargs):
            yield LLMStreamEvent(type='message_delta', content='fél')
            raise LLMProviderError('regen stream megszakadt')

    monkeypatch.setattr(assistant_router, 'LMStudioNativeProvider', FailingStreamingProvider)
    app = create_app()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    response = client.post(f'/api/assistant/chats/{chat.id}/regenerate/stream', json={'reasoning_mode': 'normal'})

    assert response.status_code == 200
    assert 'event: delta' in response.text
    assert 'event: error' in response.text
    persisted = assistant_service.get_chat(db_session, chat.id)
    assert [(message.role, message.sequence_index) for message in persisted.messages] == [('user', 0), ('assistant', 1)]
    assert persisted.messages[-1].content == 'régi válasz'



def test_assistant_api_stream_retry_last_user_persists_assistant(db_session: Session, monkeypatch) -> None:
    chat = assistant_service.create_chat(db_session)
    prepared = assistant_service.prepare_send_message_stream(
        db_session,
        chat.id,
        'Megválaszolatlan kérdés',
        settings=Settings(lm_studio_chat_model='chat-model'),
    )
    assert prepared.assistant_sequence_index == 1

    class StreamingProvider:
        def __init__(self, settings):
            self.settings = settings

        def chat_completion_stream(self, model, messages, *, temperature=None, max_tokens=None, reasoning_mode='off'):
            assert messages[-1].role == 'user'
            assert messages[-1].content == 'Megválaszolatlan kérdés'
            yield LLMStreamEvent(type='message_delta', content='retry')
            yield LLMStreamEvent(type='done', final_content='retry válasz', model='chat-model:retry')

    monkeypatch.setattr(assistant_router, 'LMStudioNativeProvider', StreamingProvider)
    app = create_app()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    response = client.post(f'/api/assistant/chats/{chat.id}/retry-last-user/stream', json={'reasoning_mode': 'normal'})

    assert response.status_code == 200
    assert 'event: done' in response.text
    persisted = assistant_service.get_chat(db_session, chat.id)
    assert [(message.role, message.sequence_index) for message in persisted.messages] == [('user', 0), ('assistant', 1)]
    assert persisted.messages[-1].content == 'retry válasz'
    assert persisted.messages[-1].model == 'chat-model:retry'


def test_assistant_api_stream_retry_last_user_rejects_answered_chat(db_session: Session) -> None:
    chat = assistant_service.create_chat(db_session)
    assistant_service.send_message(
        db_session,
        chat.id,
        'Szia',
        settings=Settings(lm_studio_chat_model='chat-model'),
        provider=FakeProvider('van válasz'),
    )
    app = create_app()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    response = client.post(f'/api/assistant/chats/{chat.id}/retry-last-user/stream', json={'reasoning_mode': 'normal'})

    assert response.status_code == 400
    persisted = assistant_service.get_chat(db_session, chat.id)
    assert [(message.role, message.sequence_index) for message in persisted.messages] == [('user', 0), ('assistant', 1)]


def test_assistant_api_stream_retry_last_user_provider_error_keeps_user_only(db_session: Session, monkeypatch) -> None:
    chat = assistant_service.create_chat(db_session)
    assistant_service.prepare_send_message_stream(
        db_session,
        chat.id,
        'Megválaszolatlan kérdés',
        settings=Settings(lm_studio_chat_model='chat-model'),
    )

    class FailingStreamingProvider:
        def __init__(self, settings):
            self.settings = settings

        def chat_completion_stream(self, *args, **kwargs):
            yield LLMStreamEvent(type='message_delta', content='fél')
            raise LLMProviderError('retry stream megszakadt')

    monkeypatch.setattr(assistant_router, 'LMStudioNativeProvider', FailingStreamingProvider)
    app = create_app()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    response = client.post(f'/api/assistant/chats/{chat.id}/retry-last-user/stream', json={'reasoning_mode': 'normal'})

    assert response.status_code == 200
    assert 'event: error' in response.text
    persisted = assistant_service.get_chat(db_session, chat.id)
    assert [(message.role, message.sequence_index) for message in persisted.messages] == [('user', 0)]



def test_assistant_api_update_unanswered_last_user_message(client: TestClient, db_session: Session) -> None:
    chat = assistant_service.create_chat(db_session)
    assistant_service.prepare_send_message_stream(
        db_session,
        chat.id,
        "Eredeti kérdés",
        settings=Settings(lm_studio_chat_model="chat-model"),
    )
    user_message = assistant_service.get_chat(db_session, chat.id).messages[-1]

    response = client.patch(
        f"/api/assistant/chats/{chat.id}/messages/{user_message.id}",
        json={"content": "  Javított kérdés  "},
    )

    assert response.status_code == 200
    persisted = assistant_service.get_chat(db_session, chat.id)
    assert [(message.role, message.sequence_index) for message in persisted.messages] == [("user", 0)]
    assert persisted.messages[0].content == "Javított kérdés"


def test_assistant_api_update_unanswered_last_user_rejects_answered_chat(client: TestClient, db_session: Session) -> None:
    chat = assistant_service.create_chat(db_session)
    assistant_service.send_message(
        db_session,
        chat.id,
        "Szia",
        settings=Settings(lm_studio_chat_model="chat-model"),
        provider=FakeProvider("van válasz"),
    )
    user_message = assistant_service.get_chat(db_session, chat.id).messages[0]

    response = client.patch(
        f"/api/assistant/chats/{chat.id}/messages/{user_message.id}",
        json={"content": "Javított kérdés"},
    )

    assert response.status_code == 400
    persisted = assistant_service.get_chat(db_session, chat.id)
    assert [(message.role, message.sequence_index) for message in persisted.messages] == [("user", 0), ("assistant", 1)]
    assert persisted.messages[0].content == "Szia"


def test_assistant_api_update_unanswered_last_user_rejects_non_latest_message(client: TestClient, db_session: Session) -> None:
    chat = assistant_service.create_chat(db_session)
    assistant_service.prepare_send_message_stream(
        db_session,
        chat.id,
        "Első válasz nélküli",
        settings=Settings(lm_studio_chat_model="chat-model"),
    )
    assistant_service.prepare_send_message_stream(
        db_session,
        chat.id,
        "Második válasz nélküli",
        settings=Settings(lm_studio_chat_model="chat-model"),
    )
    first_user = assistant_service.get_chat(db_session, chat.id).messages[0]

    response = client.patch(
        f"/api/assistant/chats/{chat.id}/messages/{first_user.id}",
        json={"content": "Nem szabad"},
    )

    assert response.status_code == 400
    persisted = assistant_service.get_chat(db_session, chat.id)
    assert persisted.messages[0].content == "Első válasz nélküli"
    assert persisted.messages[1].content == "Második válasz nélküli"


def test_assistant_api_update_unanswered_last_user_rejects_blank_content(client: TestClient, db_session: Session) -> None:
    chat = assistant_service.create_chat(db_session)
    assistant_service.prepare_send_message_stream(
        db_session,
        chat.id,
        "Eredeti kérdés",
        settings=Settings(lm_studio_chat_model="chat-model"),
    )
    user_message = assistant_service.get_chat(db_session, chat.id).messages[-1]

    response = client.patch(
        f"/api/assistant/chats/{chat.id}/messages/{user_message.id}",
        json={"content": "   "},
    )

    assert response.status_code == 400
    assert assistant_service.get_chat(db_session, chat.id).messages[-1].content == "Eredeti kérdés"


def test_update_unanswered_last_user_rejects_context_overflow(db_session: Session) -> None:
    chat = assistant_service.create_chat(db_session)
    assistant_service.prepare_send_message_stream(
        db_session,
        chat.id,
        "Eredeti kérdés",
        settings=Settings(lm_studio_chat_model="chat-model"),
    )
    user_message = assistant_service.get_chat(db_session, chat.id).messages[-1]

    with pytest.raises(assistant_service.AssistantContextLimitError):
        assistant_service.update_unanswered_last_user_message(
            db_session,
            chat.id,
            user_message.id,
            "Ez már biztosan túl hosszú ehhez a teszt budgethez",
            settings=Settings(assistant_context_char_budget=1),
        )

    assert assistant_service.get_chat(db_session, chat.id).messages[-1].content == "Eredeti kérdés"
