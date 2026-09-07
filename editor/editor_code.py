# ---------------------------------------------------------------------------
# EDITOR -- read and write the theme files on this gateway.
#
# Hand-authored, commit-tracked, appended verbatim to themepack/code.py by
# build_installer.py (same pattern as insight/ and selector-popup/).
#
# WHY THIS EXISTS. Ectobox ship a Designer module that does exactly this, and
# it is a good tool; Nigel did not want a module for it (07/09/2026). Their
# module turned out to be one RPC interface of eleven filesystem methods over
# the same directory this file resolves, with "refresh" being an ordinary
# config scan -- nothing that needs a JVM, a Designer, or a signed .modl. So it
# lives here instead, and ships with the project import that already installs
# the themes.
#
# WHAT IT IS NOT. It is not a themes BUILD tool. The ten packs are generated
# from packs/*.json by build_theme.py and embedded in THEMES above; editing a
# file here changes what is on THIS gateway and nothing in the repo. Reinstall
# from the Installer page and your edit is gone -- which is the correct
# behaviour for a live-editing tool, and the reason read_file() reports whether
# a file still matches what the installer would write.
#
# EVERY function here re-asserts that the path it is about to touch is inside
# the themes root. The guard is not "the caller already checked" -- these are
# reachable from a Perspective page, which is reachable by anyone who can open
# the project.
# ---------------------------------------------------------------------------

# resource.json is the config-resource MANIFEST, not theme content. It is
# rewritten from the directory listing on every save (_stock_rewrite_manifest),
# so hand-editing it is at best pointless and at worst strands a theme: a
# stale lastModificationSignature makes the scan reject the whole resource.
# The editor refuses to open it rather than letting someone learn that.
EDITOR_PROTECTED = ["resource.json"]

# What the editor will open. Anything else in a theme directory is listed but
# not editable -- a font or an image has no business in a text box.
EDITOR_TEXT_SUFFIXES = [".css", ".json", ".txt", ".md", ".svg"]

# A theme file we will not let a save empty. Every one of these is load-bearing:
# an empty index.css is a theme that silently stops importing Ignition's own,
# which looks like the gateway broke rather than like a bad edit.
EDITOR_NEVER_EMPTY = ["index.css", "config.json"]


def _editor_root():
    """The themes root, normalised, with a trailing separator -- the prefix
    every guarded path is tested against."""
    root = os.path.abspath(_themes_root())
    if not root.endswith(os.sep):
        root = root + os.sep
    return root


def _editor_resolve(theme, filename=None):
    """Resolve theme[/filename] INSIDE the themes root, or raise.

    Path traversal is checked after normalisation, on the absolute path, with a
    prefix test -- not by inspecting the input for '..'. A name that survives
    normalisation and still starts with the root is safe by construction; one
    that does not is refused whatever it looks like.
    """
    root = _editor_root()
    parts = [theme] if filename is None else [theme, filename]
    for part in parts:
        if not part or not isinstance(part, basestring):
            raise ValueError("Empty name -- refusing")
        if os.sep in part or (os.altsep and os.altsep in part):
            raise ValueError("'%s' is a path, not a name -- refusing" % part)
    path = os.path.abspath(os.path.join(root, *parts))
    if not (path + os.sep).startswith(root):
        raise ValueError("'%s' resolves outside the themes root -- refusing"
                         % os.path.join(*parts))
    return path


def _editor_is_text(filename):
    lowered = filename.lower()
    for suffix in EDITOR_TEXT_SUFFIXES:
        if lowered.endswith(suffix):
            return True
    return False


def list_themes():
    """Every theme directory ON DISK, with what we know about each.

    'ours' means the id is one of the ten this project can install, so the
    Installer page can overwrite it. A theme that is not ours is still fully
    editable -- that includes the four on-disk stock variants. light and dark
    are served from inside the Perspective module jar and have no directory, so
    they do not appear here at all and cannot be edited; that is not a gap this
    file can close.
    """
    root = _themes_root()
    rows = []
    if not os.path.isdir(root):
        return rows
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        files = [f for f in sorted(os.listdir(path)) if f != "resource.json"]
        rows.append({
            "id": name,
            "ours": name in THEMES,
            "stock": name in STOCK_UPDATABLE,
            "files": len(files),
            "bytes": sum(os.path.getsize(os.path.join(path, f)) for f in files),
        })
    return rows


def list_files(theme):
    """The files in one theme directory. resource.json is listed, so the page
    can show it exists, but carries editable False."""
    d = _editor_resolve(theme)
    if not os.path.isdir(d):
        raise ValueError("No theme directory '%s' on this gateway" % theme)
    rows = []
    for name in sorted(os.listdir(d)):
        path = os.path.join(d, name)
        if not os.path.isfile(path):
            continue
        rows.append({
            "name": name,
            "bytes": os.path.getsize(path),
            "editable": _editor_is_text(name) and name not in EDITOR_PROTECTED,
            "protected": name in EDITOR_PROTECTED,
        })
    return rows


