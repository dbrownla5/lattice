"""UserPromptSubmit hook, every turn: save the live session, publish what this session learned,
pull what every other session (and the reviewer) learned, and show Claude only what's new."""

import json
import sys
from pathlib import Path

from common import LATTICE, ROOT, STATE, archive_transcript, entries, git_out, is_reviewer, log, merge_main, publish, skills_text

if is_reviewer():
    sys.exit(0)

try:
    event = json.load(sys.stdin)
except Exception:
    event = {}
session = event.get("session_id", "unknown")
src = Path(event.get("transcript_path") or "")
if src.is_file():
    (STATE / "current_transcript").write_text(str(src), encoding="utf-8")

saved = archive_transcript(session, src, "live")
before = git_out("rev-parse", "HEAD")
published = publish(f"session {session[:8]}: live sync")
merged = merge_main()
after = git_out("rev-parse", "HEAD")

seen_file = STATE / "seen_lattice.md"
seen = set(entries(seen_file.read_text(encoding="utf-8"))) if seen_file.exists() else set()
now_text = LATTICE.read_text(encoding="utf-8") if LATTICE.exists() else ""
new = [e for e in entries(now_text) if e not in seen]
seen_file.write_text(now_text, encoding="utf-8")

changed = []
if before and after and before != after:
    changed = [p for p in git_out("diff", "--name-only", before, after, "--", "skills").splitlines() if p.endswith(".md")]

parts = []
if new:
    parts.append("=== NEW IN THE LATTICE SINCE YOUR LAST TURN (other sessions, the reviewer, or you) ===\n\n" + "\n\n".join(new)
                 + "\n\nIf any of these is a finding about you, run the adapt loop (skills/adapt/SKILL.md) before answering.")
if changed:
    parts.append("=== SKILLS CHANGED ON MAIN SINCE YOUR LAST TURN ===\n\n" + skills_text(set(changed)))

log(f"SYNC   session={session} saved={saved or '-'} {published} merge={merged} new_entries={len(new)} skills_changed={len(changed)}")
if parts:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "\n\n".join(parts)}}))
