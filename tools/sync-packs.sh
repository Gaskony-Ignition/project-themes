#!/bin/sh
# Re-pull the vendored source packs from a sibling ignition-styles-template-v2
# checkout.
#
# THE SOURCE IS GONE (checked 01/09/2026). ignition-styles-template-v2 was
# retired on 28/08/2026: the local folder was removed, the GitHub repo deleted,
# and the full-history bundle the workspace docs promised at host-share
# Downloads/gaskony-styles-v2-archive/ was not there. So packs/ in THIS repo is
# now the only copy of these ten packs, and the only source of truth for them.
# Edit them here.
#
# The script still works if you ever restore a v2 checkout — pass its path as
# $1 — but it will refuse to run against a missing one rather than failing
# ten times with a bare "No such file".
set -e
SRC="${1:-../ignition-styles-template-v2}/packs"

if [ ! -d "$SRC" ]; then
  echo "sync-packs: no pack source at $SRC" >&2
  echo "sync-packs: ignition-styles-template-v2 was retired 28/08/2026 and no" >&2
  echo "            copy is known to exist. packs/ here is the source of truth;" >&2
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
