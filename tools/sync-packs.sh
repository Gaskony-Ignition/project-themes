#!/bin/sh
# Re-pull the vendored source packs from a sibling ignition-styles-template-v2
# checkout (the design source of truth). Run when a pack's colours change there.
set -e
SRC="${1:-../ignition-styles-template-v2}/packs"
for p in aurora-violet aurora-teal leather-night-tan leather-parchment-tan \
         finance-ledger newsprint-night nord-dark-frost nord-light-frost \
         industrial-control-cyan industrial-day-cyan; do
  cp "$SRC/$p.json" packs/
done
echo "packs synced from $SRC -- rerun build_theme.py + build_installer.py"
