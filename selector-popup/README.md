# The theme switchers

Two copy-me views, either of which lets a user change the theme of their own
session. A project takes whichever suits it, or both:

| File | `Theme_Installer` view | What it is |
| ---- | ---------------------- | ---------- |
| `SelectorPopup.view.json` | `views/SelectorPopup` | The swatch grid, opened as a popup. Each theme is a button in its own colours, so you can see what you are picking. |
| `ThemeDropdown.view.json` | `views/ThemeDropdown` | One dropdown, 34px tall. Embeds in a header or a settings row and takes no space. |

`Theme_Installer`'s own page demonstrates both: the **Theme switcher** button
opens the popup, and the dropdown beside it is `views/ThemeDropdown` embedded
rather than duplicated, so what is on that page is the same file a project
would copy.

The two are **independent on purpose** — each carries its own copy of the
listing script rather than sharing one — so copying either into a project
drags nothing else in. That duplication is the price of self-containment and
is deliberate.

## Both read the gateway, not a list in the file

Neither view is allowed to offer a theme that is not on the gateway. Both ask
`system.config.getResources(moduleId="com.inductiveautomation.perspective",
typeId="themes")` when they open, and both add Ignition's six stock themes as
a fixed base — `light` and `dark` live inside the Perspective module's own jar
and never appear as config resources, so they cannot be discovered.

That matters because these views are meant to be copied into projects on
gateways that this pack was never installed on (Nigel, 28/08/2026). A hard
coded row for `glass-violet` on a gateway without it writes an id Perspective
cannot resolve into `session.props.theme`; a listed one cannot be offered at
all. It also means a theme from somewhere else entirely — another vendor's
pack, a hand-written one — appears in both without either file being edited.

The **swatch grid stays a fixed, hand-coloured list** (the colours cannot be
read out of a theme's CSS by a view binding), but the listing decides which of
its buttons are *offered*: each swatch binds `props.style.display` to
`indexOf({view.custom.gateway.have}, ",<id>,") >= 0`. The section heading
counts what is there — "Custom · 10 themes" when all ten are, "Custom · 3 of
10 on this gateway" when they are not — and when none are, the grid is
replaced by a line saying so and pointing at the dropdown below it.

Both halves of the popup read **one** listing (`view.custom.gateway`, bound
once when the popup opens), so the swatches and the dropdown can never
disagree about what the gateway has.

Two things learned wiring that up, both measured on 8.3.8:

- **`ia.display.label` ignores `props.style.display`.** It writes its own
  `display: flex` into the same inline style and wins, so a label bound to
  `"none"` stays on screen. `ia.input.button` and `ia.container.flex` both
  honour it. The empty-state line is therefore a one-child flex container with
  the binding on the container.
- **A dropdown's menu is not inside the popup.** Perspective renders it in a
  portal at document level (`.ia_componentModal`), so it is not clipped by a
  short popup frame — and, checked directly, picking from it does **not**
  dismiss a popup opened with `overlayDismiss=True`.
- **A config scan racing a `system.config.delete()` can leave a resource
  listed.** Ignition renames a deleted resource's directory to
  `<name>.deleted-<id>`; with a scan fired straight after **Remove custom
  themes**, two of the ten stayed in `getResources()` — and so in both
  switchers — across repeated reads several minutes apart, before being reaped.
  Pressing the button on its own is clean: 16 themes to 6 within five seconds,
  and 6 back to 16 within five of pressing Install. `system.config.delete()`
  needs no scan of its own, so do not give it one.

## How the popup is built

It is **hand-adapted and commit-tracked**, not generated: `build_installer.py`
copies this file verbatim into the built project and writes its
`resource.json` (no signature, timestamp from the clock) — the same way it
treats `ignition/script-python/themepack/`. It is not derived from `out/` at
build time; the 10 swatches' hex values are static, hand-verified against
`out/` once per swatch (see below), the way the original author built it.

**We own this file outright now.** `source-switcher-view.json` next to it is
kept only for provenance/audit trail — it is the as-handed-over popup from
another project that built the same picker for its own multi-project switcher
rig, and it is never read by any script in this repo. Edit `SelectorPopup.view.json`
directly for any future change; do not regenerate it from the source snapshot.

## Where it came from

Built against this repo's `out/` theme data for another project's switcher rig,
and handed back as `source-switcher-view.json` (818 lines) with three adaptations specified by
its own author for landing here:

1. Every swatch button wrote `self.session.custom.styleOverride` — that repo's
   own two-layer preview/commit convention (`session.custom.style` = the
   committed pack, `styleOverride` = a same-session preview layered on top,
   with a separate "Apply everywhere" step to broadcast the commit to other
   sites). `Theme_Installer` has neither layer, so every row now writes
   `self.session.props.theme` directly — an ordinary Perspective session
   property, no indirection, nothing else in this project binds it.
2. The two section labels ("hint", "Custom · N themes") bound
   `props.style.classes` to `{session.custom.style} + '/text/muted'` — that
   repo's per-theme style-class convention (an inheritable parent project
   supplying named classes per pack). This project has no such parent and no
   style classes at all; both labels now carry a plain
   `color: var(--label--disabled)` in their own `style` object instead, and
   `propConfig` was dropped from both.
