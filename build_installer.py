#!/usr/bin/env python3
"""Generate the "Theme Installer" Perspective project from out/ + out/themes.json.

This script is not wired into tools/build_all.py, does not import anything
from tools/, and never touches Styles_Template2/, Styles_Example2/, packs/ or
families/. It only READS out/ (must already exist -- run
build_theme.py first) and VERSION, and WRITES
installer-project/Theme_Installer/ (which it wipes and
rebuilds from scratch every run, same pattern as build_theme.py's own out/).

Usage:
    python3 build_theme.py       # if out/ needs (re)building
    python3 build_installer.py

Produces a stand-alone, parent-free Perspective project that embeds all 9
themes' file contents as Python data and installs/uninstalls them as gateway
config resources from a Perspective page -- no shell access, no docker exec,
just "import the project zip, open the page, click Install". See
README.md's "Theme Installer project" section and
package.sh (which zips installer-project/Theme_Installer/ into
dist/Theme_Installer-<VERSION>.zip).
"""

import datetime
import re
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "out")
VERSION_FILE = os.path.join(HERE, "VERSION")
INSTALLER_ROOT = os.path.join(HERE, "installer-project")
PROJECT_DIR = os.path.join(INSTALLER_ROOT, "Theme_Installer")

# The copy-me popup view -- hand-adapted, commit-tracked, NOT generated. See
# selector-popup/README.md for what it is and how it differs from the source
# snapshot it started from.
SELECTOR_POPUP_SRC = os.path.join(HERE, "selector-popup", "SelectorPopup.view.json")

# The other copy-me view: the swatch popup's alternative, a plain dropdown that
# lists whatever themes the gateway has. Same rules as the popup -- hand
# authored, commit-tracked, copied verbatim. The two are INDEPENDENT on
# purpose (each carries its own listing script rather than sharing one): a
# project takes whichever it wants, and neither drags the other in.
THEME_DROPDOWN_SRC = os.path.join(HERE, "selector-popup", "ThemeDropdown.view.json")

# The insight/ analysis functions -- hand-authored, appended to themepack's
# generated code.py. See the header of that file for why it reads the live
# gateway rather than anything baked in here.
INSIGHT_SRC = os.path.join(HERE, "insight", "insight_code.py")

THEME_FILES = ["config.json", "index.css", "variables.css", "globals.css", "resource.json"]

NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_version():
    if not os.path.isfile(VERSION_FILE):
        print("build_installer.py: VERSION file not found: %s" % VERSION_FILE)
        sys.exit(1)
    with open(VERSION_FILE) as fh:
        version = fh.read().strip()
    if not version:
        print("build_installer.py: VERSION file is empty")
        sys.exit(1)
    return version


def read_themes():
    themes_json = os.path.join(OUT_DIR, "themes.json")
    if not os.path.isdir(OUT_DIR) or not os.path.isfile(themes_json):
        print("build_installer.py: out/themes.json not found -- run "
              "build_theme.py first")
        sys.exit(1)
    with open(themes_json) as fh:
        meta = json.load(fh)

    themes = []
    for entry in meta:
        theme_id = entry["id"]
        theme_dir = os.path.join(OUT_DIR, theme_id)
        files = {}
        for name in THEME_FILES:
            path = os.path.join(theme_dir, name)
            if not os.path.isfile(path):
                print("build_installer.py: missing out/%s/%s" % (theme_id, name))
                sys.exit(1)
            with open(path) as fh:
                files[name] = fh.read()
        themes.append({
            "id": theme_id,
            "label": entry["label"],
            "dark": bool(entry["dark"]),
            "source_pack": entry["source_pack"],
            "files": files,
        })
    return themes


def write_json(path, data):
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def write_text(path, text):
    with open(path, "w") as fh:
        fh.write(text)


def resource_json(files, description=None):
    """A project-resource resource.json -- lastModification.timestamp set
    from the clock, deliberately NO lastModificationSignature (see this
    repo's CLAUDE.md and out/<id>/resource.json's own header comment: a
    hand-written signature that doesn't match content makes the config/
    project scan silently skip the resource)."""
    doc = {
        "scope": "G",
        "version": 1,
        "restricted": False,
        "overridable": True,
        "files": files,
        "attributes": {},
        "lastModification": {
            "actor": "external",
            "timestamp": NOW,
        },
    }
    if description:
        doc["description"] = description
    return doc


def build_project_json(version, themes):
    # Workspace rule: released projects carry their version in the Title AND
    # at the end of the Description (the Projects grid shows only the
    # Description; the Title shows in the Edit drawer and on launch surfaces).
    # The theme list is derived, never hand-listed -- a hardcoded list went
    # stale once already (said 9, omitted newsprint-dark).
    ids = ", ".join(t["id"] for t in themes)
    return {
        "title": "Theme Installer %s" % version,
        "description": (
            "Install or remove Gaskony's %d curated Perspective gateway "
            "themes (%s) with one click -- no "
            "shell, no docker exec. Writes gateway config resources under "
            "com.inductiveautomation.perspective/themes/ and triggers a "
            "config scan. Re-running Install overwrites what is on the "
            "gateway, so it also repairs themes after an Ignition upgrade. "
            "Parent-free, safe to delete after use. "
            "Generated by ignition-themes/"
            "build_installer.py. · v%s" % (len(themes), ids, version)
        ),
        "enabled": True,
        "inheritable": False,
        "parent": "",
    }


def additions_css(dark):
    """The optional stock-theme additions: ONLY what every stock theme lacks
    (a color-scheme declaration and themed scrollbars), never a colour or
    layout change -- an updated stock theme must look identical. Matches the
    scrollbar block the custom themes carry in their globals.css, except the
    thumb reads the theme's own var(--border) so one file fits any variant."""
    scheme = "dark" if dark else "light"
    return (
        "/* gaskony-additions.css -- written by the Theme Installer\n"
        " * (ignition-themes). ADDITIONS ONLY, the stock look is untouched:\n"
        " *   - color-scheme declaration (without it Chrome's auto dark mode\n"
        " *     repaints SVG fills client-side)\n"
        " *   - scrollbars follow the theme (stock themes leave them at the\n"
        " *     browser default)\n"
        " * Restore = delete this file and the import line at the end of\n"
        " * index.css -- the Restore button does exactly that. */\n"
        ":root { color-scheme: %s; }\n"
        "* {\n"
        "  scrollbar-color: var(--border) transparent;\n"
        "  scrollbar-width: thin;\n"
        "}\n"
        "::-webkit-scrollbar { width: 10px; height: 10px; }\n"
        "::-webkit-scrollbar-track, ::-webkit-scrollbar-corner { background: transparent; }\n"
        "::-webkit-scrollbar-thumb {\n"
        "  background: var(--border);\n"
        "  border-radius: 6px;\n"
        "  border: 2px solid transparent;\n"
        "  background-clip: content-box;\n"
        "}\n" % scheme
    )


