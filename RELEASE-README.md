# Ignition Themes

Ten curated Perspective gateway themes. A **theme** here is a native Ignition 8.3 gateway config resource — it restyles every stock Ignition component without needing a parent project, a project stylesheet, or any style classes.

Source, full generator documentation and the evaluation this pack grew out of — what a theme can and cannot reach, and what a look-and-feel parent still buys on top of one — are at <https://github.com/Gaskony-Ignition/project-themes>.

## What's in the box

| Theme id | Label | Look | Mode |
| --- | --- | --- | --- |
| `glass-violet` | Glass Violet | translucent glass panels over a violet/blue/green/pink gradient field | dark |
| `glass-green` | Glass Green | translucent glass panels over a dark near-black green/teal gradient field, bright mint accent | dark |
| `leather-dark` | Leather Dark | warm tan leather and dark paper, reads as a book after dark | dark |
| `leather-light` | Leather Light | warm tan leather and parchment, reads as a book in daylight | light |
| `finance-ledger` | Finance Ledger | clean, restrained ledger/spreadsheet look | light |
| `newsprint-dark` | Newsprint Dark | newsprint greys and ink on a dark page | dark |
| `nord-dark` | Nord Dark | the Nord palette, dark mode | dark |
| `nord-light` | Nord Light | the Nord palette, light mode | light |
| `industrial-dark` | Industrial Dark | industrial control-room cyan, dark mode | dark |
| `industrial-light` | Industrial Light | industrial control-room cyan, day mode | light |

Every theme covers the full live IA theme-variable surface that's meaningfully themeable (110 custom properties per theme — see "What's covered" below), not just the handful of headline colours. Every theme declares `color-scheme` correctly for its own mode, so Chrome's auto-dark-mode doesn't repaint chart SVGs white on a dark theme.

## Installing on a gateway

### 0. Theme Installer project (easiest)

If you can import a Perspective project but would rather not touch the gateway's filesystem or open a terminal at all, skip everything below and use `Theme_Installer-<VERSION>.zip` instead — shipped alongside this zip, from a project that embeds every theme's files as data inside a gateway-scope script, so importing the project *is* shipping the payload:

1. Gateway web UI → **Config → Projects → Import**, pick `Theme_Installer-<VERSION>.zip`.
2. Open `<gateway>/data/perspective/client/Theme_Installer`.
3. Click **Install all themes**. It writes the files AND runs the config scan itself — no separate "Scan File System" step, nothing else to do.
4. The page's table updates itself: the Status column flips to "Installed" for all 10 rows once the scan lands (a couple of seconds). Cross-check with step 3 below if you want the `curl` version too.
5. Optional: delete the `Theme_Installer` project afterwards. It is parent-free and self-contained — removing it does not touch the themes it already wrote, because those are gateway config resources, not project resources.

Re-running **Install custom themes** overwrites whatever is on the gateway with the embedded copies — so importing a newer release of the installer and pressing the button again is the repair path if an Ignition upgrade (or anything else) ever damages the installed themes. Installing the custom themes never touches a stock theme, and the table says so per row.

**Updating the stock themes (optional)**: the stock themes ship no scrollbar styling and no `color-scheme` declaration. **Update stock themes** adds exactly those two things to the four on-disk stock variants (`light-cool`, `light-warm`, `dark-cool`, `dark-warm`) — their look does not change — and **Restore stock themes** puts them back exactly. `light` and `dark` live inside the Perspective module (no files on disk), so they are never touched; pick `light-cool`/`dark-cool` to get the additions. An Ignition upgrade may replace the variants' files; press **Update stock themes** again afterwards.

**Uninstalling**: open the same page and click **Remove custom themes** — goes through `system.config.delete()`, which removes the resource AND its files in one call, no scan needed.

**Trying them on**: once installed, the same page gives you two ways to switch, live in your own session, with no reload and no picker to build. **Theme switcher** opens a popup of swatches — every theme as a button in its own colours. The **Theme** dropdown beside that button is the other one, listing the same themes in a control small enough to sit in a header.

