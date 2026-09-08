# How these themes are built

The README says what the themes are and how to install them. This is the rest:
what a theme actually covers, the class contract it publishes, how a switcher
view works, and where everything lives in the repo.

## Updating the stock themes (optional)

Ignition's stock themes ship no scrollbar styling and no `color-scheme`
declaration, so a dark stock session shows the OS's light scrollbar and
Chrome's auto dark mode can repaint SVG fills. **Update** adds
exactly those two things to the four on-disk stock variants (`light-cool`,
`light-warm`, `dark-cool`, `dark-warm`) as one `theme-additions.css` plus one
`@import` line appended to each variant's `index.css`. Their look does not
change — verified, the served CSS diff is purely the appended block — and the
additions read the variant's own `var(--border)` so the scrollbar matches each
variant. **Restore** deletes the file and the line, verified
byte-identical served CSS afterwards.

`light` and `dark` live inside the Perspective module jar with no files on
disk, so they are never touched; pick `light-cool`/`dark-cool` to get the
additions.

Upgrades were tested empirically on a throwaway gateway, 8.3.8 → 8.3.9 on the
same data volume: the custom themes and the updated stock variants all
survived intact. A future version that ships changed stock themes may still
replace the variants' files — if a variant's row ever drops back to "Stock -
not modified", press **Update** again.

## Adding a theme switcher

`Theme_Installer` ships **two**, either of which drops into any project to let
a user change their own session's theme, with no parent project and no style
classes:

- **`views/ThemeDropdown`** — one 34px dropdown. Embed it with an Embedded
  View component (`props.path = "ThemeDropdown"`, about 260×34) and that is the
  whole job.
- **`views/SelectorPopup`** — the swatch grid, opened as a popup. Each theme is
  a button in its own colours, so you can see what you are picking.

**Both list the gateway, not this repo.** Each asks
`system.config.getResources(moduleId="com.inductiveautomation.perspective",
typeId="themes")` when it opens, and adds Ignition's stock six as a fixed base
(`light` and `dark` live inside the Perspective module's jar and never appear
as resources). So a switcher copied onto a gateway that has none of these
themes offers that gateway's own themes instead of writing an id Perspective
cannot resolve, and a theme from anywhere else shows up without either file
being edited.

The popup's swatch colours are a fixed hand-verified list — a view binding
cannot read a colour out of a theme's CSS — but a swatch is only *offered*
when the gateway has that theme, the section heading counts what is there,
and when none are, a line says so and points at the dropdown at its foot:

![The switcher popup where no custom theme is installed](images/switcher-none.png)

Neither view depends on a script package: the listing is inline in each,
duplicated on purpose so that copying one drags nothing else in.

To use the popup in another project:

1. Copy the whole `views/SelectorPopup` directory into the target project (or
   lift it from `selector-popup/SelectorPopup.view.json` here).
2. Add a button anywhere that calls:
   ```python
   system.perspective.openPopup(
       'theme-selector',
       'SelectorPopup',
       title='Theme switcher',
       modal=True,
       draggable=True,
       resizable=False,
       overlayDismiss=True,
       viewportBound=True,
       position={'width': 560, 'height': 590})
   ```
   `width`/`height` are **not** top-level `openPopup` kwargs on this Ignition
   version — confirmed live and against IA's own scripting reference. They go
   inside `position` as plain pixel integers. `viewportBound=True` keeps the
   frame fully on-screen on a short viewport.

That is it — the popup writes `session.props.theme` itself when a swatch is
clicked; nothing else needs wiring up.

Both views are hand-authored and commit-tracked at
`selector-popup/SelectorPopup.view.json` and
`selector-popup/ThemeDropdown.view.json`; `build_installer.py` copies them into
the generated project verbatim, and only their `resource.json` is built fresh
each run.

## What a theme covers

### Variable coverage

Audited 25/08/2026 directly against a live 8.3.8 gateway
(`curl http://<gw>/data/perspective/themes/{dark,light}.css`, every
`--name: value;` enumerated): the flattened theme CSS defines exactly **120**
unique custom properties each. Every theme here covers **110** of them.

Beyond the core ~35 surfaces, borders, ink, accent, status, radius and
elevation variables, the generator derives:

- **Neutral midtones**: `--neutral-40/50/60/70/80`, interpolated (RGB lerp,
  evenly spaced) between the pack's own `--neutral-30` and `--neutral-90` — no
  source token supplies these directly. Added because the audit found ~98
  component rules across `dark.css`/`light.css` reference these *directly*
  (icon fills and strokes, secondary text, hairline borders, SVG symbol
  strokes), not merely as indirection behind variables already covered.
  Leaving them unthemed left a large swath of secondary chrome stock grey
  regardless of theme.
