"""The reviewer: a second Claude grades the reply Claude just gave against skills/adapt/rubric.md.
A fault becomes a lattice entry (via add.py) and, when it changes how a task is done, a fix to the
skill in skills/. Both reach main at once, and the working session sees them on its next turn.

usage: python3 hooks/reviewer.py <transcript.jsonl>   (normally started by review.py, the Stop hook)
"""

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

from common import LATTICE, ROOT, SKILLS, STATE, log, messages, publish

MODEL = "claude-sonnet-5-5"
path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("")
lock = STATE / "review.lock"
if lock.exists() and time.time() - lock.stat().st_mtime < 600:
    sys.exit(0)  # one reviewer at a time; the next turn's review covers what this one skips
lock.write_text(str(os.getpid()))
try:
    convo = messages(path)
    if not convo or convo[-1][0] != "assistant":
        sys.exit(0)
    reply = convo[-1][1]
    digest = hashlib.sha1(reply.encode()).hexdigest()
    done = STATE / "reviewed.txt"
    if done.exists() and digest in done.read_text():
        sys.exit(0)

    window = "\n\n".join(f"[{'DAYNA' if r == 'user' else 'CLAUDE'}] {t[:3000]}" for r, t in convo[-8:])
    lattice = LATTICE.read_text(encoding="utf-8")[-20000:]
    rubric = (SKILLS / "adapt" / "rubric.md").read_text(encoding="utf-8")
    skills = "\n".join(str(p.relative_to(ROOT)) for p in sorted(SKILLS.glob("*/*.md")))

    prompt = f"""You are the reviewer in Dayna's lattice repo. You grade the LAST Claude reply below against the rubric, so the working Claude can teach itself. You never talk to Dayna.

RUBRIC:
{rubric}

RECENT LATTICE (what Claude has already learned; don't repeat a lesson that's already here):
{lattice}

SKILLS IN THIS REPO (yours to fix when a fault comes from one):
{skills}

THE CONVERSATION, last messages; grade only the final CLAUDE reply:
{window}

Do this:
1. Grade the final CLAUDE reply on every rubric line, silently.
2. If every line passes, reply with the single word CLEAN and do nothing else.
3. For each real fault (at most two, worst first), run:
   python3 hooks/add.py reviewer "Reviewer finding: <rubric check> failed. <what happened in that reply>. Next time: <what to do instead>."
   Quote marks only around Dayna's exact words from the conversation. Don't invent facts. One or two sentences per part.
4. If the fault came from a skill in skills/ (a rule that's missing, wrong, or unclear), make the smallest edit to that skill that fixes it. Edit nothing outside skills/.
5. Finish with one line: what you found and what you changed."""

    r = subprocess.run(["claude", "-p", prompt, "--model", MODEL,
                        "--allowedTools", "Bash(python3 hooks/add.py:*)", "Read", "Edit(skills/**)", "Write(skills/**)"],
                       cwd=ROOT, capture_output=True, text=True, timeout=600,
                       env={**os.environ, "LATTICE_REVIEWER": "1"})
    verdict = (r.stdout or r.stderr).strip().splitlines()[-1:] or ["(no output)"]
    with open(done, "a") as f:
        f.write(digest + "\n")
    synced = publish("reviewer: skill fixes")
    log(f"REVIEW done verdict={verdict[0][:200]} {synced}")
finally:
    lock.unlink(missing_ok=True)
