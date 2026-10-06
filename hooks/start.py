"""SessionStart hook: syncs with main, then puts the lattice and Claude's own skills straight
into the new session's context. Claude doesn't have to find, fetch, or remember anything."""

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
brief_file = ROOT / "career" / "brief.md"
brief = brief_file.read_text(encoding="utf-8") if brief_file.exists() else ""

sessions = SESSIONS_INDEX.read_text(encoding="utf-8").splitlines() if SESSIONS_INDEX.exists() else []
recent = "\n".join(sessions[-5:]) or "(none yet)"

context = f"""=== THE LATTICE (loaded by the start hook) ===

{header}

=== THE CURRENT JOB ===

{brief}

=== RECENT SESSIONS ===
{recent}

History: memory/lattice.md (every dated entry), transcripts/, and python3 hooks/review.py --last. Read them when you need them; they are history, not rules.
To add to the lattice: python3 hooks/add.py claude "<entry>"
"""

log(f"START  session={event.get('session_id', '?')} source={event.get('source', '?')} chars={len(context)} merge={merged}")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))
