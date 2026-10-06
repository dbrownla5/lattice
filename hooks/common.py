"""Shared paths and helpers for the lattice hooks. Claude never edits these files."""

import datetime
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY = ROOT / "memory"
LATTICE = MEMORY / "lattice.md"
SESSIONS_INDEX = MEMORY / "sessions.md"
HISTORY = MEMORY / ".history"
TRANSCRIPTS = ROOT / "transcripts"
LOG = ROOT / "hooks" / "hook.log"

for d in (MEMORY, HISTORY, TRANSCRIPTS):
    d.mkdir(parents=True, exist_ok=True)


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(line: str) -> None:
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{now()}  {line}\n")


def snapshot(path: Path) -> None:
    """Copy a file into memory/.history before it changes, so nothing is ever lost."""
    if path.exists():
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        shutil.copy2(path, HISTORY / f"{path.stem}_{stamp}{path.suffix}")


def git(*args: str, timeout: int = 30) -> str:
    """Best-effort git call. Sync failures get logged, never raised: a session must start even offline."""
    import subprocess
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0:
            return "ok"
        # The signer prefixes its real error with Debug: chatter; keep the lines that say what went wrong.
        lines = [l for l in (r.stderr or r.stdout).splitlines() if l.strip() and "Debug:" not in l]
        return f"failed({r.returncode}): {' | '.join(lines)[:300]}"
    except Exception as e:
        return f"failed: {e}"


def git_out(*args: str) -> str:
    """Git output for reading state; empty string on any failure."""
    import subprocess
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception:
        return ""


def signer_ready(wait: int = 20) -> bool:
    """Commits here are signed by a program the environment installs once the session attaches.
    Wait for it rather than turn signing off; False means it never showed up."""
    import os
    import time
    if git_out("config", "--get", "commit.gpgsign").lower() != "true":
        return True
    fmt = git_out("config", "--get", "gpg.format") or "openpgp"
    program = git_out("config", "--get", f"gpg.{fmt}.program") or git_out("config", "--get", "gpg.program")
    if not program or not os.path.isabs(program):
        return True  # signer on PATH; let git use it as it normally would
    for _ in range(wait):
        if os.path.exists(program):
            return True
        time.sleep(1)
    return os.path.exists(program)


def append(path: Path, text: str) -> None:
    snapshot(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


# ---- self-teaching sync ----------------------------------------------------------------
import os

SKILLS = ROOT / "skills"
STATE = ROOT / ".git" / "lattice"  # per-clone state: live transcript path, last-seen lattice, reviewer lock
STATE.mkdir(parents=True, exist_ok=True)
# What Claude learns and works on. All of it syncs to main as soon as it changes.
SYNCED = ["memory", "skills", "career", "transcripts", ".gitattributes"]


def is_reviewer() -> bool:
    """The reviewer is itself a Claude session in this folder; its hooks must do nothing."""
    return os.environ.get("LATTICE_REVIEWER") == "1"


def merge_main() -> str:
    """Bring in what other sessions published. Merge, never rebase: the append-only files
    union-merge (.gitattributes), so parallel sessions don't conflict."""
    if not signer_ready():
        return "waiting: commit signer not installed yet"
    git("fetch", "-q", "origin", "main", timeout=20)
    return git("merge", "--no-edit", "origin/main", timeout=30)


def publish(message: str) -> str:
    """Commit what changed in SYNCED and push it to main now, then to this session's branch.
    Runs on every add and every turn, so nothing waits for a session to end."""
    paths = [p for p in SYNCED if (ROOT / p).exists()]
    committed = "nothing new"
    if git_out("status", "--porcelain", "--", *paths):
        if not signer_ready():
            return "waiting: commit signer not installed yet, changes left in place"
        git("add", "-A", "--", *paths)
        committed = git("commit", "-q", "-m", message)
    git("fetch", "-q", "origin", "main", timeout=20)
    if git_out("rev-list", "--count", "origin/main..HEAD") in ("", "0"):
        return f"commit={committed} push=up to date"
    pushed = "?"
    for _ in range(3):  # another session may push between our merge and our push
        merge_main()
        pushed = git("push", "-q", "origin", "HEAD:main", timeout=60)
        if pushed == "ok":
            break
    branch = git_out("rev-parse", "--abbrev-ref", "HEAD")
    if branch and branch not in ("main", "HEAD"):
        git("push", "-q", "-u", "origin", "HEAD", timeout=60)
    return f"commit={committed} main={pushed}"


def archive_transcript(session: str, src: Path, status: str) -> str:
    """Copy a session's transcript into transcripts/ (one file per session) and index it once."""
    if not src.is_file():
        return ""
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    existing = sorted(TRANSCRIPTS.glob(f"*_{session[:8]}.jsonl"))
    dest = existing[0] if existing else TRANSCRIPTS / f"{stamp}_{session[:8]}.jsonl"
    if not dest.exists() or dest.stat().st_size != src.stat().st_size:
        shutil.copy2(src, dest)
    indexed = SESSIONS_INDEX.exists() and f"session {session[:8]} " in SESSIONS_INDEX.read_text(encoding="utf-8")
    if not indexed:
        append(SESSIONS_INDEX, f"- {stamp}  session {session[:8]}  {status}  transcript: {dest.name}\n")
    return dest.name


def entries(text: str) -> list:
    """The lattice's ### entries, each as one string."""
    return ["### " + p.strip() for p in text.split("\n### ")[1:]]


def skills_text(only=None) -> str:
    out = []
    for f in sorted(SKILLS.glob("*/*.md")):
        rel = str(f.relative_to(ROOT))
        if only is None or rel in only:
            out.append(f"--- {rel} ---\n{f.read_text(encoding='utf-8').strip()}")
    return "\n\n".join(out)


def messages(path: Path) -> list:
    """(role, text) for every real user and assistant message in a transcript. Tool calls and
    hook noise are dropped; what's left is the conversation itself."""
    import json
    out = []
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        role = e.get("type")
        if role not in ("user", "assistant"):
            continue
        c = (e.get("message") or {}).get("content")
        if isinstance(c, list):
            c = "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
        c = (c or "").strip()
        if c and not c.startswith("<") and not c.startswith("[Request interrupted"):
            out.append((role, c))
    return out
