"""SessionStart hook: puts the lattice straight into the new session's context.

Claude doesn't have to find, fetch, or remember anything. The app runs this.
"""

import json
import sys

from common import LATTICE, SESSIONS_INDEX, TRANSCRIPTS, git, log

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

RECENT_CHARS = 25_000  # how much of our last conversations to carry in; newest wins
MY_REPLY_CHARS = 600  # Dayna's words come in whole; my replies are cut short


def said(path):
    """What was actually said in one saved session: Dayna's words exactly, my replies trimmed."""
    lines = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(raw)
        except Exception:
            continue
        if d.get("type") not in ("user", "assistant") or d.get("isMeta"):
            continue
        content = (d.get("message") or {}).get("content")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        else:
            continue
        text = text.strip()
        if not text or text.startswith("<"):  # system and tool plumbing, not conversation
            continue
        if d["type"] == "user":
            lines.append(f"DAYNA: {text}")
        else:
            lines.append(f"CLAUDE: {text[:MY_REPLY_CHARS]}{'...' if len(text) > MY_REPLY_CHARS else ''}")
    return "\n".join(lines)


this_session = str(event.get("session_id", ""))[:8]
recent_talk = []
for path in sorted(TRANSCRIPTS.glob("*.jsonl"), reverse=True):
    if this_session and path.stem.endswith(this_session):
        continue
    talk = said(path)
    if talk:
        recent_talk.insert(0, f"--- {path.stem} ---\n{talk}")
    if sum(len(t) for t in recent_talk) >= RECENT_CHARS:
        break
conversation = "\n\n".join(recent_talk)
if len(conversation) > RECENT_CHARS:
    conversation = "..." + conversation[-RECENT_CHARS:]
conversation = conversation or "(none saved yet)"

context = f"""=== THE LATTICE (loaded automatically by the start hook; you didn't have to look for it) ===

{lattice}

=== RECENT SESSIONS ===
{recent}

=== OUR LAST CONVERSATIONS (what was actually said; Dayna's words are exact, Claude's are trimmed) ===
{conversation}

How you learn here: Dayna does not approve, curate, or say "keep that." Learning is your job. When a piece of
real work ends, add what you learned on your own, following the learning protocol in the lattice:
    python hooks/add.py "claude" "<what you learned>"
That's the only way in. It appends; it never overwrites. You can't edit memory/ directly, by design.
"""

log(f"START  session={event.get('session_id', '?')} source={event.get('source', '?')} chars={len(context)} pull={pulled}")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))
