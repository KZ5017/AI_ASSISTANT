# Error and Notice UX Plan

Ez a terv a standalone AI Assistant hiba-, warning- es notice-megjelenitesenek finomitasa. Kulonallo terv, mert nem a streaming/recovery core flow resze, hanem UX-minosegi reteget ad a mar mukodo funkciokra.

## Cel

Az app jelenleg tobb helyen jelenit meg hibakat vagy figyelmezteteseket: globalis ErrorBanner, composer warning slot, stream errorok, API hibak, context limit, valamint modellhez kapcsolodo notice-ok. A cel az, hogy ezek kovetkezetesebben, kevesebb zajjal es felhasznalobaratabb magyar szoveggel jelenjenek meg.

## Fontos kitetel

A modellpanel notice/warning viselkedese ennek a tervnek szerves resze.

Resze ennek a tervnek:

- a modelNotice strukturalt notice tipussa alakitasa,
- modellpanel sikeres esemenyek `success` tipusu megjelenitese,
- modellpanel warning/error esemenyek kovetkezetesebb tipizalasa,
- sikeres, atmeneti modellmuvelet-uzenetek automatikus eltuntetese.

Nem cel ebben a tervben:

- a modellpanel nagy layout- vagy vizualis ujratervezese,
- a modell load/unload/select backend szerzodesek atalakitas,
- uj modellpanel funkciok hozzaadasa.

## Jelenlegi helyzet

Meglevo feluletek:

- globalis ErrorBanner a chat canvas tetejen,
- composer alatti stabil warning slot,
- modellpanel sajat notice/warning sorai,
- stream error handler, amely globalis hibara tud irni,
- recovery UI stop/hiba utan, amely csendesen kezeli az abortot,
- frontend errorMessage helper, amely jelenleg egyszeruen Error.message-et ad vissza.

Mukodo jo dontesek, amiket meg kell tartani:

- stream abort nem hiba UX szempontbol,
- composer warning slot stabil helyet foglal, nem rangatja a layoutot,
- context limit uzenet mar magyar es konkret,
- recovery gombok onmagukban jelzik, hogy a user uzenet valasz nelkul maradt.

## Javasolt notice kategoriak

Frontend oldalon erdemes bevezetni egy kozos notice tipust, de elso korben nem kell mindenhol lecserelni a megjelenitest.

Tipusok:

- info: semleges tajekoztatas,
- success: sikeres muvelet, peldaul modell betoltve vagy levalasztva,
- warning: felhasznaloi beavatkozast igenylo, de nem varatlan hiba,
- error: sikertelen muvelet vagy eleresi hiba.

Javasolt TypeScript forma:

type AppNotice = {
  type: "info" | "success" | "warning" | "error";
  message: string;
};

## Megjelenitesi szabalyok

### Composer warning

Csak az uzenetkuldes kozvetlen blokkolasat mutassa.

Ide valo:

- nincs betoltve chat modell,
- prompt elerte a 120000 karakteres limitet,
- teljes context meghaladja a 120000 karakteres limitet.

Nem ide valo:

- chat betoltesi hiba,
- backend eleresi hiba,
- LM Studio provider varatlan hiba,
- rename/delete sikertelenseg.

### Globalis ErrorBanner

Ide keruljon minden workflow-szintu vagy varatlan hiba.

Ide valo:

- chat lista betoltese sikertelen,
- aktiv chat betoltese sikertelen,
- chat rename/delete sikertelen,
- streaming provider hiba, ha nem abort,
- backend/API nem erheto el,
- ismeretlen frontend parsing hiba.

Viselkedes:

- manualisan zarhato maradjon,
- abort/stop soha ne jelenjen meg itt hibakent,
- ugyanazt a hibauzenetet ne duplikaljuk tobb helyen.

### Inline recovery notice

Elso korben ne vezessunk be kulon inline szoveges notice-t. A recovery action row eleg jol kommunikalja az allapotot.

Csak akkor erdemes kesobb hozzaadni, ha user teszt alapjan nem egyertelmu, hogy az utolso user uzenet valasz nelkul maradt.

### Modellpanel notice

A modellpanel notice-ai is az egyseges notice rendszer reszei legyenek.

Ide valo:

- modell sikeresen betoltve,
- modell sikeresen levalasztva,
- modelllista frissitesi hiba,
- LM Studio nem elerheto,
- kivalasztott modell nem talalhato,
- load/unload/select muvelet sikertelen.

