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
            state = "only in %s" % against
        elif other is None:
            state = "added"
        elif mine == other:
            state = "inherited"
        else:
            state = "overridden"
        rows.append({
            "variable": name,
            "value": mine or "",
            "compared": other or "",
            "state": state,
            "why": why.get(name, ""),
        })
    return rows


def summary(theme_id, against=None):
    """The headline counts, and the layer breakdown beside them."""
    rows = compare(theme_id, against)
    counts = {"inherited": 0, "overridden": 0, "added": 0}
    for row in rows:
        if row["state"] in counts:
            counts[row["state"]] += 1
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


def _readable(selector):
    """A doubled contract selector reads as one name, not two."""
    parts = selector.replace("\\", "").split(".")
    seen, out = set(), []
    for part in parts:
        if part and part not in seen:
            seen.add(part)
            out.append(part)
    return ".".join(out)


def contract(theme_id):
    """The --st-* tokens a project can rely on, with their live values."""
    css = theme_css(theme_id)
    ours = _vars_of(css)
    users = _token_users(css)
    rows = []
    for name in sorted(ours):
        if not name.startswith("--st-"):
            continue
        where = [_readable(sel) for sel in users.get(name, [])]
        shown = ", ".join(where[:3])
        if len(where) > 3:
            shown += "   (+%d more)" % (len(where) - 3)
        rows.append({
            "token": name,
            "value": ours[name],
            "uses": len(where),
            "where": shown,
        })
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