def build_themepack_code(themes, version):
    """ignition/script-python/themepack/code.py -- gateway-scope module
    embedding every theme's file contents plus install/uninstall/status.

    Jython 2.7 (workspace rule): `except (Exception, Throwable), e:` syntax,
    catching java.lang.Throwable because Ignition system calls raise Java
    Throwables that a plain `except Exception` does not see.
    """
    lines = []
    lines.append('"""themepack -- embeds Gaskony\'s %d curated Perspective' % len(themes))
    lines.append('gateway themes as data and installs/uninstalls them as')
    lines.append('gateway config resources.')
    lines.append('')
    lines.append('GENERATED by ignition-themes/')
    lines.append('build_installer.py from out/ -- DO NOT EDIT')
    lines.append('BY HAND. Regenerate with:')
    lines.append('    python3 build_installer.py')
    lines.append('')
    lines.append('Version %s. Gateway scope only -- install()/install_all() write' % version)
    lines.append('files under <dataDir>/config/resources/core/')
    lines.append('com.inductiveautomation.perspective/themes/<id>/ and request a')
    lines.append('config scan; uninstall()/uninstall_all() go through')
    lines.append('system.config.delete() instead, which removes the resource AND')
    lines.append('its files in one call (no scan needed for a delete). Every write')
    lines.append('path is a WHITELIST: custom installs against THEMES below (which can')
    lines.append('never name a stock theme), the OPTIONAL stock update against')
    lines.append('STOCK_UPDATABLE -- and that path only ever adds/removes the one')
    lines.append('additions file and its @import line (stock_update_all() /')
    lines.append('stock_restore_all()); it cannot replace stock content, and light/dark')
    lines.append('have no on-disk files at all. No code path touches any name this')
    lines.append('module was not built to know about.')
    lines.append('"""')
    lines.append('')
    lines.append('import json')
    lines.append('import os')
    lines.append('import re')
    lines.append('')
    lines.append('from java.lang import Throwable')
    lines.append('from com.inductiveautomation.ignition.gateway import IgnitionGateway')
    lines.append('')
    lines.append('')
    lines.append('# id -> {label, dark, source_pack, files: {filename: content}}')
    lines.append('# Content is plain ASCII text (verified at generation time), so a')
    lines.append('# straight repr() round-trips exactly -- no escaping surprises.')
    lines.append('THEMES = {')
    for theme in themes:
        lines.append('    %s: {' % py_repr(theme["id"]))
        lines.append('        "label": %s,' % py_repr(theme["label"]))
        lines.append('        "dark": %s,' % ("True" if theme["dark"] else "False"))
        lines.append('        "source_pack": %s,' % py_repr(theme["source_pack"]))
        lines.append('        "files": {')
        for name in THEME_FILES:
            lines.append('            %s: %s,' % (py_repr(name), py_repr(theme["files"][name])))
        lines.append('        },')
        lines.append('    },')
    lines.append('}')
    lines.append('')
    lines.append('# Display order -- matches out/themes.json / the table on the Installer')
    lines.append('# view. THEMES itself is keyed for O(1) lookup and whitelisting; this is')
    lines.append('# the order things get installed/listed in.')
    lines.append('THEME_ORDER = [')
    for theme in themes:
        lines.append('    %s,' % py_repr(theme["id"]))
    lines.append(']')
    lines.append('')
    lines.append('')
    lines.append('def _data_dir():')
    lines.append('    # Resolved dynamically -- verified live on 8.3.8. Never hardcode an')
    lines.append('    # install path; different gateways mount data/ in different places.')
    lines.append('    return str(IgnitionGateway.get().getSystemManager().getDataDir())')
    lines.append('')
    lines.append('')
    lines.append('def _themes_root():')
    lines.append('    return os.path.join(')
    lines.append('        _data_dir(), "config", "resources", "core",')
    lines.append('        "com.inductiveautomation.perspective", "themes")')
    lines.append('')
    lines.append('')
    lines.append('def _rescan():')
    lines.append('    # Config scan -- picks up newly written theme directories. Themes are')
    lines.append('    # gateway CONFIG resources, not project resources: this is the same')
    lines.append('    # scan as Config -> Platform -> Overview -> "Scan File System", not the')
    lines.append('    # Projects page one.')
    lines.append('    # requestScan() is async (returns a CompletableFuture); BLOCK on it so the')
    lines.append('    # status read that follows a click sees the registered themes, not a stale')
    lines.append('    # in-flight state. 30s cap; a timeout just means status lags a moment.')
    lines.append('    from_future = IgnitionGateway.get().getConfigurationManager().requestScan()')
    lines.append('    try:')
    lines.append('        from java.util.concurrent import TimeUnit')
    lines.append('        from_future.get(30, TimeUnit.SECONDS)')
    lines.append('    except (Exception, Throwable), e:')
    lines.append('        pass  # scan still runs; only the wait failed')
    lines.append('')
    lines.append('')
    lines.append('def _write_theme_files(name):')
    lines.append('    theme = THEMES[name]')
    lines.append('    theme_dir = os.path.join(_themes_root(), name)')
    lines.append('    if not os.path.isdir(theme_dir):')
    lines.append('        os.makedirs(theme_dir)')
    lines.append('    for filename, content in theme["files"].items():')
    lines.append('        path = os.path.join(theme_dir, filename)')
    lines.append('        handle = open(path, "wb")')
    lines.append('        try:')
    lines.append('            handle.write(content.encode("utf-8"))')
    lines.append('        finally:')
    lines.append('            handle.close()')
    lines.append('')
    lines.append('')
    lines.append('def install(name):')
    lines.append('    """Write one theme\'s files and request a scan. Refuses any name not')
    lines.append('    in the embedded THEMES set -- never touches an IA built-in theme."""')
    lines.append('    if name not in THEMES:')
    lines.append('        raise ValueError("Unknown theme id \'%s\' -- refusing to write" % name)')
    lines.append('    _write_theme_files(name)')
    lines.append('    _rescan()')
    lines.append('    return True')
    lines.append('')
    lines.append('')
    lines.append('def install_all():')
    lines.append('    """Write every embedded theme\'s files, then ONE scan at the end (not')
    lines.append('    one per theme -- a scan is not free and 9 of them in a row is no more')
    lines.append('    correct than 1)."""')
    lines.append('    for name in THEME_ORDER:')
    lines.append('        _write_theme_files(name)')
    lines.append('    _rescan()')
    lines.append('    return list(THEME_ORDER)')
    lines.append('')
    lines.append('')
    lines.append('def uninstall(name):')
    lines.append('    """Delete one theme\'s config resource (and its files) via')
    lines.append('    system.config.delete(). Returns False if it was not installed rather')
    lines.append('    than raising -- getResource() raises on missing, which is exactly how')
    lines.append('    "not installed" is detected."""')
    lines.append('    if name not in THEMES:')
    lines.append('        raise ValueError("Unknown theme id \'%s\' -- refusing to touch" % name)')
    lines.append('    try:')
    lines.append('        res = system.config.getResource(')
    lines.append('            moduleId="com.inductiveautomation.perspective",')
    lines.append('            typeId="themes", name=name)')
    lines.append('    except (Exception, Throwable), e:')
    lines.append('        return False')
    lines.append('    system.config.delete(')
    lines.append('        moduleId="com.inductiveautomation.perspective",')
    lines.append('        typeId="themes", name=name,')
    lines.append('        signature=res.getSignature(), actor="theme-installer")')
    lines.append('    return True')
    lines.append('')
    lines.append('')
    lines.append('def uninstall_all():')
    lines.append('    """Delete every embedded theme\'s config resource that is currently')
    lines.append('    installed. Returns the list of ids actually removed."""')
    lines.append('    removed = []')
    lines.append('    for name in THEME_ORDER:')
    lines.append('        if uninstall(name):')
    lines.append('            removed.append(name)')
    lines.append('    return removed')
    lines.append('')
    lines.append('')
    lines.append('# ---- optional stock-theme update ----------------------------------------')
    lines.append('# Installing the custom themes NEVER touches a stock theme. Separately and')
    lines.append('# optionally, the four ON-DISK stock variants can take a small additions')
    lines.append('# file (color-scheme + themed scrollbars) appended via one @import line at')
    lines.append('# the end of their index.css -- their look is unchanged, and restoring is')
    lines.append('# deleting that file and that line. light and dark live INSIDE the')
    lines.append('# Perspective module jar: there are no files on disk to update, so they')
    lines.append('# are never touched (pick light-cool / dark-cool to get the additions).')
    lines.append('')
    lines.append('STOCK_BUILTIN = ["light", "dark"]')
    lines.append('STOCK_UPDATABLE = ["light-cool", "light-warm", "dark-cool", "dark-warm"]')
    lines.append('STOCK_ORDER = ["light", "light-cool", "light-warm",')
    lines.append('               "dark", "dark-cool", "dark-warm"]')
    lines.append('STOCK_DARK = {"light": False, "light-cool": False, "light-warm": False,')
    lines.append('              "dark": True, "dark-cool": True, "dark-warm": True}')
    lines.append('ADDITIONS_FILE = "gaskony-additions.css"')
    lines.append("ADDITIONS_IMPORT = '@import \"./gaskony-additions.css\";'")
    lines.append('ADDITIONS_CSS = {')
    lines.append('    False: %s,' % py_repr(additions_css(False)))
    lines.append('    True: %s,' % py_repr(additions_css(True)))
    lines.append('}')
    lines.append('')
    lines.append('')
    lines.append('def _read(path):')
    lines.append('    fh = open(path, "rb")')
    lines.append('    try:')
    lines.append('        return fh.read().decode("utf-8")')
    lines.append('    finally:')
    lines.append('        fh.close()')
    lines.append('')
    lines.append('')
    lines.append('def _write(path, text):')
    lines.append('    fh = open(path, "wb")')
    lines.append('    try:')
    lines.append('        fh.write(text.encode("utf-8"))')
    lines.append('    finally:')
    lines.append('        fh.close()')
    lines.append('')
    lines.append('')
    lines.append('def _stock_rewrite_manifest(theme_dir):')
    lines.append('    """resource.json must list the files actually in the directory (and')
    lines.append('    the now-stale signature must go, the same unstamped way the custom')
    lines.append('    themes ship -- the scan re-stamps it). The description survives."""')
    lines.append('    path = os.path.join(theme_dir, "resource.json")')
    lines.append('    doc = {"scope": "G", "version": 1, "restricted": False,')
    lines.append('           "overridable": True, "attributes": {}}')
    lines.append('    try:')
    lines.append('        old = json.loads(_read(path))')
    lines.append('        if old.get("description"):')
    lines.append('            doc["description"] = old["description"]')
    lines.append('    except (Exception, Throwable), e:')
    lines.append('        pass')
    lines.append('    doc["files"] = [n for n in sorted(os.listdir(theme_dir))')
    lines.append('                    if n != "resource.json"]')
    lines.append('    _write(path, json.dumps(doc, indent=2))')
    lines.append('')
    lines.append('')
    lines.append('def stock_state(name):')
    lines.append('    """\'builtin\' (jar-served, never touched) | \'missing\' (not on this')
    lines.append('    gateway) | \'updated\' (carries the additions) | \'stock\'."""')
    lines.append('    if name in STOCK_BUILTIN:')
    lines.append('        return "builtin"')
    lines.append('    d = os.path.join(_themes_root(), name)')
    lines.append('    idx = os.path.join(d, "index.css")')
    lines.append('    if not os.path.isfile(idx):')
    lines.append('        return "missing"')
    lines.append('    try:')
    lines.append('        has_import = ADDITIONS_IMPORT in _read(idx)')
    lines.append('    except (Exception, Throwable), e:')
    lines.append('        return "missing"')
    lines.append('    if has_import and os.path.isfile(os.path.join(d, ADDITIONS_FILE)):')
    lines.append('        return "updated"')
    lines.append('    return "stock"')
    lines.append('')
    lines.append('')
    lines.append('def _stock_update_files(name):')
    lines.append('    if name not in STOCK_UPDATABLE:')
    lines.append('        raise ValueError("\'%s\' is not an updatable stock theme" % name)')
    lines.append('    d = os.path.join(_themes_root(), name)')
    lines.append('    if not os.path.isfile(os.path.join(d, "index.css")):')
    lines.append('        return False    # variant absent on this gateway -- skip, not an error')
    lines.append('    _write(os.path.join(d, ADDITIONS_FILE), ADDITIONS_CSS[STOCK_DARK[name]])')
    lines.append('    idx_path = os.path.join(d, "index.css")')
    lines.append('    idx = _read(idx_path)')
    lines.append('    if ADDITIONS_IMPORT not in idx:')
    lines.append('        # index.css is @import lines only, so one more AT THE END is valid')
    lines.append('        # css and the gateway flattener inlines it after everything stock.')
    lines.append('        if not idx.endswith("\\n"):')
    lines.append('            idx += "\\n"')
    lines.append('        _write(idx_path, idx + ADDITIONS_IMPORT + "\\n")')
    lines.append('    _stock_rewrite_manifest(d)')
    lines.append('    return True')
    lines.append('')
    lines.append('')
    lines.append('def _stock_restore_files(name):')
    lines.append('    if name not in STOCK_UPDATABLE:')
    lines.append('        raise ValueError("\'%s\' is not an updatable stock theme" % name)')
    lines.append('    d = os.path.join(_themes_root(), name)')
    lines.append('    idx_path = os.path.join(d, "index.css")')
    lines.append('    changed = False')
    lines.append('    add_path = os.path.join(d, ADDITIONS_FILE)')
    lines.append('    if os.path.isfile(add_path):')
    lines.append('        os.remove(add_path)')
    lines.append('        changed = True')
    lines.append('    if os.path.isfile(idx_path):')
    lines.append('        idx = _read(idx_path)')
    lines.append('        if ADDITIONS_IMPORT in idx:')
    lines.append('            kept = [l for l in idx.splitlines()')
    lines.append('                    if l.strip() != ADDITIONS_IMPORT]')
    lines.append('            _write(idx_path, "\\n".join(kept) + "\\n")')
    lines.append('            changed = True')
    lines.append('    if changed:')
    lines.append('        _stock_rewrite_manifest(d)')
    lines.append('    return changed')
    lines.append('')
    lines.append('')
    lines.append('def stock_update_all():')
    lines.append('    """Add the additions to every on-disk stock variant, then ONE scan.')
    lines.append('    Safe to re-run (idempotent); their look does not change."""')
    lines.append('    updated = [n for n in STOCK_UPDATABLE if _stock_update_files(n)]')
    lines.append('    if updated:')
    lines.append('        _rescan()')
    lines.append('    return updated')
    lines.append('')
    lines.append('')
    lines.append('def stock_restore_all():')
    lines.append('    """Put every updated stock variant back exactly as stock."""')
    lines.append('    restored = [n for n in STOCK_UPDATABLE if _stock_restore_files(n)]')
    lines.append('    if restored:')
    lines.append('        _rescan()')
    lines.append('    return restored')
    lines.append('')
    lines.append('')
    lines.append('def status():')
    lines.append('    """Custom rows ({kind: "custom", installed}) in THEME_ORDER, then')
    lines.append('    stock rows ({kind: "stock", stock: stock_state}) in STOCK_ORDER,')
    lines.append('    for the Installer view\'s table."""')
    lines.append('    installed = set()')
    lines.append('    try:')
    lines.append('        for res in system.config.getResources(')
    lines.append('                moduleId="com.inductiveautomation.perspective", typeId="themes"):')
    lines.append('            installed.add(str(res.getName()))')
    lines.append('    except (Exception, Throwable), e:')
    lines.append('        pass')
    lines.append('    out = []')
    lines.append('    for name in THEME_ORDER:')
    lines.append('        theme = THEMES[name]')
    lines.append('        out.append({')
    lines.append('            "id": name,')
    lines.append('            "label": theme["label"],')
    lines.append('            "dark": theme["dark"],')
    lines.append('            "kind": "custom",')
    lines.append('            "installed": name in installed,')
    lines.append('        })')
    lines.append('    for name in STOCK_ORDER:')
    lines.append('        out.append({')
    lines.append('            "id": name,')
    lines.append('            "label": name.replace("-", " ").capitalize(),')
    lines.append('            "dark": STOCK_DARK[name],')
    lines.append('            "kind": "stock",')
    lines.append('            "stock": stock_state(name),')
    lines.append('        })')
    lines.append('    return out')
    lines.append('')

    # The insight functions are hand-authored and commit-tracked rather than
    # emitted line by line -- 200 lines of lines.append() would be unreadable
    # and unreviewable, and unlike the THEMES data none of this is derived
    # from out/. Same precedent as selector-popup/: source in the repo, copied
    # in verbatim at build time. It is appended (not imported) so the shipped
    # project stays one self-contained script module.
    with open(INSIGHT_SRC) as handle:
        lines.append(handle.read().rstrip("\n"))
    lines.append('')
    return "\n".join(lines)


