# Ignition Themes — ten Perspective gateway themes, installed by one button

| Glass Violet | Newsprint Dark | Finance Ledger |
|---|---|---|
| ![Glass Violet](images/glass-violet.png) | ![Newsprint Dark](images/newsprint-dark.png) | ![Finance Ledger](images/finance-ledger.png) |

Stock Ignition gives a Perspective session six themes, all of them variations
on the same two. This project adds ten more, as native gateway **config
resources** — so they restyle every stock Ignition component in every project
on the gateway, with no parent project, no project stylesheet and no style
classes required of the projects that use them.

They install by importing one Perspective project and pressing a button. No
filesystem access, no terminal, no gateway restart, no credential.

Two copy-me theme switchers come with them — a swatch popup and a dropdown —
and both list what the **gateway** has rather than what this repo ships, so
they work unchanged on a gateway these themes were never installed on:

![Switcher popup](images/switcher-popup.png)

## The ten themes

| Theme id | Label | Look | Mode |
| --- | --- | --- | --- |
| `glass-violet` | Glass Violet | translucent glass panels over a violet/blue/green/pink gradient field | dark |
| `glass-green` | Glass Green | translucent glass over a near-black green/teal field, bright mint accent | dark |
| `leather-dark` | Leather Dark | warm tan leather and dark paper — a book after dark | dark |
| `leather-light` | Leather Light | warm tan leather and parchment — a book in daylight | light |
| `finance-ledger` | Finance Ledger | clean, restrained ledger/spreadsheet look | light |
| `newsprint-dark` | Newsprint Dark | newsprint greys and ink on a dark page | dark |
| `nord-dark` | Nord Dark | the Nord palette, dark mode | dark |
| `nord-light` | Nord Light | the Nord palette, light mode | light |
| `industrial-dark` | Industrial Dark | industrial control-room cyan, dark mode | dark |
| `industrial-light` | Industrial Light | industrial control-room cyan, day mode | light |

Every theme covers the whole meaningfully-themeable variable surface — 110 of
the gateway's 120 built-in custom properties, audited against a live 8.3.8
gateway rather than guessed — not just the handful of headline colours. Every
theme declares `color-scheme` for its own mode, so Chrome's auto dark mode
does not repaint chart SVGs white on a dark theme.

`out/themes.json` carries the same list as data (`id`, `label`, `dark`,
`source_pack`) for anything that wants to build a picker from it.

## Installing on a gateway

### The Theme Installer project (easiest)

`Theme_Installer-<VERSION>.zip` comes with each release. It embeds every
theme's files as data inside a gateway-scope script, so importing the project
*is* shipping the payload:

1. Gateway web UI → **Config → Projects → Import**, pick
   `Theme_Installer-<VERSION>.zip`.
2. Open `<gateway>/data/perspective/client/Theme_Installer`.
3. Press **Install**. It writes the files and runs the config scan itself —
   there is no separate "Scan File System" step, no gateway restart and no
   credential. The status table flips to "Installed" a couple of seconds later.
4. Optional: delete the `Theme_Installer` project afterwards. It is
   parent-free, and removing it does not touch the themes it wrote — those are
   gateway config resources, not project resources.

**Install** is safe to re-run: it overwrites the gateway's copies with the
embedded ones, which is also the repair path if an Ignition upgrade ever
damages an installed theme. **Remove** deletes them through
`system.config.delete()`. Both only ever touch these ten — a stock theme, or
one you made yourself, is left alone.

