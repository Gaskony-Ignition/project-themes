#!/usr/bin/env python3
"""Vendor one pack's half of the Styles_Template2 contract.

Called once per pack by tools/sync-contract.sh, which passes V2 / PACK / STOP
in the environment. Writes contract/tokens/<pack>.json (the pack's --st-*
values) and contract/classes/<pack>.json (its 69 class definitions).

Split out of the shell script rather than inlined as a heredoc because
sync-contract.sh already carries one heredoc-free `tail` and nesting a second
python heredoc inside a `for` loop is exactly the shell trap that eats stdin.
"""
import json, os, re, sys

V2   = os.environ["V2"]
PACK = os.environ["PACK"]
STOP = int(os.environ["STOP"])

# ---- tokens: this pack's --st-* block, out of section 1 of the stylesheet ----
css   = os.path.join(V2, "stylesheet", "stylesheet.css")
lines = open(css).read().split("\n")[:STOP]
want, toks, inside = "psc-%s/" % PACK, {}, False
for ln in lines:
    if want in ln and "[class*=" in ln:
        inside = True
    if inside:
        m = re.match(r"\s*(--st-[a-z0-9-]+):\s*(.+?);\s*$", ln)
        if m:
            toks[m.group(1)] = m.group(2).strip()
        elif ln.strip() == "}" and toks:
            break
if not toks:
    sys.exit("no --st-* block found for %s" % PACK)

# ---- classes: the 69 style.json files, consolidated ----
root = os.path.join(V2, "style-classes", PACK)
if not os.path.isdir(root):
    sys.exit("no style classes at %s" % root)
classes = {}
for dp, _, files in os.walk(root):
    if "style.json" in files:
        classes[os.path.relpath(dp, root)] = json.load(
            open(os.path.join(dp, "style.json")))

json.dump(toks,    open("contract/tokens/%s.json"  % PACK, "w"), indent=1, sort_keys=True)
json.dump(classes, open("contract/classes/%s.json" % PACK, "w"), indent=1, sort_keys=True)
print("  %-26s %2d tokens, %d classes" % (PACK, len(toks), len(classes)))