def py_repr(text):
    """repr() a plain-ASCII str for embedding as a Jython 2 source literal.

    All out/ content was verified ASCII-only at generation time (build_theme.py
    / build_css.py never emit non-ASCII), so Python's own repr() round-trips
    exactly with no encoding surprises -- this is not hand-rolled escaping."""
    return repr(text)


def build_view_json(themes, version):
    # Property-binding transform scripts and component event scripts in this
    # workspace's Perspective views are stored as the BODY of an
    # Ignition-synthesised function, one leading tab per line (confirmed live
    # against access-manager/.../Roles/view.json and
    # toolbox-playbooks/.../Monitor/view.json, both of which use
    # self.view.custom.<x> the same way this view does).
    status_transform_code = (
        "\timport themepack\n"
        "\trows = themepack.status()\n"
        "\tSTOCK_STATE = {\n"
        "\t\t'stock': 'Stock - not modified',\n"
        "\t\t'updated': 'Updated (scrollbars + colour scheme)',\n"
        "\t\t'builtin': 'Inside the Perspective module - never touched',\n"
        "\t\t'missing': 'Not on this gateway',\n"
        "\t}\n"
        "\tfor row in rows:\n"
        "\t\trow['mode'] = 'Dark' if row['dark'] else 'Light'\n"
        "\t\trow['set'] = 'Custom' if row.get('kind') == 'custom' else 'Stock'\n"
        "\t\tif row.get('kind') == 'custom':\n"
        "\t\t\trow['state'] = 'Installed' if row['installed'] else 'Not installed'\n"
        "\t\telse:\n"
        "\t\t\trow['state'] = STOCK_STATE.get(row.get('stock'), '?')\n"
        "\treturn rows"
    )
    install_all_script = (
        "\timport themepack\n"
        "\tthemepack.install_all()\n"
        "\tself.view.custom.tick += 1"
    )
    remove_all_script = (
        "\timport themepack\n"
        "\tthemepack.uninstall_all()\n"
        "\tself.view.custom.tick += 1"
    )
    update_stock_script = (
        "\timport themepack\n"
        "\tthemepack.stock_update_all()\n"
        "\tself.view.custom.tick += 1"
    )
    restore_stock_script = (
        "\timport themepack\n"
        "\tthemepack.stock_restore_all()\n"
        "\tself.view.custom.tick += 1"
    )
    # Size is passed HERE, at the call, not as the popup view's own
    # props.defaultSize (Nigel's spec -- see selector-popup/README.md).
    #
    # NOTE ON THE FORM: the originally specified
    # height='min(460px, 88vh)', width='min(560px, 94vw)' kwargs do not exist
    # on this Ignition version's system.perspective.openPopup -- confirmed
    # both live (a Jython reflection probe against
    # PerspectiveScriptingFunctions.openPopup on module-testing showed no
    # top-level width/height parameter at all -- unknown kwargs are silently
    # swallowed, which is exactly what made the CSS-string form look like it
    # "did nothing" rather than erroring) and against IA's own 8.1/8.3
    # scripting-function reference (width/height are keys INSIDE the
    # `position` dict, typed Dictionary[String, Integer] -- pixels only, no
    # CSS calc()/min()/vw units). The size therefore goes in `position={...}`
    # -- still entirely at the call site, never `props.defaultSize` -- and
    # `viewportBound=True` still does the "never bigger than a short
    # viewport" job the min()/vw forms were reaching for (verified live at
    # 1440x530: the frame stays full-size and is shifted to sit fully
    # inside, rather than being shrunk or clipped).
    #
    # NOTE ON THE HEIGHT VALUE: 460 (the originally specified figure) left
    # the swatch grid 17px taller than the space available inside the frame
    # at EVERY viewport height tried (not a short-viewport-specific problem
    # -- confirmed by measuring scrollHeight vs clientHeight on the "rows"
    # container at both 900px and 530px viewports, identical overflow both
    # times), so the bottom row needed the rows container's own
    # `overflow: auto` to reach at all. 480 cleared it with the content of the
    # day (10 custom + 6 stock swatches, two section labels, one hint line)
    # with zero internal scroll, confirmed the same way.
    #
    # The popup has since grown an "Any theme on this gateway" dropdown below
    # the grid -- a bordered section worth 62px -- and an empty-state line
    # that only appears when no pack is installed, so the frame is 590,
    # checked the same way at both viewport heights.
    open_switcher_script = (
        "\tsystem.perspective.openPopup(\n"
        "\t\t'theme-installer-selector',\n"
        "\t\t'SelectorPopup',\n"
        "\t\ttitle='Theme switcher',\n"
        "\t\tmodal=True,\n"
        "\t\tdraggable=True,\n"
        "\t\tresizable=False,\n"
        "\t\toverlayDismiss=True,\n"
        "\t\tviewportBound=True,\n"
        "\t\tposition={'width': 560, 'height': 590})"
    )

    root = {
        "custom": {
            "tick": 0,
            "themes": [],
        },
        "params": {},
        "props": {
            "defaultSize": {"width": 900, "height": 720},
        },
        "propConfig": {
            "custom.themes": {
                "binding": {
                    "type": "property",
                    "config": {"path": "view.custom.tick"},
                    "transforms": [
                        {"type": "script", "code": status_transform_code}
                    ],
                }
            }
        },
        "root": {
            "type": "ia.container.flex",
            "meta": {"name": "root"},
            "position": {"grow": 0, "shrink": 0, "basis": "auto"},
            "props": {
                "direction": "column",
                "style": {
                    "height": "100%",
                    "overflow": "auto",
                    "padding": "24px",
                    "gap": "16px",
                    "backgroundColor": "var(--containerRoot)",
                },
            },
            "children": [
                # Same nav as the insight pages. Without it those pages are
                # reachable only by typing the URL, which is not shipping them.
                _nav("Installer"),
                {
                    "type": "ia.container.flex",
                    "meta": {"name": "header"},
                    "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                    "props": {
                        "direction": "column",
                        "style": {"gap": "4px"},
                    },
                    "children": [
                        {
                            "type": "ia.display.label",
                            "meta": {"name": "heading"},
                            "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                            "props": {
                                "text": "Theme Installer",
                                "style": {
                                    "fontSize": "26px",
                                    "fontWeight": 600,
                                    "color": "var(--label)",
                                },
                            },
                        },
                        {
                            "type": "ia.display.label",
                            "meta": {"name": "subtitle"},
                            "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                            "props": {
                                "text": (
                                    "Installs Gaskony's %d curated Perspective gateway "
                                    "themes as config resources - the stock themes are "
                                    "never touched by this. Safe to re-run: installing "
                                    "overwrites the gateway's copies, which repairs the "
                                    "themes after an Ignition upgrade. Safe to delete "
                                    "this project afterwards. v%s"
                                    % (len(themes), version)
                                ),
                                "style": {
                                    "fontSize": "13px",
                                    "color": "var(--label--disabled)",
                                },
                            },
                        },
                        {
                            "type": "ia.display.label",
                            "meta": {"name": "subtitle_stock"},
                            "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                            "props": {
                                "text": (
                                    "Optional: 'Update stock themes' adds ONLY themed "
                                    "scrollbars and a colour-scheme declaration to the "
                                    "four on-disk stock variants - their look does not "
                                    "change, and 'Restore stock themes' puts them back "
                                    "exactly. Light and Dark live inside the "
                                    "Perspective module, so they are never touched."
                                ),
                                "style": {
                                    "fontSize": "13px",
                                    "color": "var(--label--disabled)",
                                },
                            },
                        },
                    ],
                },
                {
                    "type": "ia.container.flex",
                    "meta": {"name": "actions"},
                    "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                    "children": [
                        {
                            "type": "ia.input.button",
                            "meta": {"name": "install_all_btn"},
                            "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                            "props": {"text": "Install custom themes"},
                            "events": {
                                "component": {
                                    "onActionPerformed": {
                                        "config": {"script": install_all_script},
                                        "scope": "G",
                                        "type": "script",
                                    }
                                }
                            },
                        },
                        {
                            "type": "ia.input.button",
                            "meta": {"name": "remove_all_btn"},
                            "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                            "props": {
                                "text": "Remove custom themes",
                                "style": {
                                    "backgroundColor": "var(--containerNested)",
                                    "color": "var(--label)",
                                },
                            },
                            "events": {
                                "component": {
                                    "onActionPerformed": {
                                        "config": {"script": remove_all_script},
                                        "scope": "G",
                                        "type": "script",
                                    }
                                }
                            },
                        },
                        {
                            "type": "ia.input.button",
                            "meta": {"name": "update_stock_btn"},
                            "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                            "props": {
                                "text": "Update stock themes",
                                "style": {
                                    "backgroundColor": "var(--containerNested)",
                                    "color": "var(--label)",
                                },
                            },
                            "events": {
                                "component": {
                                    "onActionPerformed": {
                                        "config": {"script": update_stock_script},
                                        "scope": "G",
                                        "type": "script",
                                    }
                                }
                            },
                        },
                        {
                            "type": "ia.input.button",
                            "meta": {"name": "restore_stock_btn"},
                            "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                            "props": {
                                "text": "Restore stock themes",
                                "style": {
                                    "backgroundColor": "var(--containerNested)",
                                    "color": "var(--label)",
                                },
                            },
                            "events": {
                                "component": {
                                    "onActionPerformed": {
                                        "config": {"script": restore_stock_script},
                                        "scope": "G",
                                        "type": "script",
                                    }
                                }
                            },
                        },
                        {
                            "type": "ia.input.button",
                            "meta": {"name": "theme_switcher_btn"},
                            "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                            "props": {
                                "text": "Theme switcher",
                                "style": {
                                    "backgroundColor": "transparent",
                                    "border": "1px solid var(--border)",
                                    "color": "var(--label)",
                                },
                            },
                            "events": {
                                "component": {
                                    "onActionPerformed": {
                                        "config": {"script": open_switcher_script},
                                        "scope": "G",
                                        "type": "script",
                                    }
                                }
                            },
                        },
                        # Both switchers are on this page on purpose: the
                        # button opens the swatch popup, and the dropdown
                        # beside it is the other copy-me view, embedded rather
                        # than duplicated so what is demonstrated here is the
                        # same file a project would copy.
                        {
                            "type": "ia.container.flex",
                            "meta": {"name": "actions_spacer"},
                            "position": {"grow": 1, "shrink": 1, "basis": "0px"},
                            "props": {},
                        },
                        {
                            "type": "ia.display.view",
                            "meta": {"name": "theme_dropdown"},
                            "position": {"grow": 0, "shrink": 0, "basis": "260px"},
                            "props": {
                                "path": "ThemeDropdown",
                                "style": {"minHeight": "34px"},
                            },
                        },
                    ],
                    "props": {
                        "direction": "row",
                        "alignItems": "center",
                        "style": {"gap": "12px"},
                    },
                },
                {
                    "type": "ia.display.table",
                    "meta": {"name": "themes_table"},
                    "position": {"grow": 1, "shrink": 1, "basis": "0px"},
                    "props": {
                        "data": [],
                        "pager": {"top": False, "bottom": False},
                        "columns": [
                            {
                                "field": "set",
                                "header": {"title": "Set"},
                                "width": 90,
                                "strictWidth": True,
                            },
                            {
                                "field": "label",
                                "header": {"title": "Theme"},
                            },
                            {
                                "field": "mode",
                                "header": {"title": "Mode"},
                                "width": 100,
                                "strictWidth": True,
                            },
                            {
                                "field": "state",
                                "header": {"title": "Status"},
                                "width": 320,
                                "strictWidth": True,
                            },
                        ],
                    },
                    "propConfig": {
                        "props.data": {
                            "binding": {
                                "type": "property",
                                "config": {"path": "view.custom.themes"},
                            }
                        }
                    },
                },
            ],
        },
    }
    return root