Two further buttons are optional and nothing above needs them: **Update** adds
themed scrollbars and a `color-scheme` declaration to Ignition's four on-disk
stock variants without changing their look, and **Restore** puts them back.
See [docs/INTERNALS.md](docs/INTERNALS.md#updating-the-stock-themes-optional).

### The two pages

* **Installer** — three cards of related buttons, each with what it does to
  the gateway written beside it, then a status table covering the ten,
  Ignition's six and any theme you have made, with a thumbnail in every row of
  the same imaginary plant page drawn in that theme's colours.
* **Customise** — make a theme of your own. The ten are generated from
  `packs/` and Install overwrites them, so they are read-only here and the page
  offers a copy instead. Its values are listed grouped by what they affect —
  click one, change it, Save — beside a live preview that repaints on every
  save. Colours are typed as hex or picked from a row of swatches of the
  colours the theme already uses; Perspective ships no colour picker a view can
  reach. Raw file editing is behind an "Advanced" toggle.

Thumbnails are SVGs generated at build time from the files the installer
embeds, so a row's picture and what Install writes cannot drift apart.
Customise reads the gateway live — the resolved stylesheet the browser is
really served, with the theme's own files laid over the top — so it cannot
advertise a token the installed theme does not ship, and a theme made a second
ago reads correctly.

### Installing the files directly

Prefer this route to inspect or script the install without a Gateway UI
round-trip, or to deploy to several gateways from one place. `install.sh` has
three modes:

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

replacing any existing directory of the same name (idempotent — safe to
re-run). It tries to match ownership to the gateway's own `light-cool`
directory; if it cannot detect that, it leaves ownership alone rather than
guess. It refuses to touch `light`, `dark`, `light-cool`, `light-warm`,
`dark-cool` or `dark-warm` under any circumstances.

#### Scan — the CONFIG scan, not the Projects one

Themes are gateway **config resources**, not project resources. In the gateway
web UI: **Config → Platform → Overview → "Scan File System"**. This is a
*different* button from the Projects page's own "Scan File System" — that one
only picks up project resources (views, scripts, style classes) and will not
register a new theme.

**No gateway restart is required.** Despite what the 8.1 and 8.3 docs say
about a new theme needing a restart before it is selectable, this was tested
end to end on Ignition 8.3.8: a brand-new theme dropped under
`config/resources/.../themes/` and registered with a single config scan served
immediately, and was selectable in the same session. `docs/THEMES-EVALUATION.md`
has the full writeup.

### Selecting a theme

A Perspective session's theme is `session.props.theme` — bindable and
session-wide, as opposed to the page-scoped `system.perspective.setTheme()`.
Bind a dropdown to it bidirectionally, build the options from
`out/themes.json`, or use one of the two switchers below, which build the list
from the gateway itself. A minimal hand-written dropdown is in
[docs/INTERNALS.md](docs/INTERNALS.md#selecting-a-theme-by-hand).

## Adding a theme switcher

`Theme_Installer` ships **two** copy-me views, either of which drops into any
project with no parent project and no style classes: `views/ThemeDropdown` (one
34px dropdown) and `views/SelectorPopup` (a swatch grid opened as a popup).

Both list what the **gateway** has rather than what this repo ships, so a
switcher copied onto a gateway that has none of these themes offers that
gateway's own instead:

![The switcher popup where no custom theme is installed](images/switcher-none.png)

How to embed either one, and the `openPopup` call the popup needs, are in
[docs/INTERNALS.md](docs/INTERNALS.md#adding-a-theme-switcher).

## What a theme covers

Beyond the variables, each theme carries compensating rules for components that
hard-code IA's colours, and publishes a 69-class `st/...` contract a project can
build on without a parent project. Which variables, which components needed
rules, and how the contract is generated are in
[docs/INTERNALS.md](docs/INTERNALS.md#what-a-theme-covers).

## Building from source

```bash
python3 build_theme.py       # regenerate out/ (always wipes + rebuilds)
python3 build_installer.py   # regenerate installer-project/ from out/
./package.sh                 # -> dist/ignition-themes-<VERSION>.zip
                             # -> dist/Theme_Installer-<VERSION>.zip
```

No third-party dependencies — the chart-scale generator uses only the
standard library. `build_theme.py` wipes and rewrites everything under `out/`,
so a rename can never leave a stale directory under an old theme id sitting
beside the new one. It prints:

- a `WARNING` line for every mapping entry that needed a fallback source,
  bottomed out at a `literal:` default, or produced a chart colour with poor
  contrast against the page or too close to its neighbour;
- a `TWEAK` line per theme listing which variables a `TWEAKS` entry overrode;
- a `SWATCH` line per theme with the ten `--qual-*` hex values, for eyeballing
  hue spread.

It exits non-zero only on a hard error — a `mapping.py` entry whose whole
fallback chain resolved to nothing, which is an authoring bug in the generator
rather than a finding about a source pack.

`VERSION` is a plain one-line file, bumped by hand before packaging; neither
`build_installer.py` nor `package.sh` touches it. `package.sh` refuses to run
if `out/`, `out/themes.json` or
`installer-project/Theme_Installer/project.json` is missing, rather than
silently packaging a stale or empty `dist/`.

## Boundaries

Worth knowing before you adopt these, and none of it is fixable from a theme:

- **Elevation is one shadow across five slots.** `--boxShadow1..5` all take a
  single value, and `none` for the packs that declare no shadow token at all
  (`leather-dark`, `industrial-dark`, `industrial-light` — deliberate in
  leather's case, which reads as a flat page rather than a dashboard with
  elevation). `--boxShadow--inset` inherits the same limitation. No source
  pack defines a finer 1–5 elevation scale to derive from.
- **A heading serif face is unreachable.** Leather's Crimson Pro/Georgia
  heading face has no path to Perspective's `ia.display.label` components from
  a theme alone — confirmed against the live DOM, where `ia.display.label`
  always renders as `<div class="ia_labelComponent"><span>` and never a
  semantic heading element.
- **The Equipment Schedule / Gantt component is entirely hard-coded.** Its
  progress bar fill and track, tooltip, schedule-event blocks, lead-time
  shading, move and selected placeholders, downtime and break-period washes
  are all fixed colours regardless of theme. If your project uses it, expect
  it to look the same IA purple/blue/peach under every theme here, and under
  the stock ones too.
- **Other lower-traffic hard-codes are left as IA constants**: generic black
  elevation shadows across alarm table panels, the pager, table head and foot
  containers, the toggle-switch thumb, editable table cells and form tooltips
  (neutral black in IA's own themes too, so consistent with everything else);
  the date-range picker's day-hover tint;
  `.ia_form__actionBar--fixed`'s hairline border; and the video player's
  control-popup background, which is deliberately black to match the
  convention most video players use regardless of surrounding theme.

## Upgrade risk

Custom-named themes are low risk: the Perspective module's upgrade migrator
only manages the bundled names (`light`, `dark`, and the four shipped
variants) and never touches a custom directory. A theme installed here lives
only on the gateway it was installed to, unless you also keep a copy
elsewhere — git, a backup, or a release zip.

## Licence

Apache-2.0. See [LICENSE](LICENSE).
