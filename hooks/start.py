"""SessionStart hook: syncs with main, then puts the lattice and Claude's own skills straight
into the new session's context. Claude doesn't have to find, fetch, or remember anything."""

import json
import sys

from common import LATTICE, SESSIONS_INDEX, STATE, is_reviewer, log, merge_main, skills_text

if is_reviewer():
    sys.exit(0)

merged = merge_main()  # cloud sessions start on their own branch; main is where every session meets

try:
    event = json.load(sys.stdin)
except Exception:
    event = {}

MAX_CHARS = 60_000  # newest material wins if the lattice grows past this
lattice = LATTICE.read_text(encoding="utf-8") if LATTICE.exists() else ""
(STATE / "seen_lattice.md").write_text(lattice, encoding="utf-8")  # sync.py shows only what's new after this
if len(lattice) > MAX_CHARS:
    lattice = "...(older entries kept in memory/lattice.md)...\n" + lattice[-MAX_CHARS:]

sessions = SESSIONS_INDEX.read_text(encoding="utf-8").splitlines() if SESSIONS_INDEX.exists() else []
recent = "\n".join(sessions[-10:]) or "(none yet)"

context = f"""=== THE LATTICE (loaded automatically by the start hook; you didn't have to look for it) ===

{lattice}

=== RECENT SESSIONS ===
{recent}

=== YOUR SKILLS (skills/, yours to rewrite; they sync to main every turn) ===

{skills_text()}

=== HOW YOU LEARN HERE ===
You teach yourself, through the session, with no sign-off from Dayna: follow skills/adapt/SKILL.md.
First thing, before Dayna's task: python3 hooks/review.py --last  (the last session, Dayna's words and yours) and run the adapt loop on what went wrong.
To add to the lattice:  python3 hooks/add.py claude "<lesson>"  (appends only, goes to main at once).
Every turn, a hook syncs with main and a reviewer grades your last reply against skills/adapt/rubric.md; its findings show up as new lattice entries.
"""

log(f"START  session={event.get('session_id', '?')} source={event.get('source', '?')} chars={len(context)} merge={merged}")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))