# ---------------------------------------------------------------------------
# The two insight pages. Both are thin: every number on them comes from
# themepack's insight functions reading the live gateway, so these builders
# lay out components and nothing else -- there is no figure here to go stale.
# ---------------------------------------------------------------------------

# Only binding forms this project already proves are used: `expr` with a script
# transform (ThemeDropdown's options) and `property` with one (the Installer's
# status table). expr-struct appears nowhere in the estate, so a dependency on
# two properties is expressed as an expr binding that CONCATENATES them into
# one key, which the rows binding then watches. Guessing an unproven binding
# type here would fail the way they fail in Perspective: silently, with a blank
# table and no log line.
def _expr(expression, code):
    return {"type": "expr", "config": {"expression": expression},
            "transforms": [{"type": "script", "code": code}]}


def _prop(path, code=None):
    binding = {"type": "property", "config": {"path": path}}
    if code:
        binding["transforms"] = [{"type": "script", "code": code}]
    return binding


def _label(name, text, size="13px", colour="var(--label)", weight=None, grow=0):
    style = {"fontSize": size, "color": colour}
    if weight:
        style["fontWeight"] = weight
    return {"type": "ia.display.label", "meta": {"name": name},
            "position": {"grow": grow, "shrink": 0, "basis": "auto"},
            "props": {"text": text, "style": style}}


