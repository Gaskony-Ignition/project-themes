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
    lines.append('path is a WHITELIST against THEMES below -- there is no code path')
    lines.append('that can touch light/dark/light-cool/light-warm/dark-cool/dark-warm')
    lines.append('or any name this module was not built to know about.')
    lines.append('"""')
    lines.append('')
    lines.append('import os')
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
    lines.append('def status():')
    lines.append('    """[{id, label, dark, installed}, ...] in THEME_ORDER, for the')
    lines.append('    Installer view\'s table."""')
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
    lines.append('            "installed": name in installed,')
    lines.append('        })')
    lines.append('    return out')
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
        "\tfor row in rows:\n"
        "\t\trow['mode'] = 'Dark' if row['dark'] else 'Light'\n"
        "\t\trow['state'] = 'Installed' if row['installed'] else 'Not installed'\n"
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
    # `overflow: auto` to reach at all. 480 clears it with the current
    # content (10 custom + 6 stock swatches, two section labels, one hint
    # line) with zero internal scroll, confirmed the same way.
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
        "\t\tposition={'width': 560, 'height': 500})"
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
                                    "themes as config resources. Safe to re-run -- "
                                    "installing overwrites what is on the gateway, so "
                                    "it also repairs themes after an Ignition upgrade. "
                                    "Safe to delete this project afterwards. v%s"
                                    % (len(themes), version)
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
                    "props": {
                        "direction": "row",
                        "style": {"gap": "12px"},
                    },
                    "children": [
                        {
                            "type": "ia.input.button",
                            "meta": {"name": "install_all_btn"},
                            "position": {"grow": 0, "shrink": 0, "basis": "auto"},
                            "props": {"text": "Install all themes"},
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
                                "text": "Remove all themes",
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
                    ],
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
                                "width": 160,
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


def main():
    version = read_version()
    themes = read_themes()

    if os.path.isdir(INSTALLER_ROOT):
        shutil.rmtree(INSTALLER_ROOT)

    if not os.path.isfile(SELECTOR_POPUP_SRC):
        print("build_installer.py: %s not found -- the selector popup template "
              "is hand-authored, not generated; see selector-popup/README.md" %
              os.path.relpath(SELECTOR_POPUP_SRC, HERE))
        sys.exit(1)

    script_dir = os.path.join(PROJECT_DIR, "ignition", "script-python", "themepack")
    persp_dir = os.path.join(PROJECT_DIR, "com.inductiveautomation.perspective")
    session_props_dir = os.path.join(persp_dir, "session-props")
    page_config_dir = os.path.join(persp_dir, "page-config")
    stylesheet_dir = os.path.join(persp_dir, "stylesheet")
    view_dir = os.path.join(persp_dir, "views", "Installer")
    popup_dir = os.path.join(persp_dir, "views", "SelectorPopup")

    for d in (script_dir, session_props_dir, page_config_dir, stylesheet_dir, view_dir, popup_dir):
        os.makedirs(d)

    # project.json
    write_json(os.path.join(PROJECT_DIR, "project.json"), build_project_json(version, themes))

    # ignition/script-python/themepack/
    write_text(os.path.join(script_dir, "code.py"), build_themepack_code(themes, version))
    write_json(os.path.join(script_dir, "resource.json"), resource_json(["code.py"]))

    # session-props -- hide the app bar (standing rule for every project). No
    # props.theme override: this page runs under whatever theme the gateway
    # session already has, so it never fights the very theme it's installing.
    write_json(os.path.join(session_props_dir, "props.json"), {
        "custom": {},
        "props": {
            "appBar": {"togglePosition": "hidden"},
        },
        "propConfig": {},
    })
    write_json(os.path.join(session_props_dir, "resource.json"), resource_json(["props.json"]))

    # page-config -- "/" -> Installer
    write_json(os.path.join(page_config_dir, "config.json"), {
        "pages": {
            "/": {"title": "Theme Installer", "viewPath": "Installer"},
        }
    })
    write_json(os.path.join(page_config_dir, "resource.json"), resource_json(["config.json"]))

    # stylesheet -- color-scheme (standing workspace rule, every Perspective
    # project) + the app-bar CSS fallback the session prop alone doesn't cover
    # on Maker Edition (feedback-hide-perspective-app-bar).
    stylesheet_css = (
        "/* GENERATED by build_installer.py -- DO NOT EDIT.\n"
        " * See ignition-styles-template-v2/CLAUDE.md's cross-cutting rules:\n"
        " * every Perspective project declares color-scheme, and the app bar is\n"
        " * always hidden. This project runs under whichever theme the session\n"
        " * already has (it has no parent and sets no session.props.theme), so it\n"
        " * declares support for BOTH rather than asserting one -- this still\n"
        " * suppresses Chrome's auto-dark-mode repaint of SVG fills, which is what\n"
        " * the rule exists to prevent. */\n"
        ":root {\n"
        "  color-scheme: light dark;\n"
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

    # views/SelectorPopup -- copied verbatim from the hand-adapted, commit-tracked
    # template (NOT generated from out/ -- see selector-popup/README.md). Only
    # resource.json is built fresh here, same as every other resource.json in
    # this project: no signature, timestamp from the clock.
    with open(SELECTOR_POPUP_SRC) as fh:
        popup_view = json.load(fh)
    write_json(os.path.join(popup_dir, "view.json"), popup_view)
    write_json(os.path.join(popup_dir, "resource.json"), resource_json(["view.json"]))

    print("build_installer.py: wrote %s (%d themes, v%s)" % (
        os.path.relpath(PROJECT_DIR, os.path.dirname(os.path.dirname(HERE))),
        len(themes), version))


if __name__ == "__main__":
    main()
