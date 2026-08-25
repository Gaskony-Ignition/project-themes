#!/bin/sh
# package.sh -- build dist/gaskony-themes-<VERSION>.zip
# AND dist/Theme_Installer-<VERSION>.zip.
#
# POSIX sh. Does NOT regenerate anything -- run
# `python3 build_theme.py` (rebuilds out/) and
# `python3 build_installer.py` (rebuilds
# installer-project/Theme_Installer/ from out/) first. This always packages
# the current state of both, not a stale one. Refuses to run if either input
# is missing, rather than silently packaging an empty/partial release.
#
# Contents of gaskony-themes-<VERSION>.zip (all inside one top-level
# gaskony-themes-<VERSION>/ folder, so extracting it never sprays files into
# the current directory):
#   - the 9 theme directories, copied verbatim from out/
#   - out/themes.json
#   - install.sh (this repo's copy -- see below for why it's shared)
#   - RELEASE-README.md
#
# Contents of Theme_Installer-<VERSION>.zip: the CONTENTS of
# installer-project/Theme_Installer/ (project.json at the zip root, no
# wrapping folder) -- an Ignition 8.3 project import zip, the same layout
# tools/build_exports.py uses for this repo's own exports/*.zip (verified
# against a real Exchange package export; not inferred). Import it in the
# Designer or the Gateway's Projects page, open
# /data/perspective/client/Theme_Installer, click "Install all themes".
#
# SHARED CONTENT NOTE: RELEASE-README.md's "Installing on a gateway" section
# and this repo's own README.md carry the SAME install
# guidance, written once and mirrored (Nigel, 25/08/2026 -- so the guidance
# is readable from the repo without unzipping a release, and a release
# carries it without needing the repo). If that section changes, edit BOTH
# files -- there is no templating between them, it's a manual mirror.
#
# Usage:
#   ./package.sh
#
# VERSION comes from the sibling VERSION file (one line, e.g. "1.0.0").

set -eu

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$SCRIPT_DIR"

[ -f VERSION ] || { echo "package.sh: VERSION file not found" >&2; exit 1; }
VERSION=$(head -n1 VERSION | tr -d '[:space:]')
[ -n "$VERSION" ] || { echo "package.sh: VERSION file is empty" >&2; exit 1; }

[ -d out ] || { echo "package.sh: out/ not found -- run build_theme.py first" >&2; exit 1; }
[ -f out/themes.json ] || { echo "package.sh: out/themes.json not found -- run build_theme.py first" >&2; exit 1; }
[ -f install.sh ] || { echo "package.sh: install.sh not found" >&2; exit 1; }
[ -f RELEASE-README.md ] || { echo "package.sh: RELEASE-README.md not found" >&2; exit 1; }
[ -f installer-project/Theme_Installer/project.json ] || { echo "package.sh: installer-project/Theme_Installer/project.json not found -- run build_installer.py first" >&2; exit 1; }

RELEASE_NAME="gaskony-themes-$VERSION"
DIST_DIR="dist"
STAGE_DIR="$DIST_DIR/$RELEASE_NAME"
ZIP_PATH="$DIST_DIR/$RELEASE_NAME.zip"

echo "package.sh: building $ZIP_PATH"

rm -rf "$STAGE_DIR" "$ZIP_PATH"
mkdir -p "$STAGE_DIR"

theme_count=0
for d in out/*/; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    [ -f "$d/config.json" ] || continue
    cp -R "$d" "$STAGE_DIR/$name"
    theme_count=$((theme_count + 1))
done

if [ "$theme_count" -eq 0 ]; then
    echo "package.sh: no theme directories found under out/ -- refusing to ship an empty release" >&2
    rm -rf "$STAGE_DIR"
    exit 1
fi

cp out/themes.json "$STAGE_DIR/themes.json"
cp install.sh "$STAGE_DIR/install.sh"
chmod +x "$STAGE_DIR/install.sh"
cp RELEASE-README.md "$STAGE_DIR/RELEASE-README.md"

( cd "$DIST_DIR" && rm -f "$RELEASE_NAME.zip" && zip -rq "$RELEASE_NAME.zip" "$RELEASE_NAME" )

rm -rf "$STAGE_DIR"

echo "package.sh: wrote $ZIP_PATH ($theme_count theme(s))"
echo "package.sh: contents:"
unzip -l "$ZIP_PATH"

# ---------------------------------------------------------------------------
# Theme_Installer-<VERSION>.zip -- a project import zip. project.json goes at
# the zip ROOT (no wrapping folder), same layout tools/build_exports.py uses
# for this repo's own exports/*.zip -- see that script's docstring, it
# verified the format against a real Exchange package export rather than
# guessing. Zipped straight from installer-project/Theme_Installer/ itself
# (no staging copy needed -- there's nothing to filter out, build_installer.py
# writes only project files there).
# ---------------------------------------------------------------------------

INSTALLER_ZIP_NAME="Theme_Installer-$VERSION"
INSTALLER_ZIP_PATH="$DIST_DIR/$INSTALLER_ZIP_NAME.zip"

echo "package.sh: building $INSTALLER_ZIP_PATH"

rm -f "$INSTALLER_ZIP_PATH"
( cd installer-project/Theme_Installer && zip -rq "$OLDPWD/$INSTALLER_ZIP_PATH" . -x '__pycache__/*' )

echo "package.sh: wrote $INSTALLER_ZIP_PATH"
echo "package.sh: contents:"
unzip -l "$INSTALLER_ZIP_PATH"