def _nav(active):
    """A tab strip across the top. These are separate PAGES, so this cannot be
    an ia.container.tab -- that switches views inside one view. It is a row of
    tabs drawn to look like one: the active tab carries the accent underline
    and does not offer to navigate to the page you are already on."""
    pages = [("Installer", "/"), ("The themes", "/themes"),
             ("How it works", "/how"), ("Under the hood", "/changes"),
             ("For builders", "/contract")]
    tabs = []
    for title, path in pages:
        current = title == active
        style = {"fontSize": "13px", "padding": "9px 16px 8px",
                 "cursor": "default" if current else "pointer",
                 "whiteSpace": "nowrap",
                 "borderBottomStyle": "solid", "borderBottomWidth": "2px",
                 "borderBottomColor": ("var(--callToAction)" if current
                                       else "transparent"),
                 "color": ("var(--label)" if current
                           else "var(--label--disabled)"),
                 "fontWeight": 600 if current else 400}
        tab = {"type": "ia.display.label",
               "meta": {"name": "tab_" + (path.strip("/") or "home")},
               "position": {"grow": 0, "shrink": 0, "basis": "auto"},
               "props": {"text": title, "style": style}}
        if not current:
            # DOM event, not component: onClick under events.component is
            # accepted, saved and never fires -- the tabs looked right and did
            # nothing. events.component is for a component's OWN events
            # (a button's onActionPerformed); onClick is the browser's.
            tab["events"] = {"dom": {"onClick": {
                "config": {"script":
                           "\tsystem.perspective.navigate(page='%s')" % path},
                "scope": "G", "type": "script"}}}
        tabs.append(tab)
    return {"type": "ia.container.flex", "meta": {"name": "tabs"},
            "position": {"grow": 0, "shrink": 0, "basis": "auto"},
            "props": {"direction": "row", "alignItems": "flex-end",
                      "style": {"gap": "2px", "marginBottom": "6px",
                                "borderBottomStyle": "solid",
                                "borderBottomWidth": "1px",
                                "borderBottomColor": "var(--border)"}},
            "children": tabs}


def _stat(key, caption):
    """One headline number, bound to a field of view.custom.counts."""
    return {
        "type": "ia.container.flex", "meta": {"name": "stat_" + key},
        "position": {"grow": 1, "shrink": 1, "basis": "0px"},
        "props": {"direction": "column",
                  "style": {"padding": "10px 12px", "borderRadius": "8px",
                            "backgroundColor": "var(--container)",
                            "border": "var(--containerBorder)"}},
        "children": [
            {"type": "ia.display.label", "meta": {"name": "n"},
             "position": {"grow": 0, "shrink": 0, "basis": "auto"},
             "props": {"style": {"fontSize": "24px", "fontWeight": 600,
                                 "color": "var(--label)"}},
             "propConfig": {"props.text": {"binding": {
                 "type": "expr",
                 "config": {"expression": "{view.custom.counts.%s}" % key}}}}},
            _label("caption", caption, size="12px", colour="var(--label--disabled)"),
        ],
    }


def _table(name, columns, path):
    return {
        "type": "ia.display.table", "meta": {"name": name},
        "position": {"grow": 1, "shrink": 1, "basis": "0px"},
        # No pager, ever (workspace rule) -- these lists are meant to be
        # scrolled and read, not paged through twenty rows at a time.
        "props": {"pager": {"top": False, "bottom": False}, "columns": columns},
        "propConfig": {"props.data": {"binding": _prop(path)}},
    }


def _col(field, title, width=None, strict=False):
    col = {"field": field, "header": {"title": title}}
    if width:
        col["width"] = width
        col["strictWidth"] = strict
    return col


CHANGES_ROWS = (
    "\timport themepack\n"
    "\ttheme, against = (value + '|').split('|')[:2]\n"
    "\tif not theme:\n"
    "\t\treturn []\n"
    "\treturn themepack.compare(theme, against or None)"
)
CHANGES_COUNTS = (
    "\timport themepack\n"
    "\ttheme, against = (value + '|').split('|')[:2]\n"
    "\tif not theme:\n"
    "\t\treturn {}\n"
    "\treturn themepack.summary(theme, against or None)"
)
CHANGES_HEADLINE = (
    "\timport themepack\n"
    "\ttheme, against = (value + '|').split('|')[:2]\n"
    "\tif not theme:\n"
    "\t\treturn ''\n"
    "\treturn themepack.headline(theme, against or None)"
)
CHANGES_LAYERS = (
    "\timport themepack\n"
    "\tif not value:\n"
    "\t\treturn []\n"
    "\treturn themepack.layers(value)"
)
INSTALLED_OPTIONS = (
    "\timport themepack\n"
    "\treturn [{'value': r['id'], 'label': r['label']}\n"
    "\t        for r in themepack.status()\n"
    "\t        if r.get('kind') == 'custom' and r.get('installed')]"
)
AGAINST_OPTIONS = (
    "\timport themepack\n"
    "\topts = [{'value': '', 'label': 'its own base theme'}]\n"
    "\tfor r in themepack.status():\n"
    "\t\tif r.get('kind') != 'custom' or r.get('installed'):\n"
    "\t\t\topts.append({'value': r['id'], 'label': r['label']})\n"
    "\treturn opts"
)
FIRST_INSTALLED = (
    "\timport themepack\n"
    "\tfor r in themepack.status():\n"
    "\t\tif r.get('kind') == 'custom' and r.get('installed'):\n"
    "\t\t\treturn r['id']\n"
    "\treturn ''"
)
CONTRACT_TOKENS = (
    "\timport themepack\n"
    "\tif not value:\n"
    "\t\treturn []\n"
    "\treturn themepack.contract(value)"
)
CONTRACT_CLASSES = (
    "\timport themepack\n"
    "\tif not value:\n"
    "\t\treturn []\n"
    "\treturn themepack.contract_classes(value)"
)


def _theme_picker(name, label, custom_path, options_code):
    return {
        "type": "ia.container.flex", "meta": {"name": name},
        "position": {"grow": 0, "shrink": 0, "basis": "auto"},
        "props": {"direction": "column", "style": {"gap": "3px"}},
        "children": [
            _label("cap", label, size="12px", colour="var(--label--disabled)"),
            {"type": "ia.input.dropdown", "meta": {"name": "dd"},
             "position": {"grow": 0, "shrink": 0, "basis": "auto"},
             "props": {"allowClearing": False, "showSearch": False,
                       "style": {"height": "34px", "minWidth": "220px"}},
             "propConfig": {
                 "props.options": {"binding": _expr("1", options_code)},
                 # bidirectional goes INSIDE config or it is silently ignored
                 # and the dropdown never writes the selection back.
                 "props.value": {"binding": {
                     "type": "property",
                     "config": {"path": custom_path, "bidirectional": True}}},
             }},
        ],
    }





# ---------------------------------------------------------------------------
# The miniature screen, drawn with LITERAL colours at build time.
#
# This began as one parameterised view fed by a flex-repeater, and it did not
# work: view.params never resolved inside it, through a repeater OR a direct
# ia.display.view embed, with no error in the console, no gateway log line and
# every literal string still rendering -- so the gallery laid out perfectly in
# plain white twelve times. Property bindings, expression bindings and binding
# props.style as a whole object all failed identically.
#
# Baking the colours in is not a workaround, it is the more honest artefact:
# the installer already EMBEDS each theme's files, so a preview drawn from the
# same embedded copy shows exactly what pressing Install will produce -- and
# it renders with no bindings, no params and nothing that can silently fail.
# The measurement pages stay live; the picture is a picture.
# ---------------------------------------------------------------------------

