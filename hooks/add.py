"""The only way to write to the lattice: append one entry, snapshot first, publish to main at once.

usage: python hooks/add.py "<who>" "<entry>"
"""

import sys

from common import LATTICE, append, log, now, publish

if len(sys.argv) < 3 or not sys.argv[2].strip():
    sys.exit('usage: python hooks/add.py "<who>" "<entry>"')

who, entry = sys.argv[1].strip(), " ".join(sys.argv[2:]).strip()
append(LATTICE, f"\n### {now()} | {who}\n{entry}\n")
synced = publish(f"lattice: {who} adds an entry")
log(f"ADD    by={who} chars={len(entry)} {synced}")
print(f"added to the lattice ({synced})")
