# Design language: "instrument panel"

The look came out of a real design review of a status dashboard: three plain-HTML directions were built, opened in a browser at
six widths in light and dark, measured, broken, fixed, and one was chosen by the owner (the "ops console": a top bar, a left
rail, dense tabular panels). This page records the language so a new project extends it instead of reinventing it. Everything
described is implemented in `starter/static/css/` and shown live at `/design/` in the starter.

**The hard rule: it must not look like generic Tailwind or AI-dashboard output.** No card grids, stat boxes, gradients, drop
shadows, rounded pills or purple-to-blue washes as the main device.

## What gives it a point of view

- **Warm "paper and graphite" neutrals** instead of cool grey (`#f1f0ec` page / `#111110` in dark).
- **One azure accent** (`--ch-accent-*`), used only for links, focus rings, the active nav item and data marks. Never for status.
- **IBM Plex Sans** for prose, **IBM Plex Mono** for hostnames, ids, numbers and small-caps labels.
- **Rectangular "annunciator" chips** for state: icon + label + tinted fill, mono caps, 2 px radius.
- **Hairlines instead of shadows**, almost no rounding (2 / 3 / 4 px), no gradients.
- **One type scale**, seven steps in `rem` so user zoom works: 11 label, 12 meta, 13 dense, 14 body, 20 title, 28 display, 48 hero.
  At most one hero number per page.
- Where a number needs a visual, a **thin meter** (inline SVG), and where history matters, ticks whose **height**, not just colour,
  say "incident".

Honest weak spots, from the review: azure + Plex is a safe, Carbon-adjacent pairing, so the accent is the least distinctive part;
11 px labels are legible but at the floor (raise `--ch-fs-label` to 12 px, one token, if they tire the eye); a hero number plus a
grid of tiles is still the card-dashboard trope with better type, which is why the starter's overview leads with a sentence
("Nothing needs attention.") instead.

## Page grammar

- **The opening sentence says what needs attention** ("4 things need attention."), and the top of the page is *only* what is broken.
- **Healthy things are collapsed** (`<details class="ch-fold">`, rendered **without** `open`). The review caught two directions that
  opened their healthy folds by default, against the brief. A quiet page is a good page.
- **Say how fresh it is.** A freshness line ("checked 11 s ago, source ...") so a stale dashboard admits it is stale.
- **A site you cannot reach is a state**, not a hundred red rows: one "Site unreachable" incident, its children shown as Unknown
  (hollow, dashed) and excluded from the Down count.
- **The same row grammar everywhere**: panels with a mono-caps header bar, dense tables with a secondary-column collapse
  (`.ch-wide` shows when the wrapper is wide, `.ch-narrow` when it is not), facts as definition lists, folds as `<details>`.

## The status language

Eight states, one table in Python (`STATES` in `apps/core/templatetags/ui.py`), one chip tag (`{% status_chip "down" %}`), colours in
`tokens.css`. Never hand-copy chip markup: it drifted during the review (the key was missing two states, a hard-coded "3 open"
went stale).

| State | Icon | Label | Hue (and why) |
| --- | --- | --- | --- |
| `up` | check-circle-fill | Up | teal-leaning green: stays apart from red and amber for red-green colour blindness |
| `degraded` | exclamation-triangle-fill | Degraded | amber |
| `down` | x-octagon-fill | Down | red |
| `stale` | hourglass-split | Stale | **violet**, deliberately not orange (see below) |
| `offline` | pause-circle | Expected offline | grey |
| `unreach` | wifi-off | Site unreachable | filled red chip, white text |
| `unknown` | question-circle | Unknown | grey, dashed border |
| `warn` | pie-chart-fill | Overcommitted | uses the degraded colours (capacity warnings) |

Rules that came from failures:

- **Never colour alone.** Every state is icon + label (+ tint). Incident days in a history bar are full-height ticks.
- **Stale is violet, not orange.** Orange (hue 19) sat 22 CIE76 units from red (13 under deuteranopia) and the key showed two
  near-identical pink chips. "We do not know" is the one state that must not look like "it is on fire". Do not "tidy" it back.
- **Up is teal-leaning green.** Pure green was 8 to 12 units from red under deuteranopia and 6 from amber under protanopia; the
  closest pair is now 18. Down vs Degraded are still only ~20 units apart under deuteranopia, so they are told apart by label,
  icon and shape, not hue.
