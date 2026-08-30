# ---------------------------------------------------------------------------
# INSIGHT -- what these themes actually change.
#
# Hand-authored, commit-tracked, appended verbatim to themepack/code.py by
# build_installer.py (same pattern as selector-popup/). Everything below reads
# the LIVE gateway, never a figure baked in at build time: a page that quotes
# build-time numbers is a document that goes stale silently, and the whole
# point of these pages is to show what is actually installed right now.
# ---------------------------------------------------------------------------

_VAR_RE = re.compile(r'^[ \t]*(--[A-Za-z0-9_-]+)[ \t]*:[ \t]*([^;]+);', re.M)
_CLASS_RE = re.compile(r'^\.psc-st\\/([A-Za-z0-9/\\_-]+?)\.psc-st\\/', re.M)

# What a theme is built out of. index.css is literally three lines, and that
# is the honest answer to "what is going on": we do not replace Ignition's
# theme, we import it and then override on top.
LAYERS = [
    ("Ignition's own theme", "index.css imports light or dark from the "
     "Perspective module. Everything we do not name keeps working because "
     "this layer is still underneath it."),
    ("variables.css", "Re-points Ignition's OWN variable names at the pack's "
     "palette. This is why stock components restyle without being touched "
     "individually."),
    ("globals.css", "The part with no stock equivalent: scrollbars, "
     "compensation for colours Ignition hard-codes, the --st-* tokens, "
     "component chrome, and the st/... class contract."),
]


# ---------------------------------------------------------------------------
# Making the lists readable.
#
# The first version of these pages listed 110 variables alphabetically --
# --arrow-color, --black, --border, --borderRadius -- with a "state" column
# saying "overridden". Every fact on the page was true and none of it was
# clear: an alphabetical list of Ignition's internal variable names tells a
# first-time reader nothing about what the theme actually does to their
# screens. Grouping by what a variable AFFECTS is the difference between a
# reference and an explanation.
# ---------------------------------------------------------------------------

# Ordered: what somebody wants to know first comes first. A variable lands in
# the first group whose pattern matches, so order is also precedence.
GROUPS = [
    ("Page and card surfaces",
     r'^--(containerRoot|container|containerNested|contextBackground|'
     r'tooltip-background-color|neutral-([1-8]0))$'),
    ("Text and icons",
     r'^--(label|icon|arrow-color|neutral-(90|100))'),
    ("Accent and buttons",
     r'^--(callToAction|indicator)'),
    ("Borders and corners",
     r'^--(border|containerBorder)'),
    ("Inputs and controls",
     r'^--(input|checkbox|radio|toggleSwitch|defaultSlider)'),
    ("Status colours",
     r'^--(error|warning|success|info)'),
    ("Depth and shadows",
     r'^--boxShadow'),
    ("Progress bars",
     r'^--progress'),
    ("P&ID symbols and pipes",
     r'^--(symbol|pipe)'),
    ("Chart palettes",
     r'^--(qual|seq|div)-'),
]

TOKEN_GROUPS = [
    ("Page and surfaces", r'^--st-(page|card|topbar|sidebar)'),
    ("Text", r'^--st-(fg|chrome-fg|on-accent)$'),
    ("Accent", r'^--st-accent$'),
    ("Buttons", r'^--st-btn-'),
    ("Tables", r'^--st-(head|cell|row|table)'),
    ("Inputs", r'^--st-input'),
    ("Tabs and navigation", r'^--st-(tab|nav)'),
    ("Borders", r'^--st-(chrome-border|.*-border)$'),
    ("Type and spacing", r'^--st-(.*-font|.*-pad|row-min)$'),
]

# Expanded for readability. These are the abbreviations in our OWN token
# names, so this is a lookup, not a guess about someone else's naming.
WORDS = {
    "st": "", "btn": "button", "dan": "danger", "gho": "ghost",
    "pri": "primary", "bg": "background", "fg": "text", "head": "table header",
    "chrome": "sidebar and header", "nav": "navigation", "pad": "padding",
    "fx": "effect", "min": "minimum height", "solid": "(opaque)",
    "tab": "tab", "row": "table row", "cell": "table cell",
    "chip": "identity chip", "brand": "brand", "group": "group heading",
    "rule": "divider", "card": "card", "page": "page", "topbar": "top bar",
    "sidebar": "sidebar", "input": "input", "table": "table",
    "accent": "accent", "border": "border", "active": "selected",
    "inactive": "unselected", "on": "text on the", "font": "font size",
}

