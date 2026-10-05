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
        return "ok" if r.returncode == 0 else f"failed({r.returncode}): {(r.stderr or r.stdout).strip()[:200]}"
    except Exception as e:
        return f"failed: {e}"


def append(path: Path, text: str) -> None:
    snapshot(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)