- **Controls**: `--checkbox--checked/unchecked/indeterminate/disabled`,
  `--radio--selected/unselected/disabled`,
  `--toggleSwitch--selected/unselected`,
  `--progressLinearBar--determinate/indeterminate`,
  `--progressLinearTrack--determinate/indeterminate`. All names confirmed
  against the live CSS — an earlier pass guessed `--radio--checked/unchecked/
  indeterminate` and `--toggleSwitch--on/off/disabled` by symmetry with
  `--checkbox--*`; the real names differ, and there is no
  `--radio--indeterminate` or `--toggleSwitch--disabled` at all.
- **Status secondaries**: `--warningSecondary`, `--infoSecondary` — `--warning`
  and `--info` re-emitted as a 16%-alpha wash.
- **P&ID symbols**: `--symbolFill--default/running/faulted/stopped` and
  matching `--symbolStroke--*` (the fill darkened 20%, for a visible outline
  against its own fill; `default` reuses `--containerBorder`).
  `--symbolFillAnimation--default/running` reuse `--neutral-80`, as IA's own
  values for both do.
- **Native pipes**: `--pipeStroke`, `--pipePrimaryFill`, `--pipeSecondaryFill`,
  `--pipeSelectStroke`.
- **Chart scales**, generated algorithmically (standard-library `colorsys`, not
  read from any source pack — none defines a 10/16/6-step scale), anchored on
  the theme's own final `--callToAction`/`--error`/`--neutral-10`, and
  deterministic:
  - `--qual-1..10`: ten hues rotated evenly around the wheel, `--qual-1` being
    the accent hue itself; lightness ~65% / saturation 60% on dark themes,
    ~46% / 60% on light.
  - `--seq-1..6`: a monotonic ramp of the accent hue, weak → strong.
  - `--div-1..16`: a diverging ramp from the accent hue through a neutral
    midpoint matched to the page to the error hue.
  - Every `--qual-*` is checked (warn-only) for contrast ≥1.5 against
    `--neutral-10` and RGB distance ≥40 from its neighbour, wraparound
    included. All ten themes pass with zero chart-scale warnings.
- **Two variables IA's own themes never define at all**:
  `--tooltip-background-color` and `--arrow-color` are referenced by
  `.ia_form__tooltip-*` rules via `var()` with no fallback and no `:root`
  value anywhere in IA's CSS, so a stock tooltip's background and arrow are
  effectively unset. Every theme here gives them a real value.
