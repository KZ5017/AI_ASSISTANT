from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Local AI Assistant"
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    database_url: str = "postgresql+psycopg://ai_assistant:ai_assistant@localhost:5432/ai_assistant"

    llm_provider: str = "lm_studio_native"

    lm_studio_base_url: str = "http://127.0.0.1:1234"
    lm_studio_chat_model: str = "qwen/qwen3.5-9b"
    lm_studio_request_timeout_seconds: float = 180.0
    lm_studio_chat_context_length: int = 61_440
    lm_studio_eval_batch_size: int = 512
    lm_studio_flash_attention: bool = True
    lm_studio_offload_kv_cache_to_gpu: bool = True
    lm_studio_default_temperature: float = 0.1
    lm_studio_default_max_output_tokens: int | None = None
    lm_studio_api_token: str | None = None
    lm_studio_obsidian_integration_id: str = "mcp/obsidian"
    lm_studio_excel_integration_id: str = "mcp/excel"
    lm_studio_responses_obsidian_mcp_url: str | None = None
    lm_studio_responses_obsidian_mcp_token: str | None = None
    lm_studio_responses_excel_mcp_url: str | None = "http://127.0.0.1:8017/mcp"

    graphrag_base_url: str | None = "http://127.0.0.1:8080"
    graphrag_service_token: SecretStr | None = None
    graphrag_request_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    graphrag_result_limit: int = Field(default=10, ge=1, le=50)
    graphrag_context_char_budget: int = Field(default=60_000, ge=1_000)
    graphrag_max_response_bytes: int = Field(default=2_097_152, ge=1_024)
    graphrag_vault_id: str | None = None

    sensitive_request_guard_enabled: bool = True
    sensitive_output_guard_enabled: bool = True

    assistant_chat_delete_mode: Literal["hard", "soft"] = Field(
        default="hard",
        validation_alias=AliasChoices(
            "AI_ASSISTANT_CHAT_DELETE_MODE",
            "AI_ASSISTANT_ASSISTANT_CHAT_DELETE_MODE",
        ),
    )
    assistant_context_char_budget: int = Field(
        default=120_000,
        validation_alias=AliasChoices(
            "AI_ASSISTANT_CONTEXT_CHAR_BUDGET",
            "AI_ASSISTANT_ASSISTANT_CONTEXT_CHAR_BUDGET",
        ),
    )
    assistant_system_prompt: str = Field(
        default="You are a helpful local AI assistant.",
        validation_alias=AliasChoices(
            "AI_ASSISTANT_SYSTEM_PROMPT",
            "AI_ASSISTANT_ASSISTANT_SYSTEM_PROMPT",
        ),
    )

    @field_validator(
        "lm_studio_default_max_output_tokens",
        "lm_studio_api_token",
        "lm_studio_responses_obsidian_mcp_url",
        "lm_studio_responses_obsidian_mcp_token",
        "lm_studio_responses_excel_mcp_url",
        "graphrag_base_url",
        "graphrag_service_token",
        "graphrag_vault_id",
        mode="before",
    )
    @classmethod
    def _empty_values_as_none(cls, value):
        if value == "":
            return None
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_ASSISTANT_",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