def read_file(theme, filename):
    """One file's text, plus whether it still matches what the installer would
    write for it.

    'modified' is the honest answer to "have I edited this?" and is None for a
    theme or file the installer does not ship -- absent, not false, because
    'not modified' would be a claim we cannot make about a file we have no
    reference copy of.
    """
    path = _editor_resolve(theme, filename)
    if not os.path.isfile(path):
        raise ValueError("No file '%s' in theme '%s'" % (filename, theme))
    if filename in EDITOR_PROTECTED:
        raise ValueError("'%s' is the resource manifest and is rewritten on "
                         "every save -- it is not editable" % filename)
    if not _editor_is_text(filename):
        raise ValueError("'%s' is not a text file" % filename)
    text = _read(path)
    shipped = None
    if theme in THEMES:
        shipped = THEMES[theme]["files"].get(filename)
    return {
        "theme": theme,
        "name": filename,
        "text": text,
        "bytes": len(text.encode("utf-8")),
        "modified": None if shipped is None else (text != shipped),
    }


def write_file(theme, filename, text, rescan=True):
    """Save one theme file, rewrite the manifest, and (by default) scan.

    The write is STAGED THEN RENAMED. A plain truncating write is a real hazard
    here and not a theoretical one: a config scan that reads a half-written
    file skips the resource silently and does not come back to it until
    something else in the directory changes. os.rename within one directory is
    atomic, so a reader sees either the old file or the new one.

    Pass rescan=False when saving several files in a row and scan once at the
    end -- a scan is not free, and one at the end is no less correct.
    """
    path = _editor_resolve(theme, filename)
    d = os.path.dirname(path)
    if not os.path.isdir(d):
        raise ValueError("No theme directory '%s' on this gateway" % theme)
    if filename in EDITOR_PROTECTED:
        raise ValueError("'%s' is the resource manifest and is rewritten on "
                         "every save -- it is not editable" % filename)
    if not _editor_is_text(filename):
        raise ValueError("'%s' is not a text file" % filename)
    if text is None:
        raise ValueError("No text to write")
    if filename in EDITOR_NEVER_EMPTY and not text.strip():
        raise ValueError("'%s' is load-bearing -- refusing to save it empty"
                         % filename)
    if filename.lower().endswith(".json"):
        # Fail before writing, not after the scan has rejected it. A theme
        # whose config.json will not parse is a theme that vanishes from the
        # picker with nothing on the page to say why.
        try:
            json.loads(text)
        except (Exception, Throwable), e:
            raise ValueError("'%s' is not valid JSON: %s" % (filename, e))

    staged = path + ".editor-staged"
    _write(staged, text)
    if os.path.exists(path):
        os.remove(path)          # Jython on Windows will not rename onto an
                                 # existing name; harmless on Linux.
    os.rename(staged, path)

    _stock_rewrite_manifest(d)
    if rescan:
        _rescan()
    return {"theme": theme, "name": filename,
            "bytes": len(text.encode("utf-8"))}


def create_file(theme, filename, text=""):
    """Add a file to a theme directory. Refuses to overwrite."""
    path = _editor_resolve(theme, filename)
    if not os.path.isdir(os.path.dirname(path)):
        raise ValueError("No theme directory '%s' on this gateway" % theme)
    if os.path.exists(path):
        raise ValueError("'%s' already exists in '%s'" % (filename, theme))
    if not _editor_is_text(filename):
        raise ValueError("'%s' is not a text file name" % filename)
    if filename in EDITOR_PROTECTED:
        raise ValueError("'%s' is the resource manifest -- it is written for "
                         "you" % filename)
    return write_file(theme, filename, text)


def delete_file(theme, filename):
    """Remove a file from a theme directory and rewrite the manifest.

    index.css and config.json are refused: deleting either leaves a directory
    that still registers as a theme and then renders as a broken one.
    """
    path = _editor_resolve(theme, filename)
    if filename in EDITOR_PROTECTED or filename in EDITOR_NEVER_EMPTY:
        raise ValueError("'%s' cannot be deleted -- the theme needs it"
                         % filename)
    if not os.path.isfile(path):
        return False
    os.remove(path)
    _stock_rewrite_manifest(os.path.dirname(path))
    _rescan()
    return True


