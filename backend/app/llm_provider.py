from dataclasses import dataclass
from collections.abc import Iterable, Iterator
from typing import Any

import httpx
import json

from app.config import Settings, get_settings


class LLMProviderError(RuntimeError):
    pass


class LLMModelAlreadyLoadedError(LLMProviderError):
    pass


@dataclass(frozen=True)
class LLMModel:
    id: str


@dataclass(frozen=True)
class LLMChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMChatCompletion:
    model: str
    content: str


@dataclass(frozen=True)
class LLMStreamEvent:
    type: str
    content: str | None = None
    error_message: str | None = None
    final_content: str | None = None
    model: str | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class LLMSmokeResult:
    provider: str
    base_url: str
    reachable: bool
    model_ids: list[str]
    configured_chat_model: str
    selected_chat_model: str
    configured_chat_model_available: bool | None
    configured_chat_model_loaded: bool | None
    selected_chat_model_available: bool | None
    selected_chat_model_loaded: bool | None
    loaded_model_ids: list[str]
    error_message: str | None = None


@dataclass(frozen=True)
class LLMModelLoadResult:
    type: str
    instance_id: str
    load_time_seconds: float | None
    status: str
    load_config: dict[str, Any] | None


@dataclass(frozen=True)
class LLMModelUnloadResult:
    instance_id: str


