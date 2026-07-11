# 008 - Markdown Content Layout Hygiene Plan

## Cel

Ez a terv a chatben megjeleno assistant Markdown tartalmak stabil, esztetikus es szelessegbiztos megjeleniteset irja le.

A konkret problema: egyes modellek hosszu, nem vagy nehezen torheto tartalmakat adnak vissza, peldaul shell parancsokat, URL-eket, inline code reszeket, code blockokat vagy tablazatokat. Ezek jelenleg ki tudnak futni abbol a kozepre koncentralt savbol, ahol a chat folyik.

Az elso cel nem syntax highlighting es nem advanced code viewer, hanem az, hogy a Markdown tartalom ne tudja szethuzni a chat layoutot.

Status: Phase A CSS-only MVP kesz, felhasznaloi proban megfelelonek itelve. A jelenlegi inline code, code block es table viselkedes tudatos dontes alapjan elfogadott.

## Kiindulasi pont

A frontend jelenleg:

- `react-markdown`-t hasznal,
- `remark-gfm` pluginnel,
- assistant valaszoknal kozvetlenul a `.message-bubble` alatt renderel,
- reasoning panelben es saved reasoning panelben kulon `.reasoning-panel__content` wrapper alatt renderel.

A `react-markdown` normal Markdownbol tipikusan ezekre az elemekre renderel:

- `a`,
- `blockquote`,
- `br`,
- `code`,
- `em`,
- `h1`-`h6`,
- `hr`,
- `img`,
- `li`,
- `ol`,
- `p`,
- `pre`,
- `strong`,
- `ul`.

A `remark-gfm` miatt pluszban szamitani kell ezekre:

- `del`,
- `input`,
- `table`,
- `thead`,
- `tbody`,
- `tr`,
- `th`,
- `td`.

Fenced code block eseten a megszokott szerkezet:

```html
<pre><code class="language-bash">...</code></pre>
```

Inline code eseten:

```html
<code>sudo -l</code>
```

## Hatarok

Elso korben cel:

- assistant final Markdown tartalom ne fusson ki horizontalisan a chat savbol,
- `pre` / fenced code block kapjon kontrollalt overflow viselkedest,
- `table` ne feszitse szet a layoutot,
- listak, blockquote-ok, headingek es bekezdesek kapjanak konzisztens spacinget,
- a meglévő light/dark tokenekhez illeszkedjen,
- reasoning panel korabbi kompakt megjelenese ne romoljon.

Elso korben nem cel:

- syntax highlighting,
- code block copy gomb,
- language badge,
- custom `ReactMarkdown components` renderer,
- inline code tartalmi tordelese,
- model output szovegenek normalizalasa vagy modositasa.

Fontos aktualis dontes:

> Inline code ne torjon egyelore.

Ez azt jelenti, hogy az inline `code` kapjon sajat vizualis chip-szeru/monospace stilust, de ne vezessunk be ra agressziv `overflow-wrap: anywhere` vagy `word-break: break-all` szabalyt. Ha egy inline code nagyon hosszu, azt kesobb kulon dontes alapjan finomitjuk.

## Tervezett CSS-strategia

### 1. Assistant Markdown scope

Javasolt egy szuk scope, hogy a modositasok ne szorodjanak szet az egesz appra.

Mivel a jelenlegi markupban nincs kulon markdown wrapper, ket lehetoseg van:

1. MVP CSS selector a jelenlegi szerkezetre:

```css
.message-row.is-assistant .message-bubble ...
```

2. Kesobbi tisztabb wrapper:

```tsx
<div className="markdown-content">
  <ReactMarkdown ...>{message.content}</ReactMarkdown>
</div>
```

Javaslat elso korre: ne modositsuk a markupot, ha CSS-sel biztonsagosan megoldhato. Ha a selectorok tul nagyra nonek vagy a reasoning/saved reasoning is duplikalodik, akkor vezessunk be `MarkdownContent` komponenst kesobb.

### 2. Block szintu elemek

A kovetkezo elemek kapjanak kontrollalt margot es max-width viselkedest:

- `p`,
- `ul`,
- `ol`,
- `blockquote`,
- `pre`,
- `table`,
- `h1`-`h6`,
- `hr`.

Javaslat:

- elso elem margin-top: 0,
- utolso elem margin-bottom: 0,
- bekezdes/lista/table/code block kozti tavolsag legyen aranyos a jelenlegi chat line-heighttel,
- headingek ne legyenek hero meretuek, hanem chat-tartalomhoz illeszkedo, visszafogott szintek.

### 3. Fenced code block / `pre code`

Code block viselkedes:

- `pre` legyen `max-width: 100%`,
- `pre` kapjon `overflow-x: auto`,
- `pre` ne novelje a message row szelesseget,
- `pre` kapjon surface-soft hatteret, border-t es kis radiust,
- `code` a `pre` belsejeben maradjon monospace,
- `white-space: pre` vagy `pre-wrap` dontes kulon figyelmet igenyel.

Javaslat elso korre:

- `pre` horizontalisan scrollozzon,
- code block tartalma ne legyen agressziven attordelve,
- a chat layout maradjon stabil.

Indoklas: parancsoknal es kodnal sokszor fontos az eredeti sorstruktura. Ha mindenaron torjuk, romolhat a masolhatosag es olvashatosag.

### 4. Inline code

Elso korben csak vizualis stilus:

- monospace font,
- surface-soft vagy enyhe primary-tint hatter,
- border,
- kis radius,
- mersekelt horizontal padding.

Nem kerul be elso korben:

- `overflow-wrap: anywhere`,
- `word-break: break-all`,
- barmilyen tartalmi vagy whitespace atiras.

