"""The only way to write to the lattice: append one entry, snapshot first.

usage: python hooks/add.py "<who>" "<entry>"
"""

import sys

from common import LATTICE, append, log, now

if len(sys.argv) < 3 or not sys.argv[2].strip():
    sys.exit('usage: python hooks/add.py "<who>" "<entry>"')

who, entry = sys.argv[1].strip(), " ".join(sys.argv[2:]).strip()
append(LATTICE, f"\n### {now()} | {who}\n{entry}\n")
log(f"ADD    by={who} chars={len(entry)}")
print("added to the lattice")