3. The stock-IA section had a caveat label reading "Ignition · stock
   components only" — true of the *other* rig (a mostly-custom-styled
   product warning that this one section is unstyled IA chrome). Every
   component in `Theme_Installer` is a stock IA component, so the caveat is
   just wrong here. Removed.

## What this repo's own agent changed beyond that list

Found in the course of adapting it — not in the author's 3-item list:

- **Fixed the section-count label.** "Custom · 10 themes" — see the note
  below on why the number briefly went to 9 and back to 10 during this
  adaptation; not an independent judgement call by the time this landed, but
  worth being deliberate about since the label is a literal string, not
  derived from the row count.
- **Removed the "Back to committed" button** (`clear`, formerly
  `self.session.custom.styleOverride = ''`). It existed to unwind a *preview*
  back to the *committed* value in the two-layer model — with item 1 making
  every row a direct, un-previewed write to `session.props.theme`, there is
  no committed value left to revert to, and setting
  `session.props.theme = ''` would hand Perspective an empty/invalid theme id
  rather than reset anything. No replacement control was added; reloading the
  page already achieves the same thing (the session re-reads whatever
  `Theme_Installer`'s `session-props/props.json` actually sets, which today
  is nothing — the project runs under the gateway's own default theme unless
  a row here has been clicked).