STOCK_PALETTES = os.path.join(HERE, "insight", "stock-palettes.json")

# Ignition's light/dark define nearly everything as var(--neutral-NN); a
# preview holding a var() reference renders in the VIEWING page's colours,
# quietly showing the wrong thing rather than nothing.
_VARDEF = re.compile(r'^[ \t]*(--[A-Za-z0-9_-]+)[ \t]*:[ \t]*([^;]+);', re.M)


def theme_palette(theme):
    """The dozen colours one preview is painted with, from out/ at build time."""
    values = {}
    for filename in ("variables.css", "globals.css"):
        for match in _VARDEF.finditer(theme["files"].get(filename, "")):
            values[match.group(1)] = match.group(2).strip()

    def resolve(value, hops=0):
        while value.startswith("var(") and hops < 6:
            name = re.match(r'var\(\s*(--[A-Za-z0-9_-]+)', value)
            if not name:
                return ""
            value = values.get(name.group(1), "").strip()
            hops += 1
        return "" if value.startswith("var(") else value

    def pick(*names):
        for name in names:
            value = resolve(values.get(name, "").strip())
            if value and value != "transparent":
                return value
        return ""

    page = pick("--st-page-solid", "--containerRoot")
    return {
        "page": page,
        "sidebar": pick("--st-sidebar-solid", "--containerNested", "--container"),
        "card": pick("--st-card", "--container"),
        "text": pick("--st-fg", "--label"),
        "muted": pick("--label--disabled", "--label"),
        "chromeFg": pick("--st-chrome-fg", "--label"),
        "accent": pick("--st-accent", "--callToAction"),
        "onAccent": pick("--st-on-accent") or "#ffffff",
        "border": pick("--st-chrome-border", "--border"),
        "headBg": pick("--st-head-solid", "--containerNested", "--container"),
        "headFg": pick("--st-head-fg", "--label"),
        "rowBg": pick("--st-row-bg") or page,
        "cellFg": pick("--st-cell-fg", "--label"),
    }


def _flex(name, children=None, direction="column", grow=0, basis="auto", style=None):
    node = {"type": "ia.container.flex", "meta": {"name": name},
            "position": {"grow": grow, "shrink": 0, "basis": basis},
            "props": {"direction": direction, "style": style or {}}}
    if children:
        node["children"] = children
    return node


def _txt(name, text, size, colour, weight=None):
    style = {"fontSize": size, "color": colour, "lineHeight": "1.25",
             "whiteSpace": "nowrap", "overflow": "hidden"}
    if weight:
        style["fontWeight"] = weight
    return {"type": "ia.display.label", "meta": {"name": name},
            "position": {"grow": 0, "shrink": 1, "basis": "auto"},
            "props": {"text": text, "style": style}}


def preview_node(name, pal, label, caption):
    """A whole screen in 230px: top bar, rail, a card with a button, a table."""
    c = lambda k, fallback="#888888": pal.get(k) or fallback
    topbar = _flex("topbar", direction="row", basis="24px", style={
        "backgroundColor": c("sidebar"), "alignItems": "center",
        "gap": "6px", "padding": "0 8px"}, children=[
            _flex("dot", basis="10px", style={
                "backgroundColor": c("accent"), "height": "10px",
                "borderRadius": "5px"}),
            _txt("apptitle", "My Plant", "9px", c("chromeFg"), 600)])
    rail = _flex("rail", basis="38px", style={
        "backgroundColor": c("sidebar"), "gap": "5px",
        "padding": "8px 6px"}, children=[
            _flex("nav%d" % i, basis="4px", style={
                "backgroundColor": c("chromeFg"), "height": "4px",
                "borderRadius": "2px",
                "opacity": "0.9" if i == 0 else "0.45"}) for i in range(3)])
    card = _flex("card", style={
        "backgroundColor": c("card"), "border": "1px solid " + c("border"),
        "borderRadius": "5px", "padding": "6px 8px", "gap": "3px"}, children=[
            _txt("t", "Pump 4 - running", "9px", c("text"), 600),
            _txt("s", "Flow steady at 42 L/s", "8px", c("muted")),
            _flex("btn", direction="row", style={
                "backgroundColor": c("accent"), "borderRadius": "4px",
                "padding": "3px 8px", "alignSelf": "flex-start",
                "marginTop": "3px"}, children=[
                    _txt("b", "Acknowledge", "8px", c("onAccent"), 600)])])
    table = _flex("table", style={
        "marginTop": "6px", "borderRadius": "4px", "overflow": "hidden",
        "border": "1px solid " + c("border")}, children=[
            _flex("th", direction="row", basis="15px", style={
                "backgroundColor": c("headBg"), "alignItems": "center",
                "padding": "0 6px"}, children=[
                    _txt("h", "Tag            Value", "8px", c("headFg"), 600)]),
            _flex("r0", direction="row", basis="14px", style={
                "backgroundColor": c("rowBg"), "alignItems": "center",
                "padding": "0 6px"}, children=[
                    _txt("v", "FT-101       42.0", "8px", c("cellFg"))]),
            _flex("r1", direction="row", basis="14px", style={
                "alignItems": "center", "padding": "0 6px"}, children=[
                    _txt("v", "PT-102        3.1", "8px", c("cellFg"))])])
    screen = _flex("screen", grow=1, basis="0px", style={
        "backgroundColor": c("page"), "border": "1px solid " + c("border"),
        "borderRadius": "6px", "overflow": "hidden"}, children=[
            topbar,
            _flex("body", direction="row", grow=1, basis="0px", children=[
                rail,
                _flex("main", grow=1, basis="0px", style={
                    "padding": "7px"}, children=[card, table])])])
    return _flex(name, basis="205px", style={"gap": "0px"}, children=[
        _flex("frame", basis="150px", children=[screen]),
        _txt("name", label, "12px", "var(--label)", 600),
        _txt("cap", caption, "10px", "var(--label--disabled)")])


def _layer_card(i):
    """One of the three build layers, as a card rather than a table row.

    This was a three-row table and it clipped twice: a table sizes to rows,
    and these are paragraphs. Cards wrap instead of truncating.
    """
    def bound(field, size, colour, weight=None):
        style = {"fontSize": size, "color": colour}
        if weight:
            style["fontWeight"] = weight
        return {"type": "ia.display.label", "meta": {"name": field},
                "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                "props": {"style": style},
                "propConfig": {"props.text": {"binding": {
                    "type": "expr",
                    "config": {"expression": "{view.custom.layers[%d].%s}" % (i, field)}}}}}
    return {
        "type": "ia.container.flex", "meta": {"name": "layer%d" % i},
        "position": {"grow": 1, "shrink": 1, "basis": "0px"},
        "props": {"direction": "column",
                  "style": {"padding": "10px 12px", "gap": "5px",
                            "borderRadius": "8px",
                            "backgroundColor": "var(--container)",
                            "border": "var(--containerBorder)"}},
        "children": [
            bound("layer", "13px", "var(--label)", 600),
            bound("what", "12px", "var(--label--disabled)"),
            bound("here", "12px", "var(--label)"),
        ],
    }



# ---------------------------------------------------------------------------
# The two lay pages. "The themes" answers "what do they look like" with a
# gallery of painted screens; "How it works" answers "what is going on" with
# the same screen painted twice and three sentences. The measurement pages
# stay, demoted to "under the hood".
# ---------------------------------------------------------------------------


def _prose(name, text, size="13px", colour="var(--label)"):
    return {"type": "ia.display.label", "meta": {"name": name},
            "position": {"grow": 0, "shrink": 0, "basis": "auto"},
            "props": {"text": text,
                      "style": {"fontSize": size, "color": colour,
                                "lineHeight": "1.55", "maxWidth": "880px"}}}


def _gallery(name, cards):
    return {"type": "ia.container.flex", "meta": {"name": name},
            "position": {"grow": 0, "shrink": 0, "basis": "auto"},
            "props": {"direction": "row", "wrap": "wrap",
                      "style": {"gap": "16px", "rowGap": "18px"}},
            "children": cards}


def _stock_palettes():
    """(order, labels, palettes) for Ignition's own themes, as captured."""
    data = json.load(open(STOCK_PALETTES))
    return data["order"], data["labels"], data["palettes"]


