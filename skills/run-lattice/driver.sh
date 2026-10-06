#!/usr/bin/env bash
# Drives the lattice hooks the way Claude Code does, against a throwaway origin, with two sessions
# on their own branches. Proves they sync every turn. Never touches GitHub or the real lattice.
#   bash skills/run-lattice/driver.sh            sync tests (seconds, no LLM)
set -euo pipefail
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
W=$(mktemp -d); echo "workdir: $W"
git clone -q --bare "$REPO" "$W/origin.git"   # a local copy stands in for GitHub
git -C "$W/origin.git" update-ref refs/heads/main "$(git -C "$REPO" rev-parse HEAD)"
git -C "$W/origin.git" symbolic-ref HEAD refs/heads/main
for s in a b; do
  git clone -q "$W/origin.git" "$W/$s"
  git -C "$W/$s" config commit.gpgsign false   # test clones only; the real repo keeps signing on
  git -C "$W/$s" checkout -q -b "session-$s"
done
hook() { (cd "$W/$1" && echo "$3" | python3 "hooks/$2"); }
pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; exit 1; }

# a fake transcript for session A: Dayna corrects Claude, Claude replies
T="$W/a-transcript.jsonl"
cat > "$T" <<'J'
{"type":"user","message":{"role":"user","content":"Fix only line 3 of the summary."}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"I rewrote the whole summary and added a new skills section so it reads better."}]}}
J

hook a start.py '{"session_id":"aaaa1111","source":"startup"}' | grep -q "THE CURRENT JOB" && pass "start loads the lattice header and the job brief" || fail start
hook b start.py '{"session_id":"bbbb2222","source":"startup"}' > /dev/null

(cd "$W/a" && python3 hooks/add.py claude "driver: lesson from session A") > /dev/null
hook b sync.py '{"session_id":"bbbb2222"}' > /dev/null
grep -q "lesson from session A" "$W/b/memory/lattice.md" && pass "B has A's lesson after its very next turn" || fail "B missed A's lesson"

(cd "$W/a" && python3 hooks/add.py claude "driver: parallel A") > /dev/null
(cd "$W/b" && python3 hooks/add.py claude "driver: parallel B") > /dev/null
L=$(git -C "$W/origin.git" show main:memory/lattice.md)
grep -q "parallel A" <<<"$L" && grep -q "parallel B" <<<"$L" && pass "two sessions writing at once both land on main, no conflict" || fail "parallel writes"

echo "- driver: line written by session B" >> "$W/b/career/brief.md"
hook b sync.py '{"session_id":"bbbb2222"}' > /dev/null
hook a sync.py '{"session_id":"aaaa1111"}' > /dev/null
grep -q "line written by session B" "$W/a/career/brief.md" && pass "a file B changed reaches A next turn" || fail "file sync"

hook a sync.py "{\"session_id\":\"aaaa1111\",\"transcript_path\":\"$T\"}" > /dev/null
git -C "$W/origin.git" show main:memory/sessions.md | grep -q "session aaaa1111  live" && pass "live session saved to main mid-session" || fail "live archive"
(cd "$W/a" && python3 hooks/review.py --live) | grep -q "\[DAYNA\] Fix only line 3" && pass "review.py --live reads this session back" || fail "review --live"
hook b sync.py '{"session_id":"bbbb2222"}' > /dev/null
(cd "$W/b" && python3 hooks/review.py --last) | grep -q "\[CLAUDE\] I rewrote" && pass "review.py --last reads the last session" || fail "review --last"

echo "all passed"
