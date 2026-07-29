from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
import unicodedata
from urllib.parse import unquote

from pydantic import SecretStr
from sqlalchemy.engine import make_url

from app.config import Settings

SENSITIVE_REQUEST_BLOCK_CODE = "sensitive_request_blocked"
SENSITIVE_OUTPUT_BLOCK_CODE = "sensitive_output_blocked"
SENSITIVE_REQUEST_BLOCK_MESSAGE = (
    "Ezt a belső rendszer- vagy hozzáférési információt nem tudom kiadni. "
    "Felhasználói funkciók és dokumentált használati módok ismertetésében tudok segíteni."
)
SENSITIVE_OUTPUT_BLOCK_MESSAGE = (
    "A válasz biztonsági okból nem jeleníthető meg. "
    "Fogalmazd át a kérdést dokumentált felhasználói vagy műszaki információra."
)

_MAX_REQUEST_SCAN_CHARS = 20_000
_MIN_SECRET_LENGTH = 12
_INSTRUCTION_SIGNATURE_LENGTH = 80
_INSTRUCTION_SIGNATURE_STEP = 40


class SensitiveRequestCategory(StrEnum):
    INTERNAL_INSTRUCTION_EXTRACTION = "internal_instruction_extraction"
    RUNTIME_CAPABILITY_ENUMERATION = "runtime_capability_enumeration"
    CREDENTIAL_EXTRACTION = "credential_extraction"
    SECURITY_BYPASS_REQUEST = "security_bypass_request"


class SensitiveOutputCategory(StrEnum):
    CONFIGURED_SECRET = "configured_secret"
    INTERNAL_INSTRUCTION = "internal_instruction"


@dataclass(frozen=True)
class SensitiveRequestDecision:
    blocked: bool
    category: SensitiveRequestCategory | None = None


@dataclass(frozen=True)
class SensitiveOutputMatch:
    category: SensitiveOutputCategory


class SensitiveOutputBlocked(RuntimeError):
    def __init__(self, match: SensitiveOutputMatch) -> None:
        super().__init__(SENSITIVE_OUTPUT_BLOCK_MESSAGE)
        self.match = match


_EXTRACTION_INTENTS = (
    "mutasd meg",
    "ird ki",
    "masold ki",
    "sorold fel",
    "add meg",
    "fedd fel",
    "mondd meg",
    "mi van benne",
    "milyen erteku",
    "show me",
    "print",
    "dump",
    "export",
    "reveal",
    "list",
    "give me",
    "tell me",
    "what is the value",
    "what is your",
    "what's your",
    "mi az aktualis",
    "mi a tokened",
)

_INTERNAL_INSTRUCTION_TARGETS = (
    "rendszerprompt",
    "rendszer prompt",
    "system prompt",
    "developer prompt",
    "developer instruction",
    "fejlesztoi utasitas",
    "rejett utasitas",
    "belso utasitas",
    "belso szabaly",
    "uzenetszerep",
    "internal instruction",
    "hidden instruction",
)

_CREDENTIAL_TARGETS = (
    ".env",
    "environment variable",
    "kornyezeti valtozo",
    "authorization header",
    "authorization fejlec",
    "bearer token",
    "api token",
    "mcp token",
    "service token",
    "obsidian token",
    "graphrag token",
    "lm studio token",
    "adatbazis jelszo",
    "database password",
    "kapcsolati karakterlanc",
    "connection string",
)

_CAPABILITY_TARGETS = (
    "mcp eszkoz",
    "mcp tool",
    "vault muvelet",
    "vault eszkoz",
    "tool inventory",
    "eszkozlista",
    "allowed_tools",
    "allowed tools",
    "engedelyezett eszkoz",
    "futasideju kepesseg",
    "runtime capability",
)

_CAPABILITY_INTENTS = (
    "milyen",
    "mire vagy kepes",
    "kepes vegrehajtani",
    "tudsz hasznalni",
    "miket kaptal",
    "milyen toolokat kaptal",
    "elerheto",
    "sorold",
    "mutasd",
    "list",
    "what tools",
    "what operations",
    "which tools",
    "capabilities",
)

_SECURITY_TARGETS = (
    "biztonsagi szabaly",
    "vedelmi mechanizmus",
    "irasvedelm",
    "read-only",
    "read only",
    "allowlist",
    "engedelylista",
    "sensitive guard",
    "biztonsagi vedelem",
)

_BYPASS_INTENTS = (
    "kapcsold ki",
    "tiltsd le",
    "keruld meg",
    "hagyd figyelmen kivul",
    "ird felul",
    "modositsd",
    "bypass",
    "disable",
    "circumvent",
    "ignore",
    "remove",
    "override",
)