def build_themes_view_json(themes, version):
    """The gallery: what a gateway starts with, then what this installs."""
    order, labels, palettes = _stock_palettes()
    stock = [preview_node("stock%d" % i, palettes[theme_id],
                          labels.get(theme_id, theme_id),
                          "dark" if "dark" in theme_id else "light")
             for i, theme_id in enumerate(order)]
    ours = []
    for i, theme in enumerate(sorted(themes, key=lambda t: t["label"])):
        ours.append(preview_node(
            "t%d" % i, theme_palette(theme), theme["label"],
            "dark" if theme["dark"] else "light"))
    return {
        "custom": {}, "params": {}, "props": {},
        "root": {"type": "ia.container.flex", "meta": {"name": "root"},
                 "props": {"direction": "column",
                           "style": {"padding": "18px", "gap": "12px",
                                     "backgroundColor": "var(--containerRoot)"}},
                 "children": [
            _nav("The themes"),
            _label("title", "The themes", size="24px", weight=600),
            _prose("intro",
                   "A theme is a coat of paint for every screen on this "
                   "gateway. Each little screen below is one of them - the "
                   "same imaginary plant page, drawn with that theme's own "
                   "colours."),
            _label("stock_h", "What every gateway starts with", size="15px",
                   weight=600),
            _prose("stock_sub",
                   "Ignition's own six. They are never modified by this "
                   "project, and they stay available alongside the ones it "
                   "installs.",
                   size="12px", colour="var(--label--disabled)"),
            _gallery("stock", stock),
            _label("ours_h", "The %d themes this project installs" % len(themes),
                   size="15px", weight=600),
            _prose("ours_sub",
                   "Install them from the Installer page, then pick one from "
                   "any project's Theme button. Same screens, same data, "
                   "different paint.",
                   size="12px", colour="var(--label--disabled)"),
            _gallery("ours", ours),
        ]},
    }


def build_how_view_json(themes, version):
    """The story: three sentences, one before/after, three steps."""
    order, labels, palettes = _stock_palettes()
    dark = palettes["dark"]
    example = sorted(themes, key=lambda t: t["label"])[0]
    def step(i, title, text):
        return {"type": "ia.container.flex", "meta": {"name": "step%d" % i},
                "position": {"grow": 1, "shrink": 1, "basis": "0px"},
                "props": {"direction": "column",
                          "style": {"padding": "12px 14px", "gap": "6px",
                                    "borderRadius": "8px",
                                    "backgroundColor": "var(--container)",
                                    "border": "var(--containerBorder)"}},
                "children": [
                    _label("n", str(i), size="20px",
                           colour="var(--callToAction)", weight=700),
                    _label("t", title, size="14px", weight=600),
                    _prose("x", text, size="12px",
                           colour="var(--label--disabled)")]}
    return {
        "custom": {}, "params": {}, "props": {},
        "root": {"type": "ia.container.flex", "meta": {"name": "root"},
                 "props": {"direction": "column",
                           "style": {"padding": "18px", "gap": "14px",
                                     "backgroundColor": "var(--containerRoot)"}},
                 "children": [
            _nav("How it works"),
            _label("title", "How it works", size="24px", weight=600),
            _prose("intro",
                   "Ignition does not colour each screen by hand. It draws "
                   "everything from a palette of named colours - the page "
                   "colour, the text colour, the button colour - and every "
                   "component looks them up as it draws. A theme is a small "
                   "file that points those names at different colours. Pick "
                   "one and every screen repaints itself at once. Your views, "
                   "your data and your logic are never touched: a theme "
                   "carries colours, not screens."),
            {"type": "ia.container.flex", "meta": {"name": "pair"},
             "position": {"grow": 0, "shrink": 0, "basis": "auto"},
             "props": {"direction": "row",
                       "style": {"gap": "26px", "alignItems": "flex-start"}},
             "children": [
                 preview_node("before", dark, "Ignition dark",
                              "the palette every gateway ships with"),
                 _label("arrow", "\u2192", size="26px",
                        colour="var(--label--disabled)"),
                 preview_node("after", theme_palette(example), example["label"],
                              "the same screen, same components, repainted"),
             ]},
            {"type": "ia.container.flex", "meta": {"name": "steps"},
             "position": {"grow": 0, "shrink": 0, "basis": "auto"},
             "props": {"direction": "row", "style": {"gap": "12px"}},
             "children": [
                 step(1, "Install",
                      "The Installer page copies the theme files onto this "
                      "gateway and registers them. Nothing changes on screen "
                      "yet - installing just puts the paint on the shelf."),
                 step(2, "Pick one",
                      "Every project gets a Theme button. Choosing a theme "
                      "repaints that session straight away, and a project can "
                      "set one as the default everybody sees."),
                 step(3, "Change your mind",
                      "Nothing here is permanent. Pick a different theme and "
                      "it all repaints again; remove the themes and the "
                      "gateway is back to stock. Ignition's own light and "
                      "dark are never modified."),
             ]},
            _prose("deeper",
                   "For the detail: 'Under the hood' measures, live against "
                   "this gateway, every colour a theme changes. 'For builders' "
                   "lists the tokens and style classes a project can use.",
                   size="12px", colour="var(--label--disabled)"),
        ]},
    }


def build_changes_view_json(themes, version):
    """Page: what this theme actually changes, measured against stock."""
    return {
        "custom": {"theme": "", "against": "", "key": "",
                   "rows": [], "counts": {}, "layers": [], "headline": ""},
        "propConfig": {
            "custom.theme": {"binding": _expr("1", FIRST_INSTALLED)},
            # One key so the rows depend on BOTH dropdowns. See _expr's note.
            "custom.key": {"binding": {"type": "expr", "config": {
                "expression": "{view.custom.theme} + '|' + {view.custom.against}"}}},
            "custom.rows": {"binding": _prop("view.custom.key", CHANGES_ROWS)},
            "custom.counts": {"binding": _prop("view.custom.key", CHANGES_COUNTS)},
            "custom.layers": {"binding": _prop("view.custom.theme", CHANGES_LAYERS)},
            "custom.headline": {"binding": _prop("view.custom.key", CHANGES_HEADLINE)},
        },
        "params": {},
        "root": {
            "type": "ia.container.flex", "meta": {"name": "root"},
            "props": {"direction": "column",
                      "style": {"padding": "18px", "gap": "14px",
                                "backgroundColor": "var(--containerRoot)"}},
            "children": [
                _nav("Under the hood"),
                _label("title", "Under the hood", size="24px", weight=600),
                {"type": "ia.display.label", "meta": {"name": "headline"},
                 "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                 "props": {"style": {"fontSize": "14px", "color": "var(--label)",
                                     "lineHeight": "1.5"}},
                 "propConfig": {"props.text": {
                     "binding": _prop("view.custom.headline")}}},
                _label("sub",
                       "Measured on this gateway when you opened the page, not "
                       "written down when the theme was built. v" + version,
                       size="12px", colour="var(--label--disabled)"),
                {"type": "ia.container.flex", "meta": {"name": "pickers"},
                 "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                 "props": {"direction": "row", "style": {"gap": "14px"}},
                 "children": [
                     _theme_picker("pick_theme", "Theme", "view.custom.theme",
                                   INSTALLED_OPTIONS),
                     _theme_picker("pick_against", "Compared with",
                                   "view.custom.against", AGAINST_OPTIONS),
                 ]},
                {"type": "ia.container.flex", "meta": {"name": "stats"},
                 "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                 "props": {"direction": "row", "style": {"gap": "10px"}},
                 "children": [
                     _stat("overridden", "of Ignition's variables repainted"),
                     _stat("inherited", "left exactly as Ignition set them"),
                     _stat("added", "new variables this theme adds"),
                 ]},
                _label("anatomy_h", "How it is built", size="15px",
                       weight=600),
                {"type": "ia.container.flex", "meta": {"name": "layers"},
                 "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                 "props": {"direction": "row", "style": {"gap": "10px"}},
                 "children": [_layer_card(i) for i in range(3)]},
                _label("table_h", "Every variable, grouped by what it affects",
                       size="15px", weight=600),
                _label("table_sub",
                       "'What it is' is the derivation recorded when the value "
                       "was generated, not a description written afterwards. "
                       "Rows reading 'kept as Ignition's' are Ignition's own "
                       "value, left alone.",
                       size="12px", colour="var(--label--disabled)"),
                _table("changes", [
                    _col("group", "Affects", 180, True),
                    _col("variable", "Variable", 195, True),
                    _col("what", "What it is"),
                    _col("swatch", "Colour", 70, True),
                    _col("value", "This theme", 165, True),
                    _col("compared", "Ignition's", 150, True),
                    _col("state", "Change", 130, True),
                ], "view.custom.rows"),
            ],
        },
    }


