"""SessionEnd hook: final save of the transcript and a last publish. No Claude involved.
Most of the work already happened every turn (sync.py), so a missed end loses nothing."""

import json
import sys
from pathlib import Path

from common import SESSIONS_INDEX, archive_transcript, is_reviewer, log, publish

if is_reviewer():
    sys.exit(0)

try:
    event = json.load(sys.stdin)
except Exception:
    event = {}

session = event.get("session_id", "unknown")
reason = event.get("reason", "?")
# Cloud containers warm Claude up before anyone connects; that run has no transcript and gets no index line.
saved = archive_transcript(session, Path(event.get("transcript_path") or ""), f"ended: {reason}") or "(no transcript)"
synced = publish(f"session {session[:8]} ended ({reason})")
log(f"END    session={session} reason={reason} saved={saved} {synced}")
