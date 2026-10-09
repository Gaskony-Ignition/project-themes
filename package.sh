#!/bin/sh
# package.sh -- build dist/ignition-themes-<VERSION>.zip
#
# POSIX sh. Does NOT regenerate anything -- run `python3 build_theme.py`
# (rebuilds out/) first. This always packages the current state of out/, not a
# stale one. Refuses to run if it is missing, rather than silently packaging
# an empty/partial release.
#
# Contents of ignition-themes-<VERSION>.zip (all inside one top-level
# ignition-themes-<VERSION>/ folder, so extracting it never sprays files into
# the current directory):
#   - every theme directory, copied verbatim from out/
#   - out/themes.json
#   - install.sh (this repo's copy -- see below for why it's shared)
#   - RELEASE-README.md
#   - LICENSE (Apache-2.0; the project is public, so the artefact carries it)
#
# RELEASE-README.md's quick start mirrors README.md's "How to use it" by hand; edit both if install steps change.
#
# Usage:
#   ./package.sh
#
# VERSION comes from the sibling VERSION file (one line, e.g. "1.0.0").

set -eu

# Repo gate (REPO-STANDARD.md). Blocking; bypass deliberately with --skip-readme-check.
_skip=0
for _a in "$@"; do [ "$_a" = "--skip-readme-check" ] && _skip=1; done
if [ "$_skip" -ne 1 ]; then
    _repo=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
    _gate=""; _d="$_repo"
    while [ "$_d" != / ]; do
        [ -x "$_d/modules/readme-gate.sh" ] && { _gate="$_d/modules/readme-gate.sh"; break; }
        _d=$(dirname "$_d")
    done
    if [ -n "$_gate" ]; then
        "$_gate" "$_repo" || { echo "repo gate failed: fix the README/tree or pass --skip-readme-check" >&2; exit 1; }
    else
        echo "readme-gate.sh not found above $_repo; gate skipped" >&2
    fi
fi

# Lint gate (ign-lint + pylint via modules/lint-gate.sh). Blocking; bypass deliberately with --skip-lint-check.
_skip_lint=0
for _a in "$@"; do [ "$_a" = "--skip-lint-check" ] && _skip_lint=1; done
if [ "$_skip_lint" -ne 1 ]; then
    _repo=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
    _lint=""; _d="$_repo"
    while [ "$_d" != / ]; do
        [ -x "$_d/modules/lint-gate.sh" ] && { _lint="$_d/modules/lint-gate.sh"; break; }
        _d=$(dirname "$_d")
    done
    [ -n "$_lint" ] || { echo "lint-gate.sh not found above $_repo; pass --skip-lint-check" >&2; exit 1; }
    "$_lint" "$_repo" || { echo "lint gate failed: fix the findings or pass --skip-lint-check" >&2; exit 1; }
fi

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$SCRIPT_DIR"

[ -f VERSION ] || { echo "package.sh: VERSION file not found" >&2; exit 1; }
VERSION=$(head -n1 VERSION | tr -d '[:space:]')
[ -n "$VERSION" ] || { echo "package.sh: VERSION file is empty" >&2; exit 1; }

[ -d out ] || { echo "package.sh: out/ not found -- run build_theme.py first" >&2; exit 1; }
[ -f out/themes.json ] || { echo "package.sh: out/themes.json not found -- run build_theme.py first" >&2; exit 1; }
python3 tools/check_contrast.py || { echo "package.sh: a theme misses WCAG 2.1 AA contrast (above)" >&2; exit 1; }
python3 tools/check_alarm_contrast.py || { echo "package.sh: an alarm row misses WCAG 2.1 AA contrast (above)" >&2; exit 1; }
[ -f install.sh ] || { echo "package.sh: install.sh not found" >&2; exit 1; }
[ -f RELEASE-README.md ] || { echo "package.sh: RELEASE-README.md not found" >&2; exit 1; }
[ -f LICENSE ] || { echo "package.sh: LICENSE not found" >&2; exit 1; }

RELEASE_NAME="ignition-themes-$VERSION"
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
cp LICENSE "$STAGE_DIR/LICENSE"

( cd "$DIST_DIR" && rm -f "$RELEASE_NAME.zip" && zip -rq "$RELEASE_NAME.zip" "$RELEASE_NAME" )

rm -rf "$STAGE_DIR"

echo "package.sh: wrote $ZIP_PATH ($theme_count theme(s))"
echo "package.sh: contents:"
unzip -l "$ZIP_PATH"