def normalize_for_guard(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = "".join(
        character
        for character in unicodedata.normalize("NFKD", normalized)
        if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", normalized).strip()


class SensitiveRequestGuard:
    def evaluate(self, content: str) -> SensitiveRequestDecision:
        normalized = normalize_for_guard(content[:_MAX_REQUEST_SCAN_CHARS])

        if _contains_any(normalized, _SECURITY_TARGETS) and _contains_any(
            normalized, _BYPASS_INTENTS
        ):
            return SensitiveRequestDecision(
                blocked=True,
                category=SensitiveRequestCategory.SECURITY_BYPASS_REQUEST,
            )
        if _contains_any(normalized, _CREDENTIAL_TARGETS) and _contains_any(
            normalized, _EXTRACTION_INTENTS
        ):
            return SensitiveRequestDecision(
                blocked=True,
                category=SensitiveRequestCategory.CREDENTIAL_EXTRACTION,
            )
        if _contains_any(normalized, _INTERNAL_INSTRUCTION_TARGETS) and _contains_any(
            normalized, _EXTRACTION_INTENTS
        ):
            return SensitiveRequestDecision(
                blocked=True,
                category=SensitiveRequestCategory.INTERNAL_INSTRUCTION_EXTRACTION,
            )
        if _contains_any(normalized, _CAPABILITY_TARGETS) and _contains_any(
            normalized, _CAPABILITY_INTENTS
        ):
            return SensitiveRequestDecision(
                blocked=True,
                category=SensitiveRequestCategory.RUNTIME_CAPABILITY_ENUMERATION,
            )
        return SensitiveRequestDecision(blocked=False)


@dataclass(frozen=True)
class SensitiveValueRegistry:
    values: tuple[str, ...]

    @classmethod
    def from_settings(cls, settings: Settings) -> SensitiveValueRegistry:
        candidates = [
            settings.lm_studio_api_token,
            settings.lm_studio_responses_obsidian_mcp_token,
            _secret_value(settings.graphrag_service_token),
            _database_password(settings.database_url),
        ]
        unique_values = {
            value for candidate in candidates if (value := _eligible_secret(candidate)) is not None
        }
        return cls(values=tuple(sorted(unique_values, key=len, reverse=True)))


class SensitiveOutputGuard:
    def __init__(
        self,
        registry: SensitiveValueRegistry,
        *,
        protected_instructions: tuple[str, ...] = (),
    ) -> None:
        self._secret_values = registry.values
        self._instruction_signatures = _instruction_signatures(protected_instructions)
        pattern_lengths = [
            *(len(value) for value in self._secret_values),
            *(len(signature) for signature in self._instruction_signatures),
        ]
        self.holdback_chars = max(pattern_lengths, default=1)

    def find_match(self, content: str) -> SensitiveOutputMatch | None:
        for secret in self._secret_values:
            if secret in content:
                return SensitiveOutputMatch(SensitiveOutputCategory.CONFIGURED_SECRET)

        normalized = normalize_for_guard(content)
        for signature in self._instruction_signatures:
            if signature in normalized:
                return SensitiveOutputMatch(SensitiveOutputCategory.INTERNAL_INSTRUCTION)
        return None

    def ensure_safe(self, content: str) -> None:
        match = self.find_match(content)
        if match is not None:
            raise SensitiveOutputBlocked(match)


class SensitiveStreamFilter:
    def __init__(self, guard: SensitiveOutputGuard) -> None:
        self._guard = guard
        self._observed = ""
        self._released = ""
        self._pending = ""

    def push(self, content: str) -> str:
        if content == "":
            return ""
        self._observed += content
        self._pending += content
        self._guard.ensure_safe(self._observed)
        releasable_count = max(0, len(self._pending) - self._guard.holdback_chars)
        if releasable_count == 0:
            return ""
        released = self._pending[:releasable_count]
        self._pending = self._pending[releasable_count:]
        self._released += released
        return released

    def finish(self, final_content: str | None = None) -> str:
        complete = self._observed if final_content is None else final_content
        self._guard.ensure_safe(complete)
        if complete.startswith(self._released):
            released = complete[len(self._released) :]
        else:
            released = self._pending
        self._observed = complete
        self._released += released
        self._pending = ""
        return released


def _contains_any(content: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in content for phrase in phrases)


def _secret_value(value: SecretStr | None) -> str | None:
    return value.get_secret_value() if value is not None else None


def _database_password(database_url: str) -> str | None:
    try:
        password = make_url(database_url).password
    except Exception:
        return None
    return unquote(password) if password is not None else None


def _eligible_secret(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if len(stripped) < _MIN_SECRET_LENGTH:
        return None
    return stripped


def _instruction_signatures(instructions: tuple[str, ...]) -> tuple[str, ...]:
    signatures: set[str] = set()
    for instruction in instructions:
        normalized = normalize_for_guard(instruction)
        if len(normalized) < _INSTRUCTION_SIGNATURE_LENGTH:
            continue
        final_start = len(normalized) - _INSTRUCTION_SIGNATURE_LENGTH
        starts = range(0, final_start + 1, _INSTRUCTION_SIGNATURE_STEP)
        for start in starts:
            signatures.add(normalized[start : start + _INSTRUCTION_SIGNATURE_LENGTH])
        signatures.add(normalized[final_start:])
    return tuple(sorted(signatures))
