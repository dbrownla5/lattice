"""SessionEnd hook: archives the full transcript and indexes the session. No Claude involved."""

import datetime
import json
import shutil
import sys
from pathlib import Path

from common import SESSIONS_INDEX, TRANSCRIPTS, append, git, git_out, log, signer_ready

try:
    event = json.load(sys.stdin)
except Exception:
    event = {}

session = event.get("session_id", "unknown")
reason = event.get("reason", "?")
src = Path(event.get("transcript_path") or "")
stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")

if src.is_file():
    # One file per session: a later end for the same session refreshes it instead of adding a copy.
    existing = sorted(TRANSCRIPTS.glob(f"*_{session[:8]}.jsonl"))
    dest = existing[0] if existing else TRANSCRIPTS / f"{stamp}_{session[:8]}.jsonl"
    shutil.copy2(src, dest)
    saved = dest.name
    indexed = SESSIONS_INDEX.exists() and f"session {session[:8]} " in SESSIONS_INDEX.read_text(encoding="utf-8")
    if not indexed:
        append(SESSIONS_INDEX, f"- {stamp}  session {session[:8]}  ended: {reason}  transcript: {saved}\n")
else:
    # Cloud containers warm Claude up before anyone connects; that run ends with no conversation
    # and no transcript file. Nothing happened, so it gets no index line.
    saved = "(no transcript: session never had a conversation)"

committed = pushed = "skipped"
if not git_out("status", "--porcelain"):
    committed = "nothing to commit"
elif not signer_ready():
    committed = "waiting: commit signer not installed yet, changes left in place"
else:
    git("add", "-A")
    committed = git("commit", "-m", f"session {session[:8]} ({stamp})")
if committed == "ok":
    git("pull", "--rebase", "--autostash", "origin", "main")
    pushed = git("push", "origin", "HEAD:main", timeout=60)
    if pushed != "ok":
        # Some cloud sessions may only push to their own branch; keep the work rather than lose it.
        pushed = "main " + pushed + " | branch " + git("push", "-u", "origin", "HEAD", timeout=60)
log(f"END    session={session} reason={reason} saved={saved} commit={committed} push={pushed}")