- **Misc**: `--boxShadow--inset`, `--indicator` and `--indicatorOff` (the LED
  component's diode and the quality-overlay pending state),
  `--contextBackground`, `--defaultSliderFocusColor`,
  `--callToAction--activeAlt` and `--activeAltInvis`.

**Deliberately left inherited** — the remaining 10 of the 120, geometry or
pure IA brand constants rather than colours a theme should own: `--white`,
`--black`, `--font-NotoSans`, `--opacity-25/50/85`, `--red-10/20/30/50/60`,
and `--defaultSliderFocusBoxShadow` (a pure blur/spread value with no colour
component — its colour half, `--defaultSliderFocusColor`, *is* themed).

### Compensating rules for hard-coded IA colours

The same audit scanned the live flattened CSS for colour literals applied
directly to a component selector rather than through a variable. A handful of
IA's own rules bypass the variable system entirely, so **no** theme — IA's own
built-in ones included — can reach them by overriding `variables.css` alone.
Each theme's `globals.css` adds three targeted compensating rules, judged
common, visible and low-risk enough to be worth it — the same selectors IA
itself defines, at the same alpha steps, just with the theme's own accent:

- **`::selection`** — IA's `dark.css` hard-codes a fixed dark blue and
  `light.css` defines none at all (browser default). Tinted with the theme's
  own accent at 0.35 alpha.
- **`.ia_slider__handle:focus`** — hard-codes its own blue `color` directly
  rather than reading `--defaultSliderFocusColor`, the way IA's *other* slider
  implementation does. Swapped to read the variable properly.
- **Table row hover and selection** (`.ia_tableComponent__body__row--hovered`,
  `.ia_tableComponent__selection`, `.ia_alarmJournalTableComponent__selection`,
  `.ia_alarmStatusTableComponent__selection`) — the highest-traffic hard-code
  found, since every table hits it. `!important` here because IA's own
  declarations carry the same specificity and would otherwise win on source
  order alone from within the same imported base stylesheet.

Separately, and by the same `globals.css` mechanism, **scrollbars follow the
theme**: `scrollbar-color` and the `::-webkit-scrollbar-*` rules use the
theme's own `--containerBorder` for the thumb and `--callToAction` on hover,
since stock themes leave scrollbars at browser default regardless of theme.

### The occlusion-fix rule

Every `globals.css` emits, alongside the page background:

```css
#app-container .center.view-parent > .view.ia_container--root {
  background-color: transparent !important;
}
```

Perspective's own top-level view root — the element carrying both `.view` and
`.ia_container--root` — paints itself opaque with the theme's own
`--containerRoot`, one level inside `#app-container`. That is stock behaviour
for any `ia_container--primary` root container, not a bug in any project's
view JSON, and it hides the page background on every ordinary page in every
theme unless punched through. The selector is a structural Perspective shell
pattern rather than something specific to one theme, so the fix generalises
unchanged across all ten.

## The style-class contract

A theme is CSS only, and the conventional reading is that it therefore cannot
ship Perspective style classes. The first half is true; the conclusion is not,
and the difference is what lets a project drop a look-and-feel parent
entirely.

**Perspective emits whatever string sits in `style.classes` into the DOM as a
`psc-<string>` class, resource or no resource.** So a theme's `globals.css` —
just CSS served gateway-wide — can define `.psc-st\/containers\/card` and carry
a whole semantic class contract. What is lost is only the Designer's
style-class picker dropdown, which costs nothing for a UI that is generated
rather than hand-assembled.

`build_contract.py` appends that payload to each theme's `globals.css`, in
cascade order:

1. the theme's 40 `--st-*` tokens, hoisted to `:root`;
2. `contract/chrome.css` verbatim — component chrome, shell and card grid,
   written against `[class*="/family/name"]` attribute selectors;
3. the 69-class contract, from each class's own definition.

Two things worth knowing if you build on it or extend it:

**Keep the slashes.** `st/containers/card`, not `st-containers-card`. Part 2 is
keyed on `[class*="/tables/frame"]`-style attribute selectors, and slash names
let 585 lines of chrome port byte for byte.

**Double the selector; never use `!important`.** A theme loads *before* IA's
own `PerspectiveComponents.css`, whereas a project style-class bundle loads
*after* it — so moving a contract into a theme flips it from winning ties to
losing them. Measured: `buttons/chip` silently dropped its `padding: 0 12px`
to IA's `0`. `!important` fixes that but also beats *inline* styles, which
inverts Perspective's own precedence and breaks every per-component override
(measured: it forced topbar and sidebar padding over the components' own
props). Doubling the class — `.psc-st\/x\/y.psc-st\/x\/y`, specificity 0-2-0 —
beats IA's 0-1-0 component rules and still loses to inline, which is exactly
how a real style class behaves.

The installer's Customise page says how many classes a theme publishes and
whether that is the standard contract, read from the gateway live.

## Installing the files by hand

**Manual alternative** — if you would rather not run a shell script against a
gateway you do not fully trust yet, copy each theme folder yourself to the
same destination path, preserving the five files inside each (`config.json`,
`index.css`, `variables.css`, `globals.css`, `resource.json`), then match
ownership to a sibling shipped theme directory by hand.

Then run the scan, and verify:

### Verify

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://<gateway>/data/perspective/themes/<theme-id>.css
```

should return `200` for each installed theme id.

### Uninstall

Delete each theme's directory under `.../themes/<theme-id>/` and run the same
Overview config scan again. There is no separate gateway-side registry to
clean up — the config resource *is* the directory.

## Selecting a theme by hand

A Perspective session's theme is `session.props.theme` — bindable and
session-wide, as opposed to the page-scoped `system.perspective.setTheme()`. A
minimal dropdown bound to it:

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

`out/themes.json` carries the same id/label/dark-flag list as data, if you
would rather build the options from a script than hand-write them. Or use one
of the two switchers below, which build the list from the gateway itself.

## The glass-green tweak

`glass-green` (source pack `aurora-teal`) originally read as *violet with a
teal accent* rather than a genuine green-glass theme. Root cause: the pack's
`surface.page`/`surface.card`/`surface.sidebar` tokens were never diverged
from `aurora-violet` when the pack was cloned — both packs' `surface.page` is
the literal `"#1a1233"`, violet. Only the accent-adjacent tokens actually
changed. A stylesheet-based renderer never showed this, because it reads
`containers/page`'s *effective* `backgroundColor` override (already a correct
dark teal) rather than the raw `surface.page` token; this generator reads the
raw token, which is what let the violet leak through into a *theme*
specifically.

Fixed entirely in `mapping.TWEAKS["glass-green"]` — `packs/aurora-teal.json`
is untouched. The tweak recomputes the surface stack from a new near-black
green-tinted base (`#0d1412`) using the pack's own existing translucent
white-glass alpha values, so the *glass effect* is unchanged and only what it
sits on differs, and moves the accent from the pack's muted teal (`#0f766e`)
to a brighter mint (`#2dd4bf`, hover `#5eead4`, active `#26b4a2`) with a fresh
green `--success`. Every downstream variable that `ref:`s the accent, plus the
chart scales and the compensating rules, inherits the fix automatically.
`glass-violet` has no tweak and is unmodified.

Everything else about the repo layout and the build steps is in
[docs/INTERNALS.md](docs/INTERNALS.md#what-is-where).

## What is where

- `packs/` — the ten source colour packs, each a JSON token set.
- `mapping.py` — the curated token → built-in-Perspective-variable table, in
  three parts (read its module docstring for the full grammar):
  - `MAPPING`, the core ~35 IA variables, resolved straight from a pack;
  - `EXTENDED_MAPPING`, a second pass resolved after `MAPPING` and any
    `TWEAKS`, so it can `ref:` the final values;
  - `TWEAKS`, per-theme literal overrides — data, not code — applied between
    the two passes. Only `glass-green` has an entry today.
- `build_theme.py` — the generator: resolves `MAPPING` against the pack,
  applies `TWEAKS[id]`, resolves `EXTENDED_MAPPING`, generates the three chart
  scales, writes `out/<id>/`.
- `build_contract.py` — appends the `--st-*` / `st/...` contract payload to
  each theme's `globals.css`. Its inputs are vendored under `contract/`.
- `build_installer.py` — regenerates `installer-project/Theme_Installer/` from
  scratch, embedding every theme's file contents as data in a gateway-scope
  script (`ignition/script-python/themepack/code.py`). Data-dir resolution is
  `IgnitionGateway.get().getSystemManager().getDataDir()`, verified live on
  8.3.8. Install writes the files then requests one config scan; uninstall
  goes through `system.config.delete()` instead. Every write is whitelisted
  against whatever `out/` held at build time — there is no code path that can
  reach `light`, `dark`, `light-cool`, `light-warm`, `dark-cool` or
  `dark-warm`.
- `out/<theme-id>/` — the ten generated theme directories, each with
  `config.json`, `index.css`, `variables.css`, `globals.css` and
  `resource.json`. This is exactly what gets deployed to
  `data/config/resources/core/com.inductiveautomation.perspective/themes/<id>/`.
- `insight/` — the capture scripts used to read a live gateway's stock
  palettes for the audits above.
- `editor/` — the hand-authored half of the Customise page's script library,
  appended verbatim to the generated `themepack/code.py` by
  `build_installer.py`.
- `selector-popup/` — the two copy-me switcher views as hand-authored JSON.
  `build_installer.py` copies them into the generated project verbatim and
  builds only their `resource.json`.
- `themes-test-project/Themes_Test/` — a bare Perspective project with no
  parent, no stylesheet resource and no style classes, used to prove a theme
  restyles a project on its own and to shoot the README screenshots. Import it
  alongside the installer if you want to see a theme applied to something other
  than the installer's own pages.
- `tools/sync-packs.sh` — historical. It re-pulled `packs/` from the retired
  styles-template-v2 repo, which no longer exists anywhere; `packs/` here is
  the source of truth for these ten now, and the script refuses to run rather
  than fail ten times over. Kept only so the provenance is not lost.
- `docs/THEMES-EVALUATION.md` — the evaluation this project grew out of: what
  a theme can and cannot reach, whether themes paint earlier than a project
  stylesheet, and what a look-and-feel parent still buys on top of one.

`resource.json` deliberately carries no `lastModification` or
`lastModificationSignature`. The gateway must stamp those itself on first
scan — a hand-written signature that does not match the content makes the
config scan **silently** skip the resource.

### The glass-green tweak

`glass-green` (source pack `aurora-teal`) originally read as *violet with a
teal accent* rather than a genuine green-glass theme. Root cause: the pack's
`surface.page`/`surface.card`/`surface.sidebar` tokens were never diverged
from `aurora-violet` when the pack was cloned — both packs' `surface.page` is
the literal `"#1a1233"`, violet. Only the accent-adjacent tokens actually
changed. A stylesheet-based renderer never showed this, because it reads
`containers/page`'s *effective* `backgroundColor` override (already a correct
dark teal) rather than the raw `surface.page` token; this generator reads the
raw token, which is what let the violet leak through into a *theme*
specifically.

Fixed entirely in `mapping.TWEAKS["glass-green"]` — `packs/aurora-teal.json`
is untouched. The tweak recomputes the surface stack from a new near-black
green-tinted base (`#0d1412`) using the pack's own existing translucent
white-glass alpha values, so the *glass effect* is unchanged and only what it
sits on differs, and moves the accent from the pack's muted teal (`#0f766e`)
to a brighter mint (`#2dd4bf`, hover `#5eead4`, active `#26b4a2`) with a fresh
green `--success`. Every downstream variable that `ref:`s the accent, plus the
chart scales and the compensating rules, inherits the fix automatically.
`glass-violet` has no tweak and is unmodified.
