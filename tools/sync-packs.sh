#!/bin/sh
# Re-pull the vendored source packs from a sibling ignition-styles-template-v2
# checkout.
#
# THE SOURCE IS GONE. ignition-styles-template-v2 is retired: no local
# folder, no GitHub repo, and no full-history bundle at the host-share path
# the workspace docs point to. So packs/ in THIS repo is now the only copy
# of these ten packs, and the only source of truth for them. Edit them here.
#
# The script still works if you ever restore a v2 checkout — pass its path as
# $1 — but it will refuse to run against a missing one rather than failing
# ten times with a bare "No such file".
set -e
SRC="${1:-../ignition-styles-template-v2}/packs"

if [ ! -d "$SRC" ]; then
  echo "sync-packs: no pack source at $SRC" >&2
  echo "sync-packs: ignition-styles-template-v2 is retired and no copy is" >&2
  echo "            known to exist. packs/ here is the source of truth;" >&2
  echo "            edit those files directly, then rerun build_theme.py and" >&2
  echo "            build_installer.py." >&2
  exit 1
fi

for p in aurora-violet aurora-teal leather-night-tan leather-parchment-tan \
         finance-ledger newsprint-night nord-dark-frost nord-light-frost \
         industrial-control-cyan industrial-day-cyan; do
  cp "$SRC/$p.json" packs/
done
echo "packs synced from $SRC -- rerun build_theme.py + build_installer.py"
