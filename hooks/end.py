"""SessionEnd hook: archives the full transcript and indexes the session. No Claude involved."""

import datetime
import json
import shutil
import sys
from pathlib import Path

from common import SESSIONS_INDEX, TRANSCRIPTS, append, git, log

try:
    event = json.load(sys.stdin)
except Exception:
    event = {}

session = event.get("session_id", "unknown")
src = Path(event.get("transcript_path") or "")
stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
dest = TRANSCRIPTS / f"{stamp}_{session[:8]}.jsonl"

if src.is_file():
    shutil.copy2(src, dest)
    saved = dest.name
else:
    saved = "(no transcript found)"

append(SESSIONS_INDEX, f"- {stamp}  session {session[:8]}  ended: {event.get('reason', '?')}  transcript: {saved}\n")
git("add", "-A")
committed = git("commit", "-m", f"session {session[:8]} ({stamp})")
synced = git("pull", "--rebase", "--autostash") if committed == "ok" else "skipped"
pushed = git("push", timeout=60) if committed == "ok" else "skipped"
log(f"END    session={session} reason={event.get('reason', '?')} saved={saved} commit={committed} push={pushed}")