_COLOUR_RE = re.compile(r'^(#[0-9A-Fa-f]{3,8}|rgba?\(|hsla?\()')
_NOISE_RE = re.compile(r'\s*\((?:token|ref):[^)]*\)\s*$')


def group_of(name, groups):
    for label, pattern in groups:
        if re.search(pattern, name):
            return label
    return "Everything else"


def is_colour(value):
    """Whether a value can be painted as a swatch.

    Deliberately strict: a var(--x) reference, a shadow, a length or the
    keyword transparent all fail, and a swatch of a value that is not a colour
    is worse than no swatch -- it renders as an empty box that reads as a bug.
    """
    return bool(value and _COLOUR_RE.match(value.strip()))


def swatch(value):
    if not is_colour(value):
        return {"value": "", "style": {}}
    return {"value": "", "style": {"backgroundColor": value.strip()}}


LIMIT = 150


def plain(name, comment=""):
    """A human sentence for one variable.

    Prefers the derivation build_theme.py recorded, minus its machine suffix:
    `(token:surface.page)` and `(ref:--border)` are for us, not for a reader
    meeting these themes for the first time. Falls back to expanding our own
    abbreviations for the --st-* tokens, which carry no comment at all.
    """
    if comment:
        text = _NOISE_RE.sub("", comment).strip()
        if len(text) > LIMIT:
            text = text[:LIMIT].rsplit(" ", 1)[0] + " ..."
        return text
    parts = [p for p in name.lstrip("-").split("-") if p and p != "st"]
    if len(parts) == 3 and parts[0] == "btn":
        # btn-dan-bg reads "Danger button background", not "Button danger
        # background": the variant qualifies the noun, it does not follow it.
        return ("%s button %s" % (WORDS.get(parts[1], parts[1]),
                                  WORDS.get(parts[2], parts[2]))).capitalize()
    words = [WORDS.get(part, part) for part in parts]
    return " ".join(w for w in words if w).strip().capitalize()


def _gateway_port():
    """This gateway's own HTTP port, read from data/gateway.xml.

    Never hardcoded. The resolved CSS is only reachable over HTTP -- the base
    light/dark sheets live inside the Perspective module, not on disk -- so a
    gateway on a non-default port would fail the fetch, and a failed fetch
    read as an empty base would report every single variable as "added by us".
    Wrong in the most flattering possible direction, which is the kind of
    wrong worth engineering against.
    """
    try:
        handle = open(os.path.join(_data_dir(), "gateway.xml"))
        try:
            xml = handle.read()
        finally:
            handle.close()
        found = re.search(r'"gateway\.port"\s*>\s*(\d+)', xml)
        if found:
            return int(found.group(1))
    except (Exception, Throwable), e:
        pass
    return 8088


def theme_css(theme_id):
    """The fully resolved stylesheet the browser actually receives.

    Not our source files: this is post-@import, exactly what is served, so it
    includes the base theme we build on and reflects any local edit somebody
    made to the installed copy.
    """
    return system.net.httpGet("http://localhost:%d/data/perspective/themes/%s.css"
                              % (_gateway_port(), theme_id))


def _vars_of(css):
    """Every custom property the sheet ends up defining. LAST definition wins.

    Last-wins is not a detail, it is the measurement. Our variables.css is
    imported after the base, so reading first-wins reports zero overrides and
    makes the themes look like they change nothing at all. That is exactly
    what the first version of this said.
    """
    found = {}
    for match in _VAR_RE.finditer(css):
        found[match.group(1)] = match.group(2).strip()
    return found


def _reasons(theme_id):
    """The generated 'why' comment beside each variable in our own source.

    build_theme.py writes a derivation next to every value it emits
    (`--containerRoot: #2e3540; /* page background, flattened over white
    (token:surface.page) */`). Those comments are stripped from what the
    browser gets, so they are read from the embedded copy instead -- which
    also means the reason still shows for a theme that is not installed.
    """
    out = {}
    theme = THEMES.get(theme_id)
    if not theme:
        return out
    source = theme["files"].get("variables.css", "") + theme["files"].get("globals.css", "")
    for line in source.split("\n"):
        match = re.match(r'^\s*(--[A-Za-z0-9_-]+)\s*:[^;]*;\s*/\*\s*(.*?)\s*\*/\s*$', line)
        if match:
            out[match.group(1)] = match.group(2)
    return out