- **Rewrote the "hint" label's copy.** "Previews in THIS session. Use 'Apply
  everywhere' to send it to the edges." referenced a control
  (`Theme_Installer` has no "Apply everywhere") and a concept ("the edges" —
  the other rig's multi-site broadcast) that don't exist here. Replaced with
  "Applies to this session immediately. Reload the page to reset to the
  project default." — accurate for what item 1's direct write actually does.
- **Dropped `props.defaultSize`** from the view root. Per Nigel's spec for
  the popup: the frame size is passed at the `system.perspective.openPopup()`
  call site (see "Using this in another project" below for the exact,
  verified-working call — not `props.defaultSize`). `props` is now `{}`.
- **Fixed the `system.perspective.openPopup()` call's size kwargs.** The
  spec as given was `height='min(460px, 88vh)'`, `width='min(560px, 94vw)'`
  as top-level kwargs. Neither exists: confirmed live (a Jython reflection
  probe against the deployed gateway showed `openPopup` takes no top-level
  `width`/`height` at all — unknown kwargs are silently swallowed rather
  than raising, which is exactly what made this form look like it "worked"
  while doing nothing) and against IA's own 8.1/8.3 scripting-function
  reference (width/height are keys *inside* the `position` dict, typed
  `Dictionary[String, Integer]` — pixels only, no CSS `calc()`/`min()`/`vw`
  units). Corrected to `position={'width': 560, 'height': 500}`, still
  entirely at the call site and never `props.defaultSize`.
  `viewportBound=True` (already in the call) turns out to already do the
  "never bigger than a short viewport" job the `min()`/`vw` forms were
  reaching for — verified live at a 1440×530 viewport: the frame stays its
  full requested size and is shifted to sit entirely inside, not shrunk or
  clipped. Separately, 460 (the originally specified height) left the swatch
  grid needing 17px of internal scroll to reach the bottom row, at every
  viewport height tried, not just the short one — bumped to 480, which
  cleared it with zero internal scroll for the swatch count of the day
  (10 custom + 6 stock). It is **590** now: the popup has since grown an
  "Any theme on this gateway" dropdown below the grid, worth 62px with its
  divider, measured the same way (`scrollHeight` vs `clientHeight` on the
  root container) at both a 900px and a 530px viewport.

## A mid-adaptation correction: Newsprint Dark

The source snapshot's custom row had 10 buttons, one of them
`newsprint-dark`. At the time this adaptation started, this pack shipped only
9 themes and `newsprint-dark` did not exist under `out/` — so the first pass
of this file dropped it (`themepack.THEMES` would have raised `ValueError` if
a row tried to install a theme with no embedded files).

Nigel added `newsprint-dark` as this pack's 10th curated theme
(commit `3c4e160`, concurrent with this adaptation — family `finance`, paired
both ways with `finance-ledger`) before this work finished. Re-added the
swatch rather than shipping a popup that silently omits a real theme: **the
source's own colours for it were themselves stale** by the time this was
checked (`newsprint-dark`'s accent moved from an early near-white value to an
oxblood `#b1554a` via `mapping.TWEAKS` — see that theme's own `out/` audit
trail) — so the re-added button's `backgroundColor`/`border`/`color` came
from the source snapshot (still accurate: `--container`/`--containerBorder`/
`--label` were untouched by the tweak) but `borderLeft` was re-read fresh
from the current `out/newsprint-dark/variables.css`'s `--callToAction` rather
than trusted from the snapshot. Placed immediately after `finance-ledger`
(light-left/dark-right, matching the family/pair ordering rule and, as it
happens, exactly where the original source already had it).

## What was kept exactly, unadapted

The hard-won layout geometry, verified still present in
`SelectorPopup.view.json` after every edit above:

- Every swatch button: `position.basis: "48%"`, `position.grow: 0`,
  `position.shrink: 1` — `grow: 1` was tried and rejected by the original
  author because it makes an odd-count section's last swatch stretch wide and
  misread as its own category (this pack's `custom` row is back to an even
  10 now that `newsprint-dark` is restored, but the geometry choice is
  unaffected either way).
- `wrap: "wrap"` sits directly under a row's `props`, a sibling of `style` —
  not inside `props.style`. Perspective's flex container reads wrap from
  `props.wrap`, not a CSS-style key; the source got this right and it stayed
  untouched.
- `height: "100%"` + `minHeight: "0"` on the **root** container (the popup
  frame's own child) — the opposite of what a page root normally wants
  (`overflow: auto` with no forced height), but correct for a popup: the
  frame supplies the actual pixel box from `openPopup()`'s `position`, and
  the root needs to fill it and let its own `rows` container's
  `overflow: auto` do the internal scrolling instead.
- Every curated-theme swatch's hex values (`backgroundColor`/`color`/
  `border`/`borderLeft`) — spot-checked programmatically against every one of
  the (now 10) themes' current `out/<id>/variables.css` (`--container`,
  `--label`, `--containerBorder`, `--callToAction`) before touching anything
  else; all 40 checks (10 themes × 4 values) matched exactly, including
  `glass-green`'s and `newsprint-dark`'s `mapping.TWEAKS` overrides. The hex
  values in `SelectorPopup.view.json` are therefore either left exactly as
  handed over (9 of 10 themes) or corrected against the live source of truth
  (`newsprint-dark`'s `borderLeft` only — see above).
- Family/pair ordering: the custom row's button order (glass-violet,
  glass-green, leather-light, leather-dark, finance-ledger, newsprint-dark,
  nord-light, nord-dark, industrial-light, industrial-dark) satisfies Nigel's
  ordering rule (pairs side by side, light left / dark right, reading
  `out/themes.json`'s `family`/`pair` fields) — the source snapshot already
  had every button in exactly this order, `newsprint-dark` included, so no
  reordering was needed once it was re-added. The stock row's order (light,
  dark, light-cool, dark-cool, light-warm, dark-warm) is IA's own
  stem-derived order and was left as-is.

## Using these in another project

### The dropdown

Copy the whole `views/ThemeDropdown` directory into the target project, then
drop an **Embedded View** component wherever it should sit, with
`props.path = "ThemeDropdown"`. Give it about 260px of width and 34px of
height — `views/Installer`'s own action row is a worked example.

Nothing else is required: the view reads the gateway's theme list itself and
writes `session.props.theme` itself. There is no script package to copy, no
session or custom prop to wire up, and no parent project.

If you would rather have the bare control than an embedded view, lift the
`Theme` dropdown component out of `ThemeDropdown.view.json` and paste it into
a view of your own — it is self-contained, both of its bindings included.
Watch one thing: `bidirectional` lives **inside** the value binding's
`config`, and Perspective silently ignores it anywhere else, which turns the
dropdown read-only.

### The swatch popup

Copy the whole `views/SelectorPopup` directory into the target project (or
regenerate `Theme_Installer` and lift it from there), then add a button
somewhere that calls:

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

Nothing else is required — the popup writes `session.props.theme` on its own,
no parent project, no style classes, no other session/custom props to wire
up. See `views/Installer/view.json`'s own "Theme switcher" button for a
working example.

The popup carries the ten swatches this pack ships. On a gateway that has
none of them it still works: the grid says so and the dropdown at its foot
offers whatever that gateway does have.