Nyitott kesobbi finomitas:

- ha az inline code tovabbra is tul gyakran szetfeszit, akkor eldontjuk, hogy kapjon-e torheto viselkedest, vagy inkabb a teljes assistant markdown kontener kapjon overflow vedelmet.

### 5. Tablazatok

A GFM tablazatok kulon figyelmet igenyelnek.

Elso korben ket jarhato megoldas van:

1. CSS-only table scroll:

```css
.message-row.is-assistant .message-bubble table {
  display: block;
  max-width: 100%;
  overflow-x: auto;
}
```

2. Kesobbi ReactMarkdown component override, amely wrapperbe teszi:

```html
<div class="markdown-table-wrap"><table>...</table></div>
```

Javaslat elso korre: CSS-only table scroll, mert nincs markup valtozas es kis kockazatu.

Tablazat stilus:

- border-collapse: collapse,
- th/td border tokenbol,
- th enyhe surface-soft hatter,
- cell padding visszafogott,
- cellakban `code` es linkek ne feszitsek szet a chatet.

### 6. Linkek es URL-ek

Linkeknel hosszu URL elofordulhat.

Javaslat:

- link szin primary/token alapon,
- `overflow-wrap: anywhere` csak linkekre megfontolhato,
- de inline code-ra nem.

Ez kompromisszum: URL-eknel elfogadhatobb a tordeles, parancsoknal/kodnal kevesbe.

### 7. Kepek

Ha a modell vagy user Markdown kepet eredmenyez:

- `img { max-width: 100%; height: auto; }`,
- ne feszitse szet a chatet,
- radius es border opcionális.

## Implementacios javaslat

### Phase A - CSS-only MVP

1. Letrehozni egy logikai Markdown CSS blokkot az `app.css`-ben a message thread reszenel.
2. Scope: `.message-row.is-assistant .message-bubble`.
3. Hozzaadni:
   - block spacing,
   - heading sizing,
   - code block `pre` overflow-x,
   - table CSS-only overflow-x,
   - img max-width,
   - blockquote stilus,
   - hr stilus,
   - link stilus.
4. Inline code csak vizualis stilust kap, tordeles nelkul.
5. Reasoning panel stilusokat nem bolygatni, hacsak egyertelmuen nem oroklik rosszul a valtozast.
6. Frontend build.
7. Manual smoke hosszu shell parancsot, fenced bash blockot, fenced c blockot es GFM tablazatot tartalmazo assistant valasszal.

### Phase B - MarkdownContent wrapper, ha kell

Akkor indokolt, ha:

- a selectorok tul bonyolultak,
- a reasoning es normal assistant Markdown megjeleneset kozosan akarjuk kezelni,
- table wrapperhez vagy code block headerhez markup kell,
- code block copy gombot akarunk.

Lehetseges komponens:

```tsx
export function MarkdownContent({ content, compact = false }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>;
}
```

Kesobb `components` prop-pal bovitheto:

- `pre`,
- `code`,
- `table`,
- `a`.

### Phase C - Code block polish, ha kell

Kesobbi lehetosegek:

- code block copy gomb,
- language badge (`bash`, `c`, `python`),
- syntax highlighting,
- expanded code block view,
- sorok wrap/nowrap kapcsolo.

## Elfogadasi kriteriumok

- Hosszu egysoros shell parancs nem huzza szet a chat savot.
- Fenced bash code block nem huzza szet a chat savot.
- Fenced C code block olvashato es nem szelesiti tul a layoutot.
- GFM tablazat nem huzza szet a chat savot; ha tul szeles, sajat horizontal scrollt kap.
- Inline code tovabbra is monospace/chip-szeru, de elso korben nincs agressziv tordeles.
- Assistant Markdown elso es utolso eleme nem okoz extra felesleges margot.
- Light es dark mode-ban is tokenizalt, konzisztens megjelenes marad.
- `npm run build` sikeres.

## Manual smoke mintak

### Hosszu inline/parancs jellegu tartalom

```text
Egy hosszu, egysoros shell parancs sok kapcsoloval, idezojellel es pipe-pal, amely normal esetben tul szeles lenne a chat savhoz.
```

### Bash code block

```bash
uname -r
wget https://example.test/really/long/path/to/file.c
gcc -pthread file.c -o file -lcrypt
./file <password>
```

### C code block

```c
// example.c
#include <stdio.h>
#include <stdlib.h>
void example(void) {
    system("/bin/bash");
}
```

### GFM table

```markdown
| Prioritás | Vektor | Ellenőrzés |
| --- | --- | --- |
| 1 | `sudo -l` -> NOPASSWD parancs -> GTFOBins | `sudo -l` + gtfobins |
| 2 | SUID binary -> GTFOBins | `find / -perm -u=s` |
```

## Nyitott dontesek

- Inline code torheto legyen-e kesobb, ha gyakran szetfeszit?
- Kell-e `MarkdownContent` wrapper mar az elso korben, vagy eleg a CSS-only MVP?
- Code block tartalom `white-space: pre` vagy `pre-wrap` legyen-e hosszu parancsoknal?
- GFM table-nel eleg-e a CSS-only `display: block; overflow-x: auto`, vagy kell wrapper komponens?
- Legyen-e kesobb copy gomb es language badge code blockokra?

## Dontesi osszefoglalo

- A CSS-only Markdown layout hygiene MVP kesz.
- Inline code nem kap agressziv tordelest, mert a jelenlegi mukodes megfelelo.
- Fenced code block es table nem fesziti szet a chat layoutot; sajat overflow-x viselkedest kap.
- Markup/component refaktor most nem szukseges, csak kesobbi igeny eseten kerul elo.