def base_of(theme_id):
    """Which stock theme this one is built on -- read from its own index.css."""
    theme = THEMES.get(theme_id)
    if theme:
        if re.search(r'@import\s+"\.\./dark/', theme["files"].get("index.css", "")):
            return "dark"
        return "light"
    return "dark" if STOCK_DARK.get(theme_id) else "light"


def compare(theme_id, against=None):
    """Row per custom property: what we inherit, override, and add.

    `against` defaults to the stock theme this one is built on, which is the
    comparison that answers "what did you change". Passing another theme id
    answers "how do these two differ", using the identical machinery.
    """
    if against is None:
        against = base_of(theme_id)
    ours = _vars_of(theme_css(theme_id))
    theirs = _vars_of(theme_css(against))
    why = _reasons(theme_id)

    rows = []
    for name in sorted(set(ours) | set(theirs)):
        mine, other = ours.get(name), theirs.get(name)
        if mine is None:
            continue          # only in the comparison: not a change WE made
        if other is None:
            state = "new"
        elif mine == other:
            state = "kept as Ignition's"
        else:
            state = "repainted"
        rows.append({
            "group": group_of(name, GROUPS),
            "variable": name,
            "what": plain(name, why.get(name, "")),
            "swatch": swatch(mine),
            "value": mine,
            "compared": other or "-",
            "state": state,
        })
    # Grouped, in the order GROUPS declares. Alphabetical was the whole
    # problem: it interleaves chart palettes with page surfaces.
    order = dict((label, i) for i, (label, _) in enumerate(GROUPS))
    rows.sort(key=lambda r: (order.get(r["group"], len(order)), r["variable"]))
    return rows


def summary(theme_id, against=None):
    """The headline counts, and the layer breakdown beside them."""
    rows = compare(theme_id, against)
    counts = {"inherited": 0, "overridden": 0, "added": 0}
    tally = {"kept as Ignition's": "inherited", "repainted": "overridden",
             "new": "added"}
    for row in rows:
        key = tally.get(row["state"])
        if key:
            counts[key] += 1
    theme = THEMES.get(theme_id, {"files": {}})
    globals_css = theme["files"].get("globals.css", "")
    counts["base"] = against or base_of(theme_id)
    counts["total"] = len(rows)
    counts["tokens"] = len([r for r in rows if r["variable"].startswith("--st-")])
    counts["classes"] = len(set(_CLASS_RE.findall(globals_css)))
    return counts


_RULE_RE = re.compile(r'([^{}]+)\{([^}]*)\}', re.M)


def _token_users(css):
    """token -> the selectors in this theme that actually consume it.

    The --st-* tokens carry no derivation comment (unlike the variables.css
    values, which do), so there is no "why" to quote for them. Rather than
    ship a column that is empty on every row, this answers the question a
    reader actually has -- "what does this token affect?" -- by reading the
    theme's own rules. Measured from the artefact, so it cannot describe a use
    the theme does not have.
    """
    users = {}
    for match in _RULE_RE.finditer(css):
        group = " ".join(match.group(1).split())
        if group.startswith("@") or group == ":root":
            continue
        # One rule can carry a comma-separated selector GROUP. Count the
        # selectors, not the rules: a count of 3 printed beside six visible
        # selectors reads as a bug in the page.
        selectors = [sel.strip() for sel in group.split(",") if sel.strip()]
        for token in set(re.findall(r'var\((--st-[a-z0-9-]+)', match.group(2))):
            users.setdefault(token, []).extend(selectors)
    return users


# What a selector is TALKING ABOUT, in words. The raw text is unusable on a
# page meant for a first-time reader: one --st-sidebar-solid consumer is
# `ia_popup:has(> .body-wrapper > .popup-body > [class*="/containers/page"]) >
# .popup-header`, which is correct, precise, and tells nobody anything. Order
# matters -- the contract class is the most specific answer, so it wins.
PLACES = [
    (r'/containers/page', "page containers"),
    (r'/containers/card', "cards"),
    (r'/tables/', "tables"),
    (r'/buttons/danger', "danger buttons"),
    (r'/buttons/primary', "primary buttons"),
    (r'/buttons/ghost', "ghost buttons"),
    (r'/buttons/', "buttons"),
    (r'/text/brand', "the brand mark"),
    (r'/nav/', "navigation items"),
    (r'/inputs/', "inputs"),
    (r'psc-st-shell', "the app shell"),
    (r'ia_popup|popup-', "popups"),
    (r'ia_tabContainer|tab-menu', "tab strips"),
    (r'ia_pager', "table pagers"),
    (r'ia_table', "tables"),
    (r'scrollbar', "scrollbars"),
    (r'\bbutton\b', "buttons"),
    (r'ia_label', "labels"),
]


