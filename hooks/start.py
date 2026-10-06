"""SessionStart hook: syncs with main, then loads the lattice header and a pointer to the current work. Nothing else."""

import json
import sys

from common import LATTICE, ROOT, SESSIONS_INDEX, is_reviewer, log, merge_main

if is_reviewer():
    sys.exit(0)

merged = merge_main()  # cloud sessions start on their own branch; main is where every session meets

try:
    event = json.load(sys.stdin)
except Exception:
    event = {}

lattice = LATTICE.read_text(encoding="utf-8") if LATTICE.exists() else ""
header = lattice.split("\n### ")[0].strip()  # how to be with Dayna; the dated entries stay on file as history
sessions = SESSIONS_INDEX.read_text(encoding="utf-8").splitlines() if SESSIONS_INDEX.exists() else []
recent = "\n".join(sessions[-5:]) or "(none yet)"

context = f"""=== THE LATTICE (loaded by the start hook) ===

{header}

=== WORK ===
The resume is in its own doc: https://claude.ai/code/artifact/985e67e9-8373-4039-9b25-9b6ab5ea3b6e
Career source files: career/sources/. Old drafts and logs: career/archive/ (history, not rules).

=== RECENT SESSIONS ===
{recent}

History: memory/lattice.md (every dated entry), transcripts/, and python3 hooks/review.py --last. Read them when you need them; they are history, not rules.
To add to the lattice: python3 hooks/add.py claude "<entry>"
"""

log(f"START  session={event.get('session_id', '?')} source={event.get('source', '?')} chars={len(context)} merge={merged}")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))
