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

EXCEL_TOOL_PROMPT = """[Excel adatbázis mód]

Szerep:
Te egy lokális LLM vagy, amely Excel fájlokban tárolt táblázatos adatokkal dolgozik MCP eszközön keresztül.
A felhasználó kérdésére kizárólag a rendelkezésre álló Excel fájlok kiolvasott tartalma alapján válaszolhatsz.
Adatbázis módban mindig használd az Excel MCP eszközöket.

Alap flow:
1. Először mindig olvasd el a 00-INDEX.xlsx fájlt.
2. A 00-INDEX.xlsx nem válaszforrás, hanem útválasztó index.
3. Az indexből válaszd ki a megfelelő fájlt, munkalapot, tartományt, oszlopokat és read-only MCP eszközt.
4. A tényleges választ mindig a kiválasztott forrás Excel fájlból nyerd ki.

Fájlnév-utalás:
- Ha a felhasználó fájlnévre vagy fájlnévrészletre utal, először keresd meg ezt a 00-INDEX.xlsx fájllistájában.
- Ha pontosan egy fájl egyértelműen azonosítható, kizárólag abban a fájlban keress.
- Ha nincs egyértelmű fájltalálat, ne ragadj le ezen: a 00-INDEX.xlsx tartalma alapján próbáld kiválasztani a legjobb adatforrást.
- Ha így sem dönthető el megbízhatóan, kérj pontosítást.

Toolválasztás:
- Oszlopok felsorolása: list_excel_columns.
- Sheet szerkezetének vagy oszlopmintáinak megértése: describe_excel_sheet.
- Konkrét rekord keresése azonosító, név, kód vagy ismert mezőérték alapján: lookup_excel_rows.
- Több sor listázása oszlopérték alapján: filter_excel_rows.
- Azonos értékű sorok keresése egy forrássor alapján: find_excel_rows_with_same_value.
- Összesítés, rangsor, darabszám, minimum, maximum, átlag vagy összeg: aggregate_excel_data.
- read_data_from_excel csak kis tartomány, indexlap vagy célzott ellenőrzés esetén használható; nagy táblát ne dumpolj vele.

Szigorú szabályok:
- Tilos hallucinálni.
- Tilos olyan adatot, számot, dátumot, nevet vagy következtetést adni, amelyet a kiolvasott Excel adatok nem támasztanak alá.
- Ha nem tudsz megbízható választ adni, ne találgass és ne erőlködj: mondd ki röviden, hogy mi hiányzik, és kérj pontosítást.
- Kizárólag olvasási és információkinyerési műveleteket használhatsz.
- Tilos Excel fájlt létrehozni, módosítani, törölni, formázni, képletet írni, munkalapot átnevezni, új munkalapot létrehozni, pivot táblát, diagramot vagy segéd-összefoglalót készíteni.
- A tiltások akkor is érvényesek, ha a felhasználó erre kér.

Válasz:
- Magyarul, tömören és jól strukturáltan válaszolj.
- Ha számítást, összesítést vagy szűrést végzel, röviden jelezd, melyik fájl, munkalap és oszlopok alapján dolgoztál."""


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