class LMStudioNativeProvider:
    provider_name = "lm_studio_native"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client
        self._loaded_chat_model_instance_id: str | None = None

    def list_models(self) -> list[LLMModel]:
        model_ids, _ = self._read_model_catalog()
        return [LLMModel(id=model_id) for model_id in model_ids]

    def smoke_check(self, selected_chat_model: str | None = None) -> LLMSmokeResult:
        configured_model = self._settings.lm_studio_chat_model
        selected_model = selected_chat_model or configured_model
        try:
            models = self.list_models()
            model_ids = [model.id for model in models]
            loaded_model_ids = self.loaded_model_instance_ids()
            return LLMSmokeResult(
                provider=self.provider_name,
                base_url=self._native_base_url,
                reachable=True,
                model_ids=model_ids,
                configured_chat_model=configured_model,
                selected_chat_model=selected_model,
                configured_chat_model_available=_model_available(configured_model, model_ids),
                configured_chat_model_loaded=_model_loaded(configured_model, loaded_model_ids),
                selected_chat_model_available=_model_available(selected_model, model_ids),
                selected_chat_model_loaded=_model_loaded(selected_model, loaded_model_ids),
                loaded_model_ids=loaded_model_ids,
            )
        except LLMProviderError as exc:
            return LLMSmokeResult(
                provider=self.provider_name,
                base_url=self._native_base_url,
                reachable=False,
                model_ids=[],
                configured_chat_model=configured_model,
                selected_chat_model=selected_model,
                configured_chat_model_available=None,
                configured_chat_model_loaded=None,
                selected_chat_model_available=None,
                selected_chat_model_loaded=None,
                loaded_model_ids=[],
                error_message=str(exc),
            )

    def loaded_model_instance_ids(self) -> list[str]:
        _, instance_ids = self._read_model_catalog()
        return instance_ids

    def ensure_chat_model_loaded(self, model_id: str) -> str:
        instance_id = self._matching_loaded_instance_id(model_id, self._loaded_chat_model_instance_id)
        if instance_id is not None:
            self._loaded_chat_model_instance_id = instance_id
            return instance_id
        result = self._load_chat_model_unchecked(model_id)
        if result.status != "loaded" or result.instance_id == "":
            raise LLMProviderError("LM Studio did not return a loaded chat model instance")
        self._loaded_chat_model_instance_id = result.instance_id
        return result.instance_id

    def ensure_configured_chat_model_loaded(self) -> str:
        return self.ensure_chat_model_loaded(self._settings.lm_studio_chat_model)

    def load_chat_model(self, model_id: str) -> LLMModelLoadResult:
        if model_id.strip() == "":
            raise LLMProviderError("Chat model id is required")
        if self._matching_loaded_instance_id(model_id, self._loaded_chat_model_instance_id) is not None:
            raise LLMModelAlreadyLoadedError("Chat model is already loaded")
        return self._load_chat_model_unchecked(model_id)

    def load_configured_chat_model(self) -> LLMModelLoadResult:
        return self.load_chat_model(self._settings.lm_studio_chat_model)

    def unload_chat_model(self, model_id: str) -> LLMModelUnloadResult:
        instance_id = self._matching_loaded_instance_id(model_id, self._loaded_chat_model_instance_id)
        if instance_id is None:
            raise LLMProviderError("Chat model is not loaded")
        result = self.unload_model_instance(instance_id)
        if self._loaded_chat_model_instance_id == instance_id:
            self._loaded_chat_model_instance_id = None
        return result

    def unload_configured_chat_model(self) -> LLMModelUnloadResult:
        return self.unload_chat_model(self._settings.lm_studio_chat_model)

    def unload_model_instance(self, instance_id: str) -> LLMModelUnloadResult:
        if instance_id.strip() == "":
            raise LLMProviderError("Model instance id is required")
        client = self._client or self._build_client()
        close_client = self._client is None
        try:
            response = client.post("/api/v1/models/unload", json={"instance_id": instance_id})
            response.raise_for_status()
            payload = response.json()
            unloaded_instance_id = str(payload.get("instance_id", ""))
            if unloaded_instance_id == "":
                raise LLMProviderError("LM Studio did not return an unloaded model instance id")
            return LLMModelUnloadResult(instance_id=unloaded_instance_id)
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(_http_status_error_message(exc)) from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise LLMProviderError(str(exc)) from exc
        finally:
            if close_client:
                client.close()

    def chat_completion(
        self,
        model: str,
        messages: list[LLMChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_mode: str | None = "off",
        integrations: list[str] | None = None,
    ) -> LLMChatCompletion:
        client = self._client or self._build_client()
        close_client = self._client is None
        try:
            chat_model = self.ensure_chat_model_loaded(model) if self._settings.lm_studio_auto_load_chat_model else model
            payload = self._build_chat_payload(
                chat_model,
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                reasoning_mode=reasoning_mode,
                integrations=integrations,
            )

            response = client.post("/api/v1/chat", json=payload)
            response.raise_for_status()
            response_payload = response.json()
            content = _message_content_from_native_chat_response(response_payload)
            return LLMChatCompletion(model=chat_model, content=content)
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(_http_status_error_message(exc)) from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise LLMProviderError(str(exc)) from exc
        finally:
            if close_client:
                client.close()

    def chat_completion_stream(
        self,
        model: str,
        messages: list[LLMChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_mode: str | None = "off",
        integrations: list[str] | None = None,
    ) -> Iterator[LLMStreamEvent]:
        client = self._client or self._build_client()
        close_client = self._client is None
        try:
            chat_model = self.ensure_chat_model_loaded(model) if self._settings.lm_studio_auto_load_chat_model else model
            payload = self._build_chat_payload(
                chat_model,
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                reasoning_mode=reasoning_mode,
                integrations=integrations,
            )
            payload["stream"] = True

            with client.stream("POST", "/api/v1/chat", json=payload) as response:
                response.raise_for_status()
                for event_name, event_data in _iter_sse_events(response.iter_lines()):
                    stream_event = _native_chat_stream_event(event_name, event_data, chat_model)
                    if stream_event is not None:
                        yield stream_event
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(_http_status_error_message(exc)) from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise LLMProviderError(str(exc)) from exc
        finally:
            if close_client:
                client.close()

    def _build_chat_payload(
        self,
        chat_model: str,
        messages: list[LLMChatMessage],
        *,
        temperature: float | None,
        max_tokens: int | None,
        reasoning_mode: str | None,
        integrations: list[str] | None,
    ) -> dict[str, Any]:
        system_prompt, user_messages = _split_system_prompt(messages)
        payload: dict[str, Any] = {
            "model": chat_model,
            "input": [{"type": "text", "content": _messages_to_native_input(user_messages)}],
            "system_prompt": system_prompt,
            "temperature": temperature if temperature is not None else self._settings.lm_studio_default_temperature,
            "store": False,
        }
        output_limit = max_tokens if max_tokens is not None else self._settings.lm_studio_default_max_output_tokens
        if output_limit is not None:
            payload["max_output_tokens"] = output_limit
        if reasoning_mode not in {None, "off", "model_default"}:
            raise LLMProviderError(f"Unsupported reasoning mode: {reasoning_mode}")
        if reasoning_mode == "off" and _supports_native_reasoning_toggle(chat_model):
            payload["reasoning"] = "off"
        if integrations:
            payload["integrations"] = integrations
        return payload

    def _load_chat_model_unchecked(self, model_id: str) -> LLMModelLoadResult:
        client = self._client or self._build_client()
        close_client = self._client is None
        try:
            response = client.post(
                "/api/v1/models/load",
                json={
                    "model": model_id,
                    "context_length": self._settings.lm_studio_chat_context_length,
                    "eval_batch_size": self._settings.lm_studio_eval_batch_size,
                    "flash_attention": self._settings.lm_studio_flash_attention,
                    "offload_kv_cache_to_gpu": self._settings.lm_studio_offload_kv_cache_to_gpu,
                    "echo_load_config": True,
                },
            )
            response.raise_for_status()
            payload = response.json()
            return LLMModelLoadResult(
                type=str(payload.get("type", "")),
                instance_id=str(payload.get("instance_id", "")),
                load_time_seconds=_optional_float(payload.get("load_time_seconds")),
                status=str(payload.get("status", "")),
                load_config=payload.get("load_config") if isinstance(payload.get("load_config"), dict) else None,
            )
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(_http_status_error_message(exc)) from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise LLMProviderError(str(exc)) from exc
        finally:
            if close_client:
                client.close()

    def _matching_loaded_instance_id(self, model_id: str, cached_instance_id: str | None) -> str | None:
        instance_ids = self.loaded_model_instance_ids()
        if cached_instance_id in instance_ids and _is_instance_of_model(str(cached_instance_id), model_id):
            return cached_instance_id
        if model_id in instance_ids:
            return model_id
        for instance_id in instance_ids:
            if _is_instance_of_model(instance_id, model_id):
                return instance_id
        return None

    def _read_model_catalog(self) -> tuple[list[str], list[str]]:
        client = self._client or self._build_client()
        close_client = self._client is None
        try:
            response = client.get("/api/v1/models")
            response.raise_for_status()
            payload = response.json()
            models = payload.get("models")
            if not isinstance(models, list):
                raise LLMProviderError("LM Studio native API returned an invalid models payload")
            model_ids: list[str] = []
            instance_ids: list[str] = []
            for item in models:
                if not isinstance(item, dict):
                    continue
                if item.get("key"):
                    model_ids.append(str(item["key"]))
                loaded_instances = item.get("loaded_instances")
                if isinstance(loaded_instances, list):
                    instance_ids.extend(
                        str(instance["id"])
                        for instance in loaded_instances
                        if isinstance(instance, dict) and instance.get("id")
                    )
            return _dedupe(model_ids), _dedupe(instance_ids)
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(_http_status_error_message(exc)) from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise LLMProviderError(str(exc)) from exc
        finally:
            if close_client:
                client.close()

    def _build_client(self) -> httpx.Client:
        headers = {}
        if self._settings.lm_studio_api_token is not None:
            headers["Authorization"] = f"Bearer {self._settings.lm_studio_api_token}"
        return httpx.Client(
            base_url=self._native_base_url,
            timeout=self._settings.lm_studio_request_timeout_seconds,
            headers=headers,
        )

    @property
    def _native_base_url(self) -> str:
        return self._settings.lm_studio_base_url.rstrip("/").removesuffix("/v1")


def _model_available(model_id: str, model_ids: list[str]) -> bool | None:
    if model_id == "":
        return None
    return model_id in model_ids


def _model_loaded(model_id: str, loaded_model_ids: list[str]) -> bool | None:
    if model_id == "":
        return None
    return any(_is_instance_of_model(instance_id, model_id) for instance_id in loaded_model_ids)


def _messages_to_native_input(messages: list[LLMChatMessage]) -> str:
    return "\n\n".join(f"{message.role.upper()}:\n{message.content}" for message in messages)


def _message_content_from_native_chat_response(payload: dict[str, Any]) -> str:
    output = payload.get("output")
    if not isinstance(output, list) or not output:
        raise LLMProviderError("LM Studio native API returned no output")
    content_parts = [
        str(item["content"])
        for item in output
        if isinstance(item, dict) and item.get("type") == "message" and isinstance(item.get("content"), str)
    ]
    if not content_parts:
        raise LLMProviderError("LM Studio native API returned no message content")
    return "\n".join(content_parts)


def _iter_sse_events(lines: Iterable[str]) -> Iterator[tuple[str | None, dict[str, Any]]]:
    event_name: str | None = None
    data_lines: list[str] = []
    for raw_line in lines:
        line = raw_line.rstrip("\r")
        if line == "":
            if data_lines:
                yield event_name, _json_object_from_sse_data("\n".join(data_lines))
            event_name = None
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        field, separator, value = line.partition(":")
        if separator == "":
            continue
        if value.startswith(" "):
            value = value[1:]
        if field == "event":
            event_name = value
        elif field == "data":
            data_lines.append(value)
    if data_lines:
        yield event_name, _json_object_from_sse_data("\n".join(data_lines))


def _json_object_from_sse_data(data: str) -> dict[str, Any]:
    payload = json.loads(data)
    if not isinstance(payload, dict):
        raise LLMProviderError("LM Studio native API returned a non-object stream event")
    return payload


def _native_chat_stream_event(
    event_name: str | None,
    payload: dict[str, Any],
    fallback_model: str,
) -> LLMStreamEvent | None:
    event_type = str(payload.get("type") or event_name or "")
    if event_type == "message.delta":
        content = payload.get("content")
        return LLMStreamEvent(type="message_delta", content=str(content) if isinstance(content, str) else "", raw=payload)
    if event_type == "reasoning.delta":
        content = payload.get("content")
        return LLMStreamEvent(type="reasoning_delta", content=str(content) if isinstance(content, str) else "", raw=payload)
    if event_type == "error":
        error = payload.get("error")
        message = str(error.get("message", "LM Studio streaming error")) if isinstance(error, dict) else "LM Studio streaming error"
        return LLMStreamEvent(type="error", error_message=message, raw=payload)
    if event_type == "chat.end":
        result = payload.get("result")
        if not isinstance(result, dict):
            raise LLMProviderError("LM Studio native API returned an invalid chat.end event")
        return LLMStreamEvent(
            type="done",
            final_content=_message_content_from_native_chat_response(result),
            model=str(result.get("model_instance_id") or fallback_model),
            raw=payload,
        )
    if event_type in {
        "chat.start",
        "model_load.start",
        "model_load.progress",
        "model_load.end",
        "prompt_processing.start",
        "prompt_processing.progress",
        "prompt_processing.end",
        "reasoning.start",
        "reasoning.end",
        "message.start",
        "message.end",
    }:
        return LLMStreamEvent(type="status", raw=payload)
    return None


def _split_system_prompt(messages: list[LLMChatMessage]) -> tuple[str, list[LLMChatMessage]]:
    system_messages = [message.content for message in messages if message.role == "system"]
    user_messages = [message for message in messages if message.role != "system"]
    return "\n\n".join(system_messages), user_messages


def _supports_native_reasoning_toggle(model: str) -> bool:
    return "qwen" in model.casefold()


def _is_instance_of_model(instance_id: str, model_id: str) -> bool:
    return instance_id == model_id or instance_id.startswith(f"{model_id}:")


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _http_status_error_message(exc: httpx.HTTPStatusError) -> str:
    detail = exc.response.text.strip()
    if detail:
        return f"{exc.response.status_code} {exc.response.reason_phrase}: {detail}"
    return str(exc)