Viselkedes:

- success notice 3-5 masodperc utan tunjon el,
- warning/error notice maradjon lathato, amig az allapot fennall vagy uj frissites nem tortenik,
- ne legyen kulon nagy vizualis redesign, csak a meglevo modellpanel notice sorainak tipizalt, kovetkezetes mukodese.

## Hibauzenet-normalizalas

Javasolt uj frontend helper: normalizeErrorMessage(error, fallback).

Cel: a technikai hibakat emberibb magyar uzenetekre cserelni.

Javasolt mappingek:

- Failed to fetch -> A backend nem elerheto. Ellenorizd, hogy fut-e az app backendje.
- NetworkError -> Halozati vagy backend eleresi hiba tortent.
- A bongeszo nem adott olvashato streaming valaszt. -> A streaming valasz nem olvashato ebben a bongeszoben.
- LM Studio nem adott vissza vegleges assistant valaszt. -> Az LM Studio nem adott vegleges valaszt. Probalj ujrakuldest.
- provider/connection jellegu hiba -> Az LM Studio nem valaszolt. Ellenorizd, hogy fut-e es be van-e toltve a modell.

A backendbol erkezo strukturalt context limit detailt meg kell tartani, mert mar jo es konkret.

## Implementacios fazisok

Status: Phase A, Phase B es Phase C aktualis MVP-je kesz.

### Phase A - Notice es error helper alap

Status: kesz.

Feladatok:

- letrehozni egy frontend notice/error helper modult, peldaul frontend/src/utils/notices.ts,
- AppNotice tipus definialasa,
- normalizeErrorMessage helper bevezetese,
- a jelenlegi errorMessage helper kivaltasa a ChatShell-ben,
- build ellenorzes.

Kesz definicio:

- a globalis hibak tovabbra is ugyanott jelennek meg,
- de a leggyakoribb technikai hibak magyarabb, erthetobb szoveget kapnak,
- a modellpanel notice-ai strukturalt tipust kapnak, de nagy layout redesign nelkul.

### Phase B - Composer warning tisztitas

Status: kesz.

Feladatok:

- a composerWarningText szabalyait kulon helperbe rendezni,
- biztositania kell, hogy csak kuldest blokkolo okok jelenjenek meg ott,
- a warning slot stabil helye maradjon meg,
- build ellenorzes.

Kesz definicio:

- composer alatt csak prompt/context/model-loaded jellegu blokkolas jelenik meg,
- nincs layout ugralas,
- a composer szabalyai nem keverednek a modellpanel notice-aival.

### Phase C - Stream es recovery hiba-polish

Status: kesz az aktualis MVP-re.

Feladatok:

- ellenorizni, hogy AbortError minden stream flow-ban csendes marad,
- provider error esetekben globalis, magyarabb uzenet jelenjen meg,
- retry/edit recovery sikertelen muveletei ne tuntessek el feleslegesen a user recovery allapotot,
- celzott manual smoke.

Kesz definicio:

- stop nem piros hiba,
- provider/backend hiba ertheto globalis uzenet,
- recovery actionok megmaradnak, ha tovabbra is user-only allapot van.

## Teszt es smoke terv

Automata:

- npm run build,
- pytest -q,
- ruff check app tests.

Manual smoke:

1. backend leallitva -> frontend ertheto backend eleresi hibat mutat,
2. nincs betoltve modell -> composer warning jelenik meg,
3. context tul hosszu -> composer warning jelenik meg stabil helyen,
4. stream indit majd Leallitas -> nincs globalis error, recovery action megmarad,
5. LM Studio/provider hiba -> globalis error ertheto magyar szoveggel,
6. rename/delete hiba -> globalis error, nem composer warning.

## Kockazatok

- Tul sok uj notice hely zajossa teheti a UI-t. Ezert elso korben ne legyen uj inline notice.
- A modellpanel notice tipizalasa hasznos, de vigyazni kell, hogy ne csusszon at teljes modellpanel redesignba.
- Hibaszovegek tul altalanossa valhatnak; a context limit reszletes uzenetet meg kell tartani.

## Aktualis kovetkezo lepes

Az error/notice MVP implementacio kesz. Kovetkezo lepes csak manual smoke vagy kesobbi finomitas legyen: ikonok/animacio nelkuli tovabbi szovegpolish, ha hasznalat kozben szukseges.