def _readable(selector):
    """One selector, as the thing it styles."""
    for pattern, place in PLACES:
        if re.search(pattern, selector):
            return place
    # Nothing recognised: fall back to the bare class name rather than the
    # whole selector chain, which is what made this column unreadable.
    bare = re.findall(r'[.#]([A-Za-z][A-Za-z0-9_-]+)', selector.replace("\\", ""))
    return bare[-1] if bare else selector[:40]


def contract(theme_id):
    """The --st-* tokens a project can rely on, with their live values."""
    css = theme_css(theme_id)
    ours = _vars_of(css)
    users = _token_users(css)
    why = _reasons(theme_id)
    rows = []
    for name in sorted(ours):
        if not name.startswith("--st-"):
            continue
        seen, where = set(), []
        for sel in users.get(name, []):
            place = _readable(sel)
            if place not in seen:
                seen.add(place)
                where.append(place)
        shown = ", ".join(where[:4])
        if len(where) > 4:
            shown += " (+%d more)" % (len(where) - 4)
        rows.append({
            "group": group_of(name, TOKEN_GROUPS),
            "token": name,
            "what": plain(name, why.get(name, "")),
            "swatch": swatch(ours[name]),
            "value": ours[name],
            "where": shown or "-",
        })
    order = dict((label, i) for i, (label, _) in enumerate(TOKEN_GROUPS))
    rows.sort(key=lambda r: (order.get(r["group"], len(order)), r["token"]))
    return rows


def contract_classes(theme_id):
    """Every st/... class this theme publishes, and what each one sets.

    Read out of the theme's own globals.css rather than a list kept beside it,
    so the page cannot claim a class the theme does not actually ship.
    """
    theme = THEMES.get(theme_id)
    if not theme:
        return []
    css = theme["files"].get("globals.css", "")
    rows = []
    for match in re.finditer(
            r'^\.psc-st\\/([A-Za-z0-9/\\_-]+?)\.psc-st\\/[A-Za-z0-9/\\_-]+?\s*\{([^}]*)\}',
            css, re.M):
        name = match.group(1).replace("\\", "")
        sets = []
        for decl in match.group(2).split(";"):
            if ":" in decl:
                sets.append(decl.split(":", 1)[0].strip())
        rows.append({
            "family": name.split("/")[0],
            "klass": "st/" + name,
            "sets": ", ".join(sets),
            "count": len(sets),
        })
    return sorted(rows, key=lambda r: r["klass"])


def layers(theme_id):
    """The three-layer anatomy, with this theme's real numbers attached."""
    counts = summary(theme_id)
    theme = THEMES.get(theme_id, {"files": {}})
    detail = [
        "%s -- inherited untouched by this theme: %d of %d variables"
        % (counts["base"], counts["inherited"], counts["total"]),
        "%d variables overridden, %d lines"
        % (counts["overridden"], len(theme["files"].get("variables.css", "").split("\n"))),
        "%d --st-* tokens, %d st/... classes, %d lines"
        % (counts["tokens"], counts["classes"],
           len(theme["files"].get("globals.css", "").split("\n"))),
    ]
    return [{"layer": LAYERS[i][0], "what": LAYERS[i][1], "here": detail[i]}
            for i in range(3)]


def headline(theme_id, against=None):
    """The plain-English answer, in one sentence, with the real numbers in it.

    A first-time reader should not have to add up four tiles to work out what
    the theme does. This is the sentence they would otherwise have to assemble
    themselves.
    """
    counts = summary(theme_id, against)
    label = THEMES.get(theme_id, {}).get("label", theme_id)
    return ("%s is built on Ignition's %s theme and repaints it: %d of its "
            "variables carry this pack's values, %d are left exactly as "
            "Ignition set them, and %d are new. Nothing is replaced wholesale "
            "-- anything the theme never names behaves as stock."
            % (label, counts["base"], counts["overridden"],
               counts["inherited"], counts["added"]))

