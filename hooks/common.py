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
