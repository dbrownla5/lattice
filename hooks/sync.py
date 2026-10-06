"""UserPromptSubmit hook, every turn: save the live session, publish to main, pull from main. Silent."""

import json
import sys
from pathlib import Path

from common import ROOT, STATE, archive_transcript, log_dayna_messages, git_out, is_reviewer, log, merge_main, publish

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

logged = log_dayna_messages(session, src)
saved = archive_transcript(session, src, "live")
published = publish(f"session {session[:8]}: live sync")
merged = merge_main()

log(f"SYNC   session={session} dayna_msgs={logged} saved={saved or '-'} {published} merge={merged}")