def revert_file(theme, filename):
    """Put back what the installer ships for one file. Only for our ten
    themes -- there is no reference copy of anyone else's."""
    if theme not in THEMES:
        raise ValueError("'%s' is not one of this project's themes -- there is "
                         "nothing to revert to" % theme)
    shipped = THEMES[theme]["files"].get(filename)
    if shipped is None:
        raise ValueError("The installer does not ship '%s' for '%s'"
                         % (filename, theme))
    return write_file(theme, filename, shipped)


def search(theme, needle, ignore_case=True):
    """Find a string across one theme's editable files.

    Plain substring, not regex: the thing anyone actually searches a theme for
    is a token name or a colour, and a regex box is a way to get a confusing
    error instead of an answer.
    """
    if not needle:
        return []
    d = _editor_resolve(theme)
    if not os.path.isdir(d):
        raise ValueError("No theme directory '%s' on this gateway" % theme)
    target = needle.lower() if ignore_case else needle
    hits = []
    for name in sorted(os.listdir(d)):
        if name in EDITOR_PROTECTED or not _editor_is_text(name):
            continue
        path = os.path.join(d, name)
        if not os.path.isfile(path):
            continue
        for number, line in enumerate(_read(path).split("\n"), start=1):
            haystack = line.lower() if ignore_case else line
            if target in haystack:
                hits.append({"file": name, "line": number,
                             "text": line.strip()[:200]})
    return hits


def search_all(needle, ignore_case=True):
    """The same search across every theme on the gateway -- the question
    'which themes still say this' is the one worth asking before an edit."""
    hits = []
    for row in list_themes():
        for hit in search(row["id"], needle, ignore_case):
            hit = dict(hit)
            hit["theme"] = row["id"]
            hits.append(hit)
    return hits


def refresh():
    """Ask the gateway to re-read the theme directories.

    This is the whole of Ectobox's "one-click refresh": an ordinary config
    scan. A saved file is already on disk -- this is what makes the gateway
    notice. write_file() does it for you; this is for after an edit made some
    other way, or to prove to yourself that the scan is what applies a change.
    """
    _rescan()
    return True


# ---------------------------------------------------------------------------
# TOKEN EDITING -- the part that is better than a text box.
#
# A theme's variables.css is a flat list of `--name: value;` declarations, and
# that is the file people actually want to change: the colours. Editing it as
# text means typing hex into a wall of CSS and finding out whether you got it
# right by looking at a page. Editing it as a FORM means a labelled row, a
# swatch you can see, and a colour picker.
#
# The raw text editor stays for index.css and globals.css, which are structure
# rather than values and have no useful form representation.
#
# These reuse the insight functions above -- GROUPS, group_of, is_colour,
# swatch, _VAR_RE -- on purpose. The grouping that explains a theme on the
# Themes page is the grouping that should order it in the editor; two different
# groupings of the same tokens would be two things to keep in step.
# ---------------------------------------------------------------------------

def tokens(theme, filename="variables.css"):
    """Every custom property THIS FILE declares, in file order, grouped.

    Deliberately the file's own declarations, not the resolved stylesheet:
    this is an editor, and you can only edit what is written here. A token the
    theme inherits from the base it imports is not in this list because
    changing it here would mean ADDING a declaration, which is a different
    action and gets its own button.

    Last-wins is reported as a duplicate rather than hidden -- two
    declarations of one token is nearly always a mistake, and silently showing
    only the winner is how it survives.
    """
    doc = read_file(theme, filename)
    text = doc["text"]
    seen = {}
    rows = []
    for match in _VAR_RE.finditer(text):
        name = match.group(1)
        value = match.group(2).strip()
        line = text.count("\n", 0, match.start()) + 1
        row = {
            "name": name,
            "value": value,
            "line": line,
            "group": group_of(name, GROUPS),
            "colour": is_colour(value),
            "swatch": swatch(value),
            "duplicate": name in seen,
        }
        seen[name] = True
        rows.append(row)

    # Grouped in the order GROUPS declares, file order within a group. The
    # alphabetical version of this list was unreadable for the same reason it
    # was unreadable on the Themes page.
    order = dict((label, i) for i, (label, _) in enumerate(GROUPS))
    rows.sort(key=lambda r: (order.get(r["group"], len(order)), r["line"]))
    return rows


def token_groups(theme, filename="variables.css"):
    """tokens() folded into [{group, rows}] -- what a Perspective repeater of
    sections binds to directly, so the view does no grouping of its own."""
    sections = []
    for row in tokens(theme, filename):
        if not sections or sections[-1]["group"] != row["group"]:
            sections.append({"group": row["group"], "rows": []})
        sections[-1]["rows"].append(row)
    for section in sections:
        section["count"] = len(section["rows"])
    return sections


