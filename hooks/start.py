"""SessionStart hook: puts the lattice straight into the new session's context.

Claude doesn't have to find, fetch, or remember anything. The app runs this.
"""

import json
import sys

from common import LATTICE, SESSIONS_INDEX, git, log

# Always sync against main: cloud sessions start on their own branch with no upstream.
pulled = git("pull", "--rebase", "--autostash", "origin", "main", timeout=20)

MAX_CHARS = 60_000  # newest material wins if the lattice grows past this

try:
    event = json.load(sys.stdin)
except Exception:
    event = {}

lattice = LATTICE.read_text(encoding="utf-8") if LATTICE.exists() else ""
if len(lattice) > MAX_CHARS:
    lattice = "...(older entries kept in memory/lattice.md)...\n" + lattice[-MAX_CHARS:]

sessions = SESSIONS_INDEX.read_text(encoding="utf-8").splitlines() if SESSIONS_INDEX.exists() else []
recent = "\n".join(sessions[-10:]) or "(none yet)"

context = f"""=== THE LATTICE (loaded automatically by the start hook; you didn't have to look for it) ===

{lattice}

=== RECENT SESSIONS ===
{recent}

To add to the lattice, run:  python hooks/add.py "<your name or 'claude'>" "<what to keep>"
That's the only way in. It appends; it never overwrites. You can't edit memory/ directly, by design.
"""

log(f"START  session={event.get('session_id', '?')} source={event.get('source', '?')} chars={len(context)} pull={pulled}")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))
