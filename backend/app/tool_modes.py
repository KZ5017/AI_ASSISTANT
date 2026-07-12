from dataclasses import dataclass
from typing import Literal

from app.config import Settings

ToolMode = Literal["none", "obsidian", "excel"]

OBSIDIAN_TOOL_PROMPT = """[Obsidian tool mode]
Te egy lokalis LLM vagy, amely Obsidian vaultban dolgozik MCP eszkozon keresztul.
A felhasznalo kerdesere csak a vault tartalma alapjan valaszolhatsz.
A vault tartalmanak felterkepezesehez eloszor a 00-INDEX.md fajlt hasznald.
A 00-INDEX.md alapjan keresd meg a valaszhoz relevans jegyzeteket.
Ha a valaszhoz szukseges informacio nem talalhato meg a vaultban, mondd ki vilagosan.
Ne talalj ki vaulton kivuli informaciot.
Ne hivatkozz olyan jegyzetre vagy fajlra, amelyet nem talaltal meg.
A vegso valaszt magyarul, jol strukturaltan add meg, hacsak a felhasznalo mast nem ker."""

EXCEL_TOOL_PROMPT = """[Excel database tool mode]
Te egy lokalis LLM vagy, amely Excel fajlokban tarolt tabularis adatokkal dolgozik MCP eszkozon keresztul.
A felhasznalo kerdesere az Excel adatforrasok tartalma alapjan valaszolj.
Adatbazis modban a valaszhoz az Excel eszkozt kell hasznalnod.
Kotelezo elso lepes: eloszor mindig olvasd el a 00-INDEX.xlsx fajlt.
A 00-INDEX.xlsx adatforras-index. Ebbol allapitsd meg, melyik Excel fajl, munkalap, tartomany es oszlop relevans a kerdeshez.
A felhasznalonak nem kell fajlnevet vagy munkalapnevet megadnia.
Ha a kerdes es a 00-INDEX.xlsx alapjan egyertelmuen kivalaszthato az adatforras, hasznald azt.
Ha tobb adatforras is relevans, valaszd a legvaloszinubbet, es roviden jelezd, milyen adatforras alapjan valaszolsz.
Ha a 00-INDEX.xlsx alapjan sem dontheto el, melyik adatforrast kell hasznalni, kerj pontositas.
A valaszhoz ne talalj ki tablazaton kivuli adatot.
Ha a valaszhoz szukseges informacio nem talalhato meg az indexben vagy a relevans Excel fajlban, mondd ki vilagosan.
Kizarolag olvasasi/informaciokinyeresi muveleteket hasznalhatsz.
Tilos Excel fajlt letrehozni, modositani, torolni, formazni, kepletet irni, munkalapot atnevezni vagy barmilyen irasi/mutacios toolt hivni.
Tilos pivot tablat, diagramot, uj munkalapot, szamitott tartomanyt vagy barmilyen seged-osszefoglalot letrehozni.
Osszesites, rangsorolas vagy szures eseten a mar kiolvasott adatokbol kovetkeztess es szamolj, ne hozz letre uj Excel objektumot.
Ez a tiltas akkor is ervenyes, ha a felhasznalo kifejezetten irasi vagy modosito muveletre ker.
Valaszadas menete: 1) olvasd el a 00-INDEX.xlsx fajlt, 2) valaszd ki a relevans fajlt, munkalapot es tartomanyt, 3) olvasd el a szukseges adatokat, 4) kizarolag az olvasott Excel adatok alapjan valaszolj.
A vegso valaszt magyarul, jol strukturaltan add meg, hacsak a felhasznalo mast nem ker."""


@dataclass(frozen=True)
class ToolModePolicy:
    id: ToolMode
    label: str
    integration_ids: tuple[str, ...] = ()
    prompt_instructions: str | None = None


SUPPORTED_TOOL_MODES: tuple[ToolMode, ...] = ("none", "obsidian", "excel")


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
    if normalized == "excel":
        return ToolModePolicy(
            id="excel",
            label="Adatbazis",
            integration_ids=(settings.lm_studio_excel_integration_id,),
            prompt_instructions=EXCEL_TOOL_PROMPT,
        )
    raise ValueError(f"Unsupported tool mode: {tool_mode}")


def _normalize_tool_mode(tool_mode: str | None) -> ToolMode:
    if tool_mode is None or tool_mode.strip() == "":
        return "none"
    if tool_mode not in SUPPORTED_TOOL_MODES:
        raise ValueError(f"Unsupported tool mode: {tool_mode}")
    return tool_mode