def _token_replace(text, name, value):
    """Replace the value of the LAST declaration of one token, in place.

    Surgical on purpose. Regenerating the file from a parsed token list would
    lose every comment in it -- and our variables.css carries the generated
    'why' comment beside each variable, which is the only explanation of what
    the token is for. An editor that silently strips the documentation is
    worse than no editor.
    """
    last = None
    for match in _VAR_RE.finditer(text):
        if match.group(1) == name:
            last = match
    if last is None:
        raise ValueError("'%s' is not declared in this file" % name)
    # group(2) is the value between ':' and ';'. Splice around it rather than
    # rebuilding the line, so leading whitespace and any trailing comment on
    # the same line survive untouched.
    start = last.start(2)
    end = last.end(2)
    return text[:start] + value + text[end:]


def set_token(theme, value_map_or_name, value=None, filename="variables.css"):
    """Change one token, or several at once, and save.

    Two shapes because the page needs both: set_token(theme, '--border',
    '#4c566a') for a single picker commit, and set_token(theme, {'--border':
    '#4c566a', '--label': '#d8dee9'}) for a Save that collects a form. The
    batch does ONE write and ONE scan.
    """
    if isinstance(value_map_or_name, dict):
        changes = value_map_or_name
    else:
        if value is None:
            raise ValueError("No value for '%s'" % value_map_or_name)
        changes = {value_map_or_name: value}
    if not changes:
        return {"changed": 0}

    doc = read_file(theme, filename)
    text = doc["text"]
    for name in sorted(changes):
        new = changes[name]
        if new is None or not str(new).strip():
            raise ValueError("No value for '%s' -- a token with an empty value "
                             "is not the same as a token that is absent, and "
                             "reads as a broken theme" % name)
        if ";" in str(new) or "}" in str(new):
            raise ValueError("'%s' is not a single CSS value" % new)
        text = _token_replace(text, name, str(new).strip())

    write_file(theme, filename, text)
    return {"changed": len(changes), "tokens": sorted(changes)}


def add_token(theme, name, value, filename="variables.css"):
    """Declare a token the file does not currently declare.

    Appended inside the LAST rule in the file rather than at the end of the
    text, because a declaration after the closing brace is not in any rule and
    does nothing -- silently, which is the worst way for this to fail.
    """
    if not name.startswith("--"):
        raise ValueError("'%s' is not a custom property name" % name)
    doc = read_file(theme, filename)
    text = doc["text"]
    for match in _VAR_RE.finditer(text):
        if match.group(1) == name:
            raise ValueError("'%s' is already declared -- edit it instead"
                             % name)
    close = text.rfind("}")
    if close == -1:
        raise ValueError("'%s' has no CSS rule to add a declaration to"
                         % filename)
    line = "  %s: %s;\n" % (name, str(value).strip())
    text = text[:close] + line + text[close:]
    write_file(theme, filename, text)
    return {"name": name, "value": value}


def tokens_compared(theme, against=None, filename="variables.css"):
    """tokens(), plus what another theme says for the same token.

    This is what the retired "Under the hood" page did, folded into the place
    where you can act on it: seeing that --border is repainted is more useful
    beside the field that changes it than on a page of its own.

    `against` defaults to the stock theme this one is built on, which answers
    "what did we change". Pass another theme id to answer "how do these two
    differ". Same defaulting as compare(), on purpose -- one rule to remember.

    The comparison reads the other theme's RESOLVED stylesheet (post-@import),
    not its files, because the question is what the browser ends up with. Our
    own side stays the file's declarations: you can only edit what is written
    here.
    """
    rows = tokens(theme, filename)
    if against is None:
        against = base_of(theme)
    if not against:
        # A base theme with nothing behind it. Return the rows unmarked rather
        # than inventing a comparison -- see headline().
        for row in rows:
            row["compared"] = ""
            row["state"] = ""
        return rows
    try:
        theirs = _vars_of(theme_css(against))
    except (Exception, Throwable), e:
        # A comparison we could not fetch must not take the editor down with
        # it: the rows are still editable without it.
        for row in rows:
            row["compared"] = ""
            row["state"] = "compare unavailable"
        return rows
    for row in rows:
        other = theirs.get(row["name"])
        row["compared"] = other or "-"
        if other is None:
            row["state"] = "new"
        elif other == row["value"]:
            row["state"] = "same as %s" % against
        else:
            row["state"] = "differs"
    return rows


def compare_options(theme=None):
    """Theme ids to offer in the editor's 'compare against' picker, base
    first -- the default comparison should be the first thing in the list, not
    something to hunt for."""
    ids = [r["id"] for r in list_themes()]
    for builtin in STOCK_BUILTIN:
        if builtin not in ids:
            ids.append(builtin)   # jar-served: comparable, just not editable
    base = base_of(theme) if theme else ""
    ordered = ([base] if base and base in ids else [])
    ordered += [i for i in ids if i != base and i != theme]
    return ordered