- **The most important state must be the most readable.** The first "site unreachable" card was solid red with dark text:
  1.04:1 on its chip, 1.6:1 for its meta text. It is now a tinted card with a heavy red frame and a filled chip that passes in
  both modes. Check the loud states first.
- **Quiet inline form** (`.ch-st`: icon + sentence-case label, no fill) for rows that are fine; the loud chip is for things that
  need a person.

## Colour mechanics (`tokens.css`)

- Every colour is **one** definition: `--ch-surface: light-dark(#fbfaf8, #181817)`. No duplicate dark block to drift.
- Per state: `-solid` (marks, >= 3:1), `-fg` (text/icon on the tint, >= 5.6:1), `-bg` and `-bd` derived with `color-mix()`.
- A **bridge to Bootstrap 5.3** (`--bs-*`) at the bottom maps Bootstrap's variables onto ours, so the Bootstrap grid and reboot
  inherit the theme.
- Contrast was measured on every pair in use, in both modes: body and secondary text >= 7:1, muted text >= 4.5:1, status text on
  its tint >= 5.6:1, marks, control borders and the no-data tick >= 3:1. Re-measure when you add a colour. The review found the
  "no data" tick at 2.8/2.5:1 and the faintest capacity layer at 2.0/2.7:1, both below the floor the file claimed.

## Components in the kit

| Class | What |
| --- | --- |
| `.ch-chip[data-state]`, `.ch-st`, `.ch-tag`, `.ch-count` | state chip, quiet state, neutral tag, count badge |
| `.btn.btn-ch`, `.btn-ch-primary` | buttons on Bootstrap's `.btn`, restyled by tokens |
| `.ch-field`, `.ch-input`, `.ch-select` | form controls (the select chevron follows the text colour in both themes) |
| `.ch-panel`, `.ch-panel__bar`, `.ch-panel__body` | the panel: mono-caps header bar, hairline frame |
| `.ch-fold` | native collapse (`<details>`), with the chevron rotating |
| `.ch-notice[data-state]` | Django messages, shown in the state language |
| `.ch-tablewrap`, `.ch-table` | data tables with container-query column collapse |
| `.ch-meter` | single-value usage meter (inline SVG, amber and full width when over capacity) |
| `.ch-tally`, `.ch-facts` | counts row; definition-list facts |
| `.ch-top`, `.ch-shell`, `.ch-rail`, `.ch-nav`, `.ch-main`, `.ch-head`, `.ch-attn`, `.ch-empty` | the app shell and the "needs attention" frame |
| `.ch-theme` | the Light / Auto / Dark control |

To add a component: put the rules in `components.css`, use only tokens (no literal colours), pair any icon with a label, give it a
44 px touch target under `@media (pointer: coarse), (max-width: 575.98px)`, show it on `/design/`, and let the tests render it.

## Accessibility baseline

- AA contrast everywhere in both themes, measured (above).
- A visible 2 px focus outline on every control; a skip link to `#main`; `aria-pressed` on the theme buttons, kept in sync.
- 44 px touch targets on phones and coarse pointers (the review found compact desktop sizes overriding them: nav 37 px, folds
  36 px, logo 26 px; the touch block now comes last so it wins).
- No horizontal scroll at 320 px. Tap targets, not hover, carry anything essential: a hover-only `title` is not enough for touch
  and keyboard users, so a history bar gets a `role="img"` + `aria-label` summary and the detail page a per-day table.
- Icon-only buttons have accessible names (`aria-label` / visually-hidden text). Icons are `aria-hidden`.
- `prefers-reduced-motion` turns the chevron animation off. The theme control is hidden with `@media (scripting: none)`.

## Designing something new

For a new kind of page (the starter covers the shell, overview, login and a component reference), follow the same process that
produced this language. Skipping it is how the reference project's first mockups shipped an unreadable "site unreachable" card.

1. Write the plain-HTML options (two or three directions) in a folder **outside** `apps/`, `templates/` and `static/`.
2. Open them in a real browser at 320, 375, 768, 1000, 1280 and 1440 px, light and dark, with the worst-case data (a Down service,
   an unreachable site, an over-capacity disk), not just the happy path.
3. Run contrast, focus, overflow, tap-size and heading-order checks as scripts in the page, with folds opened first.
4. Run a colour-blindness simulation on the token values for any new state colour.
5. Write down what failed and what you fixed. Show the owner the options and let them choose.
6. Then implement the choice with tests, and keep the mockups as a record of what was reviewed, not as a target.
