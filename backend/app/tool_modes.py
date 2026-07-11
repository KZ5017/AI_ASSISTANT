from dataclasses import dataclass
from typing import Literal

from app.config import Settings

ToolMode = Literal["none", "obsidian"]

OBSIDIAN_TOOL_PROMPT = """[Obsidian tool mode]
Te egy lokalis LLM vagy, amely Obsidian vaultban dolgozik MCP eszkozon keresztul.
A felhasznalo kerdesere csak a vault tartalma alapjan valaszolhatsz.
A vault tartalmanak felterkepezesehez eloszor a 00-INDEX.md fajlt hasznald.
A 00-INDEX.md alapjan keresd meg a valaszhoz relevans jegyzeteket.
Ha a valaszhoz szukseges informacio nem talalhato meg a vaultban, mondd ki vilagosan.
Ne talalj ki vaulton kivuli informaciot.
Ne hivatkozz olyan jegyzetre vagy fajlra, amelyet nem talaltal meg.
A vegso valaszt magyarul, jol strukturaltan add meg, hacsak a felhasznalo mast nem ker."""


@dataclass(frozen=True)
class ToolModePolicy:
    id: ToolMode
    label: str
    integration_ids: tuple[str, ...] = ()
    prompt_instructions: str | None = None


SUPPORTED_TOOL_MODES: tuple[ToolMode, ...] = ("none", "obsidian")


def resolve_tool_mode_policy(settings: Settings, tool_mode: str | None) -> ToolModePolicy:
    normalized = _normalize_tool_mode(tool_mode)
    if normalized == "none":
        return ToolModePolicy(id="none", label="Normal")
    if normalized == "obsidian":
        return ToolModePolicy(
            id="obsidian",
            label="Obsidian",
            integration_ids=(settings.lm_studio_obsidian_integration_id,),
            prompt_instructions=OBSIDIAN_TOOL_PROMPT,
        )
    raise ValueError(f"Unsupported tool mode: {tool_mode}")


def _normalize_tool_mode(tool_mode: str | None) -> ToolMode:
    if tool_mode is None or tool_mode.strip() == "":
        return "none"
    if tool_mode not in SUPPORTED_TOOL_MODES:
        raise ValueError(f"Unsupported tool mode: {tool_mode}")
    return tool_mode
