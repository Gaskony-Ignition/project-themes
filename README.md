# Ignition Themes — ten Perspective gateway themes, installed by one button

Stock Ignition gives a Perspective session six themes, all variations on the
same two. This project adds ten more as native gateway config resources, so
they restyle every stock component on every project on the gateway with no
parent project, no project stylesheet and no style classes required.

## Why this exists

A look and feel that every project on a gateway should share is normally a
parent project every consumer must inherit. A theme is a gateway config
resource instead — it reaches every project without anyone inheriting
anything, and it installs by importing one Perspective project and pressing a
button.

## What it looks like

| Glass Violet | Newsprint Dark | Finance Ledger |
|---|---|---|
| ![Glass Violet](images/glass-violet.png) | ![Newsprint Dark](images/newsprint-dark.png) | ![Finance Ledger](images/finance-ledger.png) |

Three of the ten themes, each restyling the same stock components.

![Switcher popup](images/switcher-popup.png)

The copy-me swatch popup, listing the themes installed on the gateway it is
running on rather than a fixed list.

![The switcher popup where no custom theme is installed](images/switcher-none.png)

The same popup on a gateway with none of these themes installed — it offers
that gateway's own themes instead of an id it cannot resolve.

## What it does

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

Each theme covers 110 of the gateway's 120 built-in theme variables, not just
the headline colours, and declares `color-scheme` for its own mode so
Chrome's auto dark mode does not repaint chart SVGs white. Each also publishes
a 69-class `st/...` style-class contract a project can build on without a
parent project — see [docs/INTERNALS.md](docs/INTERNALS.md#the-style-class-contract).

`out/themes.json` carries the same theme list as data (`id`, `label`, `dark`,
`source_pack`) for anything that wants to build a picker from it.

## How to use it

### Install (Theme Installer project)

`Theme_Installer-<VERSION>.zip` comes with each release. It embeds every
theme's files as data inside a gateway-scope script, so importing the project
*is* shipping the payload:

1. Gateway web UI → **Config → Projects → Import**, pick
   `Theme_Installer-<VERSION>.zip`.
2. Open `<gateway>/data/perspective/client/Theme_Installer`.
3. Press **Install**. It writes the files and runs the config scan itself —
   no separate "Scan File System" step, no gateway restart and no credential.
   The status table flips to "Installed" a couple of seconds later.
4. Optional: delete the `Theme_Installer` project afterwards. It is
   parent-free, and removing it does not touch the themes it wrote — those are
   gateway config resources, not project resources.

**Install** is safe to re-run — it overwrites the gateway's copies with the
embedded ones, which is also the repair path if an Ignition upgrade damages an
installed theme. **Remove** deletes them through `system.config.delete()`.
Both only ever touch these ten — a stock theme, or one you made yourself, is
left alone.

Two further buttons are optional: **Update** adds themed scrollbars and a
`color-scheme` declaration to Ignition's four on-disk stock variants without
changing their look, and **Restore** puts them back. See
[docs/INTERNALS.md](docs/INTERNALS.md#updating-the-stock-themes-optional).

A **Customise** page lets you make a theme of your own from any of the ten,
with a live preview that repaints on every save.

Prefer installing the files directly — `./install.sh --data-dir`,
`--docker <container>` or `--ssh <host> --data-dir` — to inspect or script the
install without a Gateway UI round-trip, or to deploy to several gateways from
one place. See [docs/INTERNALS.md](docs/INTERNALS.md#installing-the-files-by-hand).

Themes are gateway **config resources**, not project resources, so they
register through **Config → Platform → Overview → "Scan File System"** — a
different button from the Projects page's own scan, which will not pick up a
new theme. No gateway restart is required.

### Select a theme

A session's theme is `session.props.theme` — bindable and session-wide, as
opposed to the page-scoped `system.perspective.setTheme()`. Bind a dropdown to
it, build the options from `out/themes.json`, or use one of the two copy-me
switchers that ship with `Theme_Installer`: `views/ThemeDropdown` (a 34px
dropdown) and `views/SelectorPopup` (a swatch-grid popup). Both list what the
gateway has rather than what this repo ships. See
[selector-popup/README.md](selector-popup/README.md) for how to embed either
one in another project.

---

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
beside the new one. It prints a `WARNING` line for any mapping entry that
needed a fallback or produced a low-contrast chart colour, a `TWEAK` line per
theme listing overridden variables, and a `SWATCH` line per theme with its ten
`--qual-*` hex values. It exits non-zero only on a hard error in the mapping
itself.

`VERSION` is a plain one-line file, bumped by hand before packaging; neither
`build_installer.py` nor `package.sh` touches it. `package.sh` refuses to run
if `out/`, `out/themes.json` or
`installer-project/Theme_Installer/project.json` is missing, rather than
silently packaging a stale or empty `dist/`. It also runs the repo's
README/tree gate first; bypass deliberately with `--skip-readme-check`.

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