Both are copy-me artefacts, and both list what **the gateway** has rather than what this release ships, so either works unchanged in a project on a gateway that has none of these packs. Copy `views/ThemeDropdown` into another project and place it with an Embedded View component (`props.path = "ThemeDropdown"`, about 260×34) — that is the whole job. Or copy `views/SelectorPopup` and open it with `system.perspective.openPopup('theme-selector', 'SelectorPopup', title='Theme switcher', modal=True, draggable=True, resizable=False, overlayDismiss=True, viewportBound=True, position={'width': 560, 'height': 590})`. Neither needs a script package, a parent project or any prop wiring.

Prefer the `install.sh` route below if you want to inspect or script the install without a Designer/Gateway UI round-trip, or if you're deploying to several gateways from one place.

### 1. Install the files

Three `install.sh` modes (or copy manually — see below):

```bash
# Local filesystem -- e.g. a mounted docker volume
./install.sh --data-dir /path/to/ignition/data

# A running Ignition docker container
./install.sh --docker <container-name>

# A remote gateway over ssh (key-based auth; data-dir is on the REMOTE host)
./install.sh --ssh gateway.example.com --data-dir /path/to/ignition/data
```

Each mode copies every theme directory next to `install.sh` into:
```text
<data-dir>/config/resources/core/com.inductiveautomation.perspective/themes/<theme-id>/
```
replacing any existing directory of the same name (idempotent — safe to re-run). It tries to match ownership to the gateway's own `light-cool` directory; if it can't detect that, it leaves ownership alone rather than guess. It refuses to touch `light`, `dark`, `light-cool`, `light-warm`, `dark-cool`, `dark-warm` under any circumstances.

**Manual alternative** — if you'd rather not run a shell script against a gateway you don't fully trust yet, copy each theme folder yourself to the same destination path, preserving the four files inside each (`config.json`, `index.css`, `variables.css`, `globals.css` — plus `resource.json`), then match ownership to a sibling shipped theme directory by hand.

### 2. Scan — the CONFIG scan, not the Projects one

Themes are gateway **config resources**, not project resources. In the gateway web UI: **Config → Platform → Overview → "Scan File System"**. This is a *different* button from the Projects page's own "Scan File System" — that one only picks up project resources (views, scripts, style classes) and will not register a new theme.

**No gateway restart is required.** Despite what the 8.1 and 8.3 docs say about a new theme needing a restart before it's selectable, this was tested end-to-end on Ignition 8.3.8: a brand-new theme dropped under `config/resources/.../themes/` and registered with a single config scan served immediately and was selectable in the same session.