# ---------------------------------------------------------------------------
# Previews: the lay answer.
#
# Everything above measures; none of it SHOWS. A first-time reader -- told
# "108 variables repainted" -- still has no idea what any theme looks like.
# So the pages now paint each theme as a miniature screen (top bar, sidebar,
# card, button, table) whose colours are the theme's real values, read from
# the same data everything else here uses. Ten of those side by side answer
# "what is this project?" faster than any table on this gateway.
# ---------------------------------------------------------------------------

def _theme_vars(theme_id):
    """Every variable a theme defines, from the embedded copy when we have one.

    The embedded copy means a theme's preview renders even when the theme is
    not installed yet -- which is exactly when someone is deciding whether to
    press Install. Stock light/dark have no embedded copy (they live inside
    the Perspective module), so those two go over HTTP like the diffs do.
    """
    theme = THEMES.get(theme_id)
    if theme:
        merged = {}
        for filename in ("variables.css", "globals.css"):
            for match in _VAR_RE.finditer(theme["files"].get(filename, "")):
                merged[match.group(1)] = match.group(2).strip()
        return merged
    return _vars_of(theme_css(theme_id))


def palette(theme_id):
    """The dozen colours the miniature screen is painted with.

    Prefers the theme's own --st-* tokens and falls back to the stock variable
    for the same surface, so one function serves both our themes and
    Ignition's light/dark.
    """
    v = _theme_vars(theme_id)

    def resolve(value, depth=0):
        """Follow var(--x) to a literal.

        Ignition's own light and dark define almost everything as
        var(--neutral-NN), so without this the two 'what you start with'
        previews come back holding CSS references rather than colours -- and a
        var() that means nothing in the previewing page renders as the SESSION
        theme's colour, quietly showing the wrong thing rather than nothing.
        """
        seen = 0
        while value and value.startswith("var(") and seen < 6:
            name = re.match(r'var\(\s*(--[A-Za-z0-9_-]+)', value)
            if not name:
                return ""
            value = v.get(name.group(1), "")
            seen += 1
        return value if value and not value.startswith("var(") else ""

    def pick(*names):
        for name in names:
            value = resolve(v.get(name, "").strip())
            if value and value != "transparent":
                return value
        return ""
    page = pick("--st-page-solid", "--containerRoot")
    return {
        "page":     page,
        "sidebar":  pick("--st-sidebar-solid", "--containerNested", "--container"),
        "card":     pick("--st-card", "--container"),
        "text":     pick("--st-fg", "--label"),
        "muted":    pick("--label--disabled", "--st-fg", "--label"),
        "chromeFg": pick("--st-chrome-fg", "--label"),
        "accent":   pick("--st-accent", "--callToAction"),
        "onAccent": pick("--st-on-accent") or "#ffffff",
        "border":   pick("--st-chrome-border", "--border"),
        "headBg":   pick("--st-head-solid", "--containerNested", "--container"),
        "headFg":   pick("--st-head-fg", "--label"),
        "rowBg":    pick("--st-row-bg") or page,
        "cellFg":   pick("--st-cell-fg", "--label"),
    }


def preview_instances(kind="custom"):
    """Instances for the gallery's flex-repeater: one painted screen per theme.

    kind="stock" returns just Ignition's own light and dark, so the gallery
    can show what a gateway starts with directly above what this project
    turns it into -- which IS the explanation, with no sentence attached.
    """
    out = []
    if kind == "stock":
        for theme_id, label in (("light", "Ignition light"),
                                ("dark", "Ignition dark")):
            try:
                entry = palette(theme_id)
            except (Exception, Throwable), e:
                continue      # gateway fetch failed: show fewer, never break
            entry["label"] = label
            entry["caption"] = "what every gateway starts with"
            out.append(entry)
        return out
    installed = set()
    try:
        for row in status():
            if row.get("kind") == "custom" and row.get("installed"):
                installed.add(row["id"])
    except (Exception, Throwable), e:
        pass
    for theme_id in THEME_ORDER:
        entry = palette(theme_id)
        theme = THEMES[theme_id]
        entry["label"] = theme["label"]
        entry["caption"] = ("%s · %s" % (
            "dark" if theme["dark"] else "light",
            "installed" if theme_id in installed else "not installed yet"))
        out.append(entry)
    return out
