from dataclasses import dataclass
from collections.abc import Iterable, Iterator
from typing import Any, Protocol

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


class LLMProvider(Protocol):
    provider_name: str

    def list_models(self) -> list[LLMModel]: ...

    def smoke_check(self, selected_chat_model: str | None = None) -> LLMSmokeResult: ...

    def loaded_model_instance_ids(self) -> list[str]: ...

    def ensure_chat_model_loaded(self, model_id: str) -> str: ...

    def load_chat_model(self, model_id: str) -> LLMModelLoadResult: ...

    def load_configured_chat_model(self) -> LLMModelLoadResult: ...

    def unload_chat_model(self, model_id: str) -> LLMModelUnloadResult: ...

    def unload_configured_chat_model(self) -> LLMModelUnloadResult: ...

    def unload_model_instance(self, instance_id: str) -> LLMModelUnloadResult: ...

    def chat_completion(
        self,
        model: str,
        messages: list[LLMChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_mode: str | None = "off",
        integrations: list[str] | None = None,
    ) -> LLMChatCompletion: ...

    def chat_completion_stream(
        self,
        model: str,
        messages: list[LLMChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_mode: str | None = "off",
        integrations: list[str] | None = None,
    ) -> Iterator[LLMStreamEvent]: ...


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
            chat_model = _require_model_id(model)
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
            chat_model = _require_model_id(model)
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


class LMStudioResponsesProvider:
    provider_name = "lm_studio_responses"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client

    def list_models(self) -> list[LLMModel]:
        client = self._client or self._build_client()
        close_client = self._client is None
        try:
            response = client.get("/v1/models")
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data")
            if not isinstance(data, list):
                raise LLMProviderError("LM Studio Responses API returned an invalid models payload")
            return [LLMModel(id=str(item["id"])) for item in data if isinstance(item, dict) and item.get("id")]
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(_http_status_error_message(exc)) from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise LLMProviderError(str(exc)) from exc
        finally:
            if close_client:
                client.close()

    def smoke_check(self, selected_chat_model: str | None = None) -> LLMSmokeResult:
        configured_model = self._settings.lm_studio_chat_model
        selected_model = selected_chat_model or configured_model
        try:
            models = self.list_models()
            model_ids = [model.id for model in models]
            loaded_model_ids = self.loaded_model_instance_ids()
            return LLMSmokeResult(
                provider=self.provider_name,
                base_url=self._responses_base_url,
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
                base_url=self._responses_base_url,
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
        if self._client is not None:
            try:
                response = self._client.get("/api/v1/models")
                response.raise_for_status()
                _, instance_ids = _native_model_catalog_from_payload(response.json())
                return instance_ids
            except httpx.HTTPStatusError as exc:
                raise LLMProviderError(_http_status_error_message(exc)) from exc
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                raise LLMProviderError(str(exc)) from exc
        _, instance_ids = _read_native_model_catalog(self._settings)
        return instance_ids

    def ensure_chat_model_loaded(self, model_id: str) -> str:
        return _require_model_id(model_id)

    def load_chat_model(self, model_id: str) -> LLMModelLoadResult:
        raise LLMProviderError("Model load is not supported by provider lm_studio_responses")

    def load_configured_chat_model(self) -> LLMModelLoadResult:
        return self.load_chat_model(self._settings.lm_studio_chat_model)

    def unload_chat_model(self, model_id: str) -> LLMModelUnloadResult:
        raise LLMProviderError("Model unload is not supported by provider lm_studio_responses")

    def unload_configured_chat_model(self) -> LLMModelUnloadResult:
        return self.unload_chat_model(self._settings.lm_studio_chat_model)

    def unload_model_instance(self, instance_id: str) -> LLMModelUnloadResult:
        raise LLMProviderError("Model unload is not supported by provider lm_studio_responses")

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
        if reasoning_mode not in {None, "off", "model_default"}:
            raise LLMProviderError(f"Unsupported reasoning mode: {reasoning_mode}")

        client = self._client or self._build_client()
        close_client = self._client is None
        try:
            chat_model = self.ensure_chat_model_loaded(model)
            payload = self._build_responses_payload(
                chat_model,
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                reasoning_mode=reasoning_mode,
                integrations=integrations,
            )
            response = client.post("/v1/responses", json=payload)
            response.raise_for_status()
            response_payload = response.json()
            return LLMChatCompletion(model=chat_model, content=_message_content_from_responses_response(response_payload))
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
        if reasoning_mode not in {None, "off", "model_default"}:
            raise LLMProviderError(f"Unsupported reasoning mode: {reasoning_mode}")

        client = self._client or self._build_client()
        close_client = self._client is None
        try:
            chat_model = self.ensure_chat_model_loaded(model)
            payload = self._build_responses_payload(
                chat_model,
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                reasoning_mode=reasoning_mode,
                integrations=integrations,
            )
            payload["stream"] = True

            with client.stream("POST", "/v1/responses", json=payload) as response:
                response.raise_for_status()
                for event_name, event_data in _iter_sse_events(response.iter_lines()):
                    stream_event = _responses_stream_event(event_name, event_data, chat_model)
                    if stream_event is not None:
                        yield stream_event
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(_http_status_error_message(exc)) from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise LLMProviderError(str(exc)) from exc
        finally:
            if close_client:
                client.close()

    def _build_responses_payload(
        self,
        model: str,
        messages: list[LLMChatMessage],
        *,
        temperature: float | None,
        max_tokens: int | None,
        reasoning_mode: str | None,
        integrations: list[str] | None,
    ) -> dict[str, Any]:
        system_prompt, user_messages = _split_system_prompt(messages)
        payload: dict[str, Any] = {
            "model": model,
            "input": _messages_to_responses_input(user_messages),
            "temperature": temperature if temperature is not None else self._settings.lm_studio_default_temperature,
            "store": False,
        }
        if system_prompt:
            payload["instructions"] = system_prompt
        if reasoning_mode == "off":
            payload["reasoning"] = {"effort": "none"}
        tools = self._responses_mcp_tools(integrations)
        if tools:
            payload["tools"] = tools
        output_limit = max_tokens if max_tokens is not None else self._settings.lm_studio_default_max_output_tokens
        if output_limit is not None:
            payload["max_output_tokens"] = output_limit
        return payload

    def _responses_mcp_tools(self, integrations: list[str] | None) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for integration_id in integrations or []:
            if integration_id == self._settings.lm_studio_excel_integration_id:
                tools.append(_responses_excel_mcp_tool(self._settings))
            elif integration_id == self._settings.lm_studio_obsidian_integration_id:
                tools.append(_responses_obsidian_mcp_tool(self._settings))
            else:
                raise LLMProviderError(f"Unsupported Responses MCP integration: {integration_id}")
        return tools

    def _build_client(self) -> httpx.Client:
        headers = {}
        if self._settings.lm_studio_api_token is not None:
            headers["Authorization"] = f"Bearer {self._settings.lm_studio_api_token}"
        return httpx.Client(
            base_url=self._responses_base_url,
            timeout=self._settings.lm_studio_request_timeout_seconds,
            headers=headers,
        )

    @property
    def _responses_base_url(self) -> str:
        return self._settings.lm_studio_base_url.rstrip("/").removesuffix("/v1")


RESPONSES_EXCEL_ALLOWED_TOOLS = (
    "get_workbook_metadata",
    "list_excel_sheets",
    "list_excel_columns",
    "read_data_from_excel",
    "describe_excel_sheet",
    "detect_header_row",
    "find_relevant_column",
    "lookup_excel_rows",
    "filter_excel_rows",
    "find_excel_rows_with_same_value",
    "aggregate_excel_data",
)


def _responses_excel_mcp_tool(settings: Settings) -> dict[str, Any]:
    server_url = settings.lm_studio_responses_excel_mcp_url
    if server_url is None:
        raise LLMProviderError("Responses Excel MCP URL is not configured")
    return {
        "type": "mcp",
        "server_label": "excel",
        "server_url": server_url,
        "allowed_tools": list(RESPONSES_EXCEL_ALLOWED_TOOLS),
    }


def _responses_obsidian_mcp_tool(settings: Settings) -> dict[str, Any]:
    server_url = settings.lm_studio_responses_obsidian_mcp_url
    if server_url is None:
        raise LLMProviderError("Responses Obsidian MCP URL is not configured")
    tool: dict[str, Any] = {
        "type": "mcp",
        "server_label": "obsidian",
        "server_url": server_url,
    }
    if settings.lm_studio_responses_obsidian_mcp_token is not None:
        tool["headers"] = {
            "Authorization": f"Bearer {settings.lm_studio_responses_obsidian_mcp_token}",
        }
    return tool


def _read_native_model_catalog(settings: Settings) -> tuple[list[str], list[str]]:
    headers = {}
    if settings.lm_studio_api_token is not None:
        headers["Authorization"] = f"Bearer {settings.lm_studio_api_token}"
    with httpx.Client(
        base_url=settings.lm_studio_base_url.rstrip("/").removesuffix("/v1"),
        timeout=settings.lm_studio_request_timeout_seconds,
        headers=headers,
    ) as client:
        try:
            response = client.get("/api/v1/models")
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(_http_status_error_message(exc)) from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise LLMProviderError(str(exc)) from exc

    return _native_model_catalog_from_payload(payload)


def _native_model_catalog_from_payload(payload: dict[str, Any]) -> tuple[list[str], list[str]]:
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


def _require_model_id(model_id: str) -> str:
    normalized = model_id.strip()
    if normalized == "":
        raise LLMProviderError("Chat model id is required")
    return normalized


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    resolved_settings = settings or get_settings()
    provider_name = resolved_settings.llm_provider.strip()
    if provider_name == "lm_studio_native":
        return LMStudioNativeProvider(resolved_settings)
    if provider_name == "lm_studio_responses":
        return LMStudioResponsesProvider(resolved_settings)
    raise LLMProviderError(f"Unsupported LLM provider: {provider_name}")


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


def _messages_to_responses_input(messages: list[LLMChatMessage]) -> list[dict[str, Any]]:
    return [
        {
            "role": message.role,
            "content": [{"type": _responses_content_type_for_role(message.role), "text": message.content}],
        }
        for message in messages
    ]


def _responses_content_type_for_role(role: str) -> str:
    if role == "assistant":
        return "output_text"
    return "input_text"


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


def _message_content_from_responses_response(payload: dict[str, Any]) -> str:
    output = payload.get("output")
    if not isinstance(output, list) or not output:
        raise LLMProviderError("LM Studio Responses API returned no output")
    content_parts: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if isinstance(content, str):
            content_parts.append(content)
        elif isinstance(content, list):
            content_parts.extend(
                str(part["text"])
                for part in content
                if isinstance(part, dict)
                and part.get("type") in {"output_text", "text"}
                and isinstance(part.get("text"), str)
            )
    if not content_parts:
        raise LLMProviderError("LM Studio Responses API returned no message content")
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


def _responses_stream_event(
    event_name: str | None,
    payload: dict[str, Any],
    fallback_model: str,
) -> LLMStreamEvent | None:
    event_type = str(payload.get("type") or event_name or "")
    if event_type == "response.output_text.delta":
        return LLMStreamEvent(type="message_delta", content=_responses_delta_text(payload), raw=payload)
    if event_type == "response.reasoning_text.delta":
        return LLMStreamEvent(type="reasoning_delta", content=_responses_delta_text(payload), raw=payload)
    if event_type == "response.completed":
        response_payload = _responses_event_response_payload(payload)
        return LLMStreamEvent(
            type="done",
            final_content=_message_content_from_responses_response(response_payload),
            model=str(response_payload.get("model") or fallback_model),
            raw=payload,
        )
    if event_type in {"response.failed", "response.incomplete"}:
        return LLMStreamEvent(type="error", error_message=_responses_error_message(payload), raw=payload)
    if event_type in {"response.output_item.added", "response.output_item.done"}:
        tool_activity_text = _responses_output_item_tool_activity_text(event_type, payload)
        if tool_activity_text is not None:
            return LLMStreamEvent(type="tool_activity", content=tool_activity_text, raw=payload)
        return LLMStreamEvent(type="status", raw=payload)
    if event_type.startswith("response.mcp_list_tools.") or event_type.startswith("response.mcp_call"):
        return LLMStreamEvent(type="status", raw=payload)
    if event_type in {
        "response.created",
        "response.in_progress",
        "response.content_part.added",
        "response.content_part.done",
    }:
        return LLMStreamEvent(type="status", raw=payload)
    return None


def _responses_output_item_tool_activity_text(event_type: str, payload: dict[str, Any]) -> str | None:
    item = payload.get("item")
    if not isinstance(item, dict):
        return None
    item_type = item.get("type")
    if item_type not in {"mcp_list_tools", "mcp_call"}:
        return None

    server_label = _first_string(item, "server_label", "server") or _first_string(payload, "server_label", "server")
    server_name = _tool_activity_server_name(server_label)
    event_status = "done" if event_type.endswith(".done") else "added"

    if item_type == "mcp_list_tools":
        if event_status == "done":
            return f"- **{server_name} eszközlista elérhető**"
        return f"- *{server_name} eszközlista lekérése*"

    tool_name = _first_string(item, "name", "tool_name", "tool") or "ismeretlen eszköz"
    if event_status != "done":
        return f"- *{server_name} eszköz indult:* `{tool_name}`"

    arguments = _json_object_from_maybe_json_string(item.get("arguments"))
    output_summary = _responses_tool_output_summary(item.get("output"))
    lines = [f"- **{server_name} eszköz:** `{tool_name}`"]
    lines.extend(_responses_tool_argument_summary(arguments))
    if output_summary:
        lines.append(output_summary)
    return "\n".join(lines)


def _tool_activity_server_name(server_label: str | None) -> str:
    if not server_label:
        return "MCP"
    if server_label.lower() == "excel":
        return "Excel"
    if server_label.lower() == "obsidian":
        return "Tudásbázis"
    return server_label


def _responses_tool_argument_summary(arguments: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    filepath = _string_value(arguments.get("filepath"))
    sheet_name = _string_value(arguments.get("sheet_name"))
    if filepath and sheet_name:
        lines.append(f"  - Fájl: `{filepath}`, munkalap: `{sheet_name}`")
    elif filepath:
        lines.append(f"  - Fájl: `{filepath}`")
    elif sheet_name:
        lines.append(f"  - Munkalap: `{sheet_name}`")

    lookup_column = _string_value(arguments.get("lookup_column"))
    lookup_value = _string_value(arguments.get("lookup_value"))
    filter_column = _string_value(arguments.get("filter_column"))
    filter_value = _string_value(arguments.get("filter_value"))
    search_term = _string_value(arguments.get("search_term"))
    group_by = _string_value(arguments.get("group_by"))
    metric_column = _string_value(arguments.get("metric_column")) or _string_value(arguments.get("value_column"))
    operation = _string_value(arguments.get("operation")) or _string_value(arguments.get("aggregation"))

    if lookup_column and lookup_value:
        match_mode = _string_value(arguments.get("match_mode"))
        suffix = " (részszöveg)" if match_mode == "contains" else ""
        lines.append(f"  - Keresés: `{lookup_column} = {lookup_value}`{suffix}")
    elif filter_column and filter_value:
        lines.append(f"  - Szűrés: `{filter_column} = {filter_value}`")
    elif search_term:
        intent = _string_value(arguments.get("search_intent"))
        suffix = f" ({intent})" if intent else ""
        lines.append(f"  - Oszlopkeresés: `{search_term}`{suffix}")

    if group_by and metric_column:
        operation_label = operation or "összesítés"
        lines.append(f"  - Összesítés: `{operation_label}`, csoport: `{group_by}`, mező: `{metric_column}`")
    elif group_by:
        lines.append(f"  - Csoportosítás: `{group_by}`")

    start_cell = _string_value(arguments.get("start_cell"))
    end_cell = _string_value(arguments.get("end_cell"))
    if start_cell and end_cell:
        lines.append(f"  - Tartomány: `{start_cell}:{end_cell}`")
    elif start_cell:
        lines.append(f"  - Tartomány kezdete: `{start_cell}`")
    return lines


def _responses_tool_output_summary(output: Any) -> str | None:
    text_payload = _responses_tool_output_text(output)
    if text_payload is None:
        return None
    parsed = _json_object_from_maybe_json_string(text_payload)
    if not parsed:
        return None

    matches = _int_value(parsed.get("matches"))
    if matches is not None:
        return f"  - Találat: **{matches} sor**"
    row_count = _int_value(parsed.get("row_count"))
    used_range = _string_value(parsed.get("used_range"))
    if row_count is not None and used_range:
        return f"  - Tábla: **{row_count} sor**, tartomány: `{used_range}`"
    if row_count is not None:
        return f"  - Tábla: **{row_count} sor**"
    recommended_header_row = _int_value(parsed.get("recommended_header_row")) or _int_value(parsed.get("detected_header_row"))
    confidence = _string_value(parsed.get("confidence")) or _string_value(parsed.get("header_confidence"))
    if recommended_header_row is not None and confidence:
        return f"  - Fejlécsor: **{recommended_header_row}**, biztosság: `{confidence}`"
    if recommended_header_row is not None:
        return f"  - Fejlécsor: **{recommended_header_row}**"
    best_column = _string_value(parsed.get("best_column"))
    if best_column:
        if confidence:
            return f"  - Javasolt oszlop: `{best_column}`, biztosság: `{confidence}`"
        return f"  - Javasolt oszlop: `{best_column}`"
    return None


def _responses_tool_output_text(output: Any) -> str | None:
    if isinstance(output, str):
        parsed = _json_value_from_string(output)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    return item["text"]
        return output
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                return item["text"]
    return None


def _json_object_from_maybe_json_string(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    parsed = _json_value_from_string(value)
    return parsed if isinstance(parsed, dict) else {}


def _json_value_from_string(value: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, int | float) and not isinstance(value, bool):
        return str(value)
    return None


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _first_string(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _responses_delta_text(payload: dict[str, Any]) -> str:
    delta = payload.get("delta")
    if isinstance(delta, str):
        return delta
    text = payload.get("text")
    return str(text) if isinstance(text, str) else ""


def _responses_event_response_payload(payload: dict[str, Any]) -> dict[str, Any]:
    response_payload = payload.get("response")
    if isinstance(response_payload, dict):
        return response_payload
    return payload


def _responses_error_message(payload: dict[str, Any]) -> str:
    response_payload = _responses_event_response_payload(payload)
    error = response_payload.get("error") or payload.get("error")
    if isinstance(error, dict):
        message = error.get("message") or error.get("code")
        if isinstance(message, str) and message.strip():
            return message
    if isinstance(error, str) and error.strip():
        return error
    status = response_payload.get("status") or payload.get("status")
    if isinstance(status, str) and status.strip():
        return f"LM Studio Responses API stream ended with status: {status}"
    return "LM Studio Responses API streaming error"


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
    try:
        detail = exc.response.text.strip()
    except httpx.ResponseNotRead:
        exc.response.read()
        detail = exc.response.text.strip()
    if detail:
        return f"{exc.response.status_code} {exc.response.reason_phrase}: {detail}"
    return str(exc)