### 3. Verify

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://<gateway>/data/perspective/themes/<theme-id>.css
```
should return `200` for each installed theme id.

### 4. Select a theme

A Perspective session's theme is `session.props.theme` (bindable, session-wide — not page-scoped, that's `system.perspective.setTheme()` instead). A minimal dropdown bound to it:

```json
{
  "type": "ia.input.dropdown",
  "props": {
    "options": [
      {"label": "Glass Violet", "value": "glass-violet"},
      {"label": "Glass Green", "value": "glass-green"},
      {"label": "Leather Dark", "value": "leather-dark"},
      {"label": "Leather Light", "value": "leather-light"},
      {"label": "Finance Ledger", "value": "finance-ledger"},
      {"label": "Newsprint Dark", "value": "newsprint-dark"},
      {"label": "Nord Dark", "value": "nord-dark"},
      {"label": "Nord Light", "value": "nord-light"},
      {"label": "Industrial Dark", "value": "industrial-dark"},
      {"label": "Industrial Light", "value": "industrial-light"}
    ]
  },
  "propConfig": {
    "props.value": {
      "binding": {
        "type": "property",
        "config": {
          "path": "session.props.theme",
          "bidirectional": true
        }
      }
    }
  }
}
```

`themes.json` (included in this pack) carries the same id/label/dark-flag list as data, if you'd rather build the options dynamically from a script than hand-write them.

### 5. Uninstall

Delete each theme's directory under `.../themes/<theme-id>/` and run the same Overview config scan again. There's no separate gateway-side registry to clean up — the config resource IS the directory.

## What's covered

Each theme's `variables.css` maps **110** of the live gateway's **120** built-in custom properties (audited directly against a running 8.3.8 gateway's flattened `dark.css`/`light.css`, not guessed) — surfaces, borders, ink, the full accent family, status colours (incl. secondary washes), radius, elevation, checkbox/radio/toggle/progress-bar controls, the full 10-step neutral scale, P&ID symbol fill/stroke states, native pipe rendering, and three algorithmically-generated chart scales (`--qual-1..10`, `--seq-1..6`, `--div-1..16`) anchored on each theme's own accent colour.

**Deliberately left inherited** (the remaining 10 of the 120 — geometry or pure IA brand constants, not colours a pack should override): `--white`, `--black`, `--font-NotoSans`, `--opacity-25/50/85`, `--red-10/20/30/50/60`, `--defaultSliderFocusBoxShadow` (a pure blur/spread value with no colour component — its colour half, `--defaultSliderFocusColor`, IS themed).

**Two bonus variables** our themes cover that IA's own built-in themes never define at all — `--tooltip-background-color` and `--arrow-color` are referenced by `.ia_form__tooltip-*` rules via `var()` with no fallback and no `:root` value anywhere in IA's own CSS, so a stock IA tooltip's background/arrow are effectively unset. Every theme in this pack gives them a real value.

**A handful of IA rules hard-code a colour literal directly onto a component selector, bypassing the variable system entirely** — no theme, IA's own or ours, can reach these by overriding a variable. Three were judged common and visible enough to compensate for with a small targeted rule in each theme's `globals.css`:
- Browser text selection (`::selection`) — IA hardcodes a fixed dark blue in dark mode and leaves light mode at browser default; every theme here tints it with its own accent instead.
- The primary slider's focus glow (`.ia_slider__handle:focus`) — IA hardcodes its own blue directly on this selector rather than reading the `--defaultSliderFocusColor` variable the way its own *other* slider implementation does; compensated to read the variable properly.
- Table row hover/selection (`.ia_tableComponent__body__row--hovered`, `.ia_tableComponent__selection`, `.ia_alarmJournalTableComponent__selection`, `.ia_alarmStatusTableComponent__selection`) — the highest-traffic hardcode found (every table hits it); IA's own blue is replaced with the theme's accent at the same alpha steps IA itself uses.

**Left as IA constants, not compensated for** (lower traffic and/or would need a wider, riskier rule to reach properly — genuinely inherited, not an oversight):
- Generic black elevation `box-shadow`s across many selectors (alarm table panels, the pager, table head/foot containers, the toggle switch thumb, editable table cells, form tooltips) — these are neutral black in IA's own themes too, so they're consistent with everything else this pack already does for its own `--boxShadow1..5`.
- The date-range picker's day-hover tint (a narrow, low-traffic component).
- The **entire Equipment Schedule / Gantt component** — progress-bar fill and track, tooltip, schedule-event blocks, lead-time shading, move/selected placeholders, downtime and break-period washes are ALL hard-coded regardless of theme. If your project uses this component, expect it to look the same (IA-purple/blue/peach) under every theme in this pack, including the stock ones.
- `.ia_form__actionBar--fixed`'s border colour (a single grey hairline).
- The video player's control-popup background (deliberately black — matches the convention most video players use regardless of surrounding theme).

## Upgrade risk

Custom-named themes are low-risk — the Perspective module's upgrade migrator only manages the bundled names (`light`, `dark`, and the four shipped variants), and never touches a custom directory. A theme installed by this pack lives only on the gateway it was installed to unless you also keep a copy elsewhere (git, a backup, this zip).

## Source

Generated by `mapping.py` (the token → theme-variable table) and `build_theme.py`, at <https://github.com/Gaskony-Ignition/project-themes>. That repo's `README.md` carries the full generator documentation, including per-theme derivation notes, the style-class contract and the `glass-green` colour correction.

Apache-2.0.