def build_contract_view_json(themes, version):
    """Page: the tokens and classes a project can build on."""
    return {
        "custom": {"theme": "", "tokens": [], "classes": []},
        "propConfig": {
            "custom.theme": {"binding": _expr("1", FIRST_INSTALLED)},
            "custom.tokens": {"binding": _prop("view.custom.theme", CONTRACT_TOKENS)},
            "custom.classes": {"binding": _prop("view.custom.theme", CONTRACT_CLASSES)},
        },
        "params": {},
        "root": {
            "type": "ia.container.flex", "meta": {"name": "root"},
            "props": {"direction": "column",
                      "style": {"padding": "18px", "gap": "14px",
                                "backgroundColor": "var(--containerRoot)"}},
            "children": [
                _nav("For builders"),
                _label("title", "For builders", size="24px", weight=600),
                _label("sub",
                       "What a project can rely on without inheriting anything. "
                       "Both lists are read out of the installed theme itself, "
                       "so this page cannot advertise a token or a class the "
                       "theme does not actually ship. v" + version,
                       size="13px", colour="var(--label--disabled)"),
                _theme_picker("pick_theme", "Theme", "view.custom.theme",
                              INSTALLED_OPTIONS),
                _label("tok_h", "Tokens", size="15px", weight=600),
                _label("tok_sub",
                       "Custom properties published at :root. Use them as "
                       "var(--st-accent) in a style class or an inline style. "
                       "'Where' is read from the theme's own rules, so a token "
                       "shown with no consumers is one the theme publishes for "
                       "your project to use rather than one it uses itself.",
                       size="12px", colour="var(--label--disabled)"),
                _table("tokens", [
                    _col("group", "Group", 170, True),
                    _col("token", "Token", 200, True),
                    _col("what", "What it is", 230),
                    _col("swatch", "Colour", 70, True),
                    _col("value", "Value", 175, True),
                    _col("where", "Where the theme uses it"),
                ], "view.custom.tokens"),
                _label("cls_h", "Style classes", size="15px", weight=600),
                _label("cls_sub",
                       "Put the name in a component's style.classes and the "
                       "theme styles it -- no style-class resource needed in "
                       "your project. Each selector is doubled in the CSS so it "
                       "outranks Ignition's own component rules without "
                       "!important, which would also beat your inline styles.",
                       size="12px", colour="var(--label--disabled)"),
                _table("classes", [
                    _col("family", "Family", 130, True),
                    _col("klass", "Class", 260, True),
                    _col("count", "Sets", 70, True),
                    _col("sets", "Properties"),
                ], "view.custom.classes"),
            ],
        },
    }


def main():
    version = read_version()
    themes = read_themes()

    if os.path.isdir(INSTALLER_ROOT):
        shutil.rmtree(INSTALLER_ROOT)

    if not os.path.isfile(INSIGHT_SRC):
        print("build_installer.py: %s not found -- the insight functions are "
              "hand-authored, not generated" % os.path.relpath(INSIGHT_SRC, HERE))
        sys.exit(1)

    for src in (SELECTOR_POPUP_SRC, THEME_DROPDOWN_SRC):
        if not os.path.isfile(src):
            print("build_installer.py: %s not found -- the theme-switcher views "
                  "are hand-authored, not generated; see "
                  "selector-popup/README.md" % os.path.relpath(src, HERE))
            sys.exit(1)

    script_dir = os.path.join(PROJECT_DIR, "ignition", "script-python", "themepack")
    persp_dir = os.path.join(PROJECT_DIR, "com.inductiveautomation.perspective")
    session_props_dir = os.path.join(persp_dir, "session-props")
    page_config_dir = os.path.join(persp_dir, "page-config")
    stylesheet_dir = os.path.join(persp_dir, "stylesheet")
    view_dir = os.path.join(persp_dir, "views", "Installer")
    changes_dir = os.path.join(persp_dir, "views", "Changes")
    themes_dir = os.path.join(persp_dir, "views", "Themes")
    how_dir = os.path.join(persp_dir, "views", "How")
    contract_dir = os.path.join(persp_dir, "views", "Contract")
    popup_dir = os.path.join(persp_dir, "views", "SelectorPopup")
    dropdown_dir = os.path.join(persp_dir, "views", "ThemeDropdown")

    for d in (script_dir, session_props_dir, page_config_dir, stylesheet_dir,
              view_dir, popup_dir, dropdown_dir, changes_dir, contract_dir,
              themes_dir, how_dir):
        os.makedirs(d)

    # project.json
    write_json(os.path.join(PROJECT_DIR, "project.json"), build_project_json(version, themes))

    # ignition/script-python/themepack/
    write_text(os.path.join(script_dir, "code.py"), build_themepack_code(themes, version))
    write_json(os.path.join(script_dir, "resource.json"), resource_json(["code.py"]))

    # session-props -- hide the app bar (standing rule for every project) and
    # run on Ignition's STOCK dark theme (Nigel, 31/08/2026).
    #
    # This used to set no theme at all, so the project inherited whatever the
    # gateway session had. That reasoning does not survive the preview pages:
    # they paint every theme in literal colours, so the surface behind them has
    # to be a known, stable backdrop or the same gallery reads differently on
    # every gateway. "dark" is also the one theme guaranteed to exist -- it
    # lives inside the Perspective module, so it is present before this project
    # has installed anything and cannot be removed by uninstalling.
    write_json(os.path.join(session_props_dir, "props.json"), {
        "custom": {},
        "props": {
            "appBar": {"togglePosition": "hidden"},
            "theme": "dark",
        },
        "propConfig": {},
    })
    write_json(os.path.join(session_props_dir, "resource.json"), resource_json(["props.json"]))

    # page-config -- "/" -> Installer
    write_json(os.path.join(page_config_dir, "config.json"), {
        "pages": {
            "/": {"title": "Theme Installer", "viewPath": "Installer"},
            "/themes": {"title": "The themes", "viewPath": "Themes"},
            "/how": {"title": "How it works", "viewPath": "How"},
            "/changes": {"title": "Under the hood", "viewPath": "Changes"},
            "/contract": {"title": "The contract", "viewPath": "Contract"},
        }
    })
    write_json(os.path.join(page_config_dir, "resource.json"), resource_json(["config.json"]))

    # stylesheet -- color-scheme (standing workspace rule, every Perspective
    # project) + the app-bar CSS fallback the session prop alone doesn't cover
    # on Maker Edition (feedback-hide-perspective-app-bar).
    stylesheet_css = (
        "/* GENERATED by build_installer.py -- DO NOT EDIT.\n"
        " * Workspace cross-cutting rules: every Perspective project declares\n"
        " * color-scheme, and the app bar is always hidden. This project runs\n"
        " * on Ignition's stock dark theme (session.props.theme), so it\n"
        " * declares dark -- matching what the pages are actually painted in is\n"
        " * the point of the rule: it stops Chrome's auto-dark-mode repainting\n"
        " * SVG fills and washing the theme previews out. */\n"
        ":root {\n"
        "  color-scheme: dark;\n"
        "}\n"
        "\n"
        ".app-bar {\n"
        "  display: none !important;\n"
        "}\n"
    )
    write_text(os.path.join(stylesheet_dir, "stylesheet.css"), stylesheet_css)
    write_json(os.path.join(stylesheet_dir, "resource.json"), resource_json(["stylesheet.css"]))

    # views/Installer
    write_json(os.path.join(view_dir, "view.json"), build_view_json(themes, version))
    write_json(os.path.join(view_dir, "resource.json"), resource_json(["view.json"]))

    # views/Preview, Themes, How -- the lay-reader surface: a miniature
    # screen painted from params, the gallery of all themes drawn with their
    # real colours, and the three-sentence story with a before/after pair.
    write_json(os.path.join(themes_dir, "view.json"),
               build_themes_view_json(themes, version))
    write_json(os.path.join(themes_dir, "resource.json"), resource_json(["view.json"]))
    write_json(os.path.join(how_dir, "view.json"),
               build_how_view_json(themes, version))
    write_json(os.path.join(how_dir, "resource.json"), resource_json(["view.json"]))

    # views/Changes and views/Contract -- the insight pages. Generated, but
    # they contain no data of their own: every number is bound to a themepack
    # call that reads the live gateway.
    write_json(os.path.join(changes_dir, "view.json"),
               build_changes_view_json(themes, version))
    write_json(os.path.join(changes_dir, "resource.json"), resource_json(["view.json"]))
    write_json(os.path.join(contract_dir, "view.json"),
               build_contract_view_json(themes, version))
    write_json(os.path.join(contract_dir, "resource.json"), resource_json(["view.json"]))

    # views/SelectorPopup -- copied verbatim from the hand-adapted, commit-tracked
    # template (NOT generated from out/ -- see selector-popup/README.md). Only
    # resource.json is built fresh here, same as every other resource.json in
    # this project: no signature, timestamp from the clock.
    with open(SELECTOR_POPUP_SRC) as fh:
        popup_view = json.load(fh)
    write_json(os.path.join(popup_dir, "view.json"), popup_view)
    write_json(os.path.join(popup_dir, "resource.json"), resource_json(["view.json"]))

    # views/ThemeDropdown -- the other copy-me view, same treatment.
    with open(THEME_DROPDOWN_SRC) as fh:
        dropdown_view = json.load(fh)
    write_json(os.path.join(dropdown_dir, "view.json"), dropdown_view)
    write_json(os.path.join(dropdown_dir, "resource.json"), resource_json(["view.json"]))

    print("build_installer.py: wrote %s (%d themes, v%s)" % (
        os.path.relpath(PROJECT_DIR, os.path.dirname(os.path.dirname(HERE))),
        len(themes), version))


if __name__ == "__main__":
    main()
