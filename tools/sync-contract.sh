#!/bin/sh
# Re-pull the vendored Styles_Template2 CONTRACT from a sibling
# ignition-styles-template-v2 checkout.
#
# Three things come across, and together they are everything a theme needs in
# order to replace the styles parent outright rather than only carry its token
# layer (see build_contract.py's docstring for what that means):
#
#   contract/tokens/<pack>.json   that pack's 40 --st-* token values, which the
#                                 chrome below is written in terms of
#   contract/classes/<pack>.json  the 69-class contract for that pack, one
#                                 consolidated file per pack instead of 69
#                                 separate style.json files
#   contract/chrome.css           sections 2-4 of the shared stylesheet -- the
#                                 component chrome, shell and card grid. Already
#                                 pack-independent and keyed on
#                                 [class*="/family/name"], so they are copied
#                                 VERBATIM and never rewritten.
#
# This is a TRANSITIONAL dependency in one direction only: once styles v2 is
# retired, contract/ is the source of truth and this script stops being run.
# It is deliberately an explicit vendoring step (like sync-packs.sh) rather
# than a build-time read of a sibling checkout, so a clone of this repo builds
# without one.
set -e
SRC="${1:-../ignition-styles-template-v2}"
V2="$SRC/Styles_Template2/com.inductiveautomation.perspective"
CHROME_START=3764   # the "2. RULES" section header; sections 2-4 run to EOF

[ -d "$V2" ] || { echo "no Styles_Template2 at $V2" >&2; exit 2; }

mkdir -p contract/classes contract/tokens

# The chrome, verbatim from the line the section header sits on.
{
  echo "/* Sections 2-4 of Styles_Template2's shared stylesheet, VERBATIM."
  echo " * Vendored by tools/sync-contract.sh -- do not edit here. */"
  tail -n "+$CHROME_START" "$V2/stylesheet/stylesheet.css"
} > contract/chrome.css

for f in packs/*.json; do
  pack=$(basename "$f" .json)
  V2="$V2" PACK="$pack" STOP="$CHROME_START" python3 tools/_sync_contract_pack.py
done

echo "contract synced from $SRC -- rerun build_theme.py + build_installer.py"
