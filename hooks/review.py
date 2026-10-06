"""Read a session back, or (as the Stop hook) start the reviewer on the reply Claude just gave.

  python3 hooks/review.py --last   the last session before this one: every message, Dayna's and Claude's
  python3 hooks/review.py --live   this session so far (Claude reviewing itself mid-session)
"""

import sys
from pathlib import Path

from common import SESSIONS_INDEX, STATE, TRANSCRIPTS, messages


def show(path: Path) -> None:
    print(f"=== {path.name} ===")
    for role, text in messages(path):
        who = "DAYNA" if role == "user" else "CLAUDE"
        if role == "assistant" and len(text) > 1200:
            text = text[:1200] + " …[cut]"
        print(f"\n[{who}] {text}")


def current() -> Path:
    f = STATE / "current_transcript"
    return Path(f.read_text(encoding="utf-8").strip()) if f.exists() else Path("")


import signal
signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # piping into head shouldn't throw

arg = sys.argv[1] if len(sys.argv) > 1 else ""
if arg == "--live":
    show(current())
elif arg == "--last":
    live = current()
    mine = live.stem[:8] if live.name else "-"
    # The session index is in the order sessions happened; file times aren't (git resets them).
    index = SESSIONS_INDEX.read_text(encoding="utf-8").splitlines() if SESSIONS_INDEX.exists() else []
    names = [l.rsplit("transcript: ", 1)[-1].strip() for l in index if "transcript: " in l]
    past = [TRANSCRIPTS / n for n in names if (TRANSCRIPTS / n).is_file() and not n.endswith(f"_{mine}.jsonl")]
    if past:
        show(past[-1])
    else:
        print("(no earlier session archived yet)")
