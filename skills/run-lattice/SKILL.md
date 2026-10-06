---
name: run-lattice
description: Run, test, or debug the lattice hooks (start, per-turn sync, reviewer, end). Use to prove sessions sync with each other, to check the reviewer, or after changing anything in hooks/.
---

# Run the lattice

The lattice is a set of Claude Code hooks (hooks/, registered in .claude/settings.json). Paths are relative to the repo root.

## Run (agent path): the driver
```bash
bash skills/run-lattice/driver.sh            # sync tests, a few seconds, no LLM
bash skills/run-lattice/driver.sh --review   # also runs the real LLM reviewer once, about a minute
```
It copies the repo into a throwaway origin, starts two sessions on their own branches, and feeds the hooks the same JSON Claude Code does. It never touches GitHub or the real lattice. It prints one PASS line per check and `all passed`; the workdir stays in /tmp for inspection.

What it proves: start loads the lattice and skills; a lesson one session adds shows up in the other on its next turn; two sessions writing at once both land on main; a skill one session rewrites reaches the other; the live session saves mid-session; `review.py --live` and `--last` read sessions back; the reviewer grades a reply and the finding reaches the other session.

## Read a session back
```bash
python3 hooks/review.py --last   # the last session before this one
python3 hooks/review.py --live   # this session so far
```

## How it runs in a real session
- SessionStart: `start.py` merges main and loads the lattice, recent sessions, all skills, and the learning rules.
- Every prompt: `sync.py` saves the live transcript, publishes, merges main, and shows Claude only new lattice entries and changed skills.
- After every reply: `review.py` starts `reviewer.py` in the background, which is `claude -p` grading the reply against skills/adapt/rubric.md. Findings go in through add.py, and skill fixes go into skills/.
- SessionEnd: `end.py` does a final save and publish.
- Everything in memory/, skills/, career/ and transcripts/ goes to main as soon as it changes.
- hooks/hook.log (not committed) has one line per hook run; the reviewer's own output is in .git/lattice/reviewer.out.

## Gotchas
- Cloud sessions start on their own branch. Everything syncs through main, by merge and never rebase. memory/lattice.md, memory/sessions.md and career/feedback-log.md union-merge (.gitattributes), so parallel appends don't conflict. Before that, they did, and sessions split apart.
- The reviewer is a Claude session in this folder. `LATTICE_REVIEWER=1` makes every hook exit at once, so it can't trigger itself.
- File times are useless for ordering sessions, because git resets them on checkout. `--last` follows memory/sessions.md.
- In Auto mode, the safety check blocks Claude from editing hooks/ and .claude/, even with Dayna's OK in chat. Switch the mode to Accept edits for hook work.
- The test clones turn commit signing off; the real repo keeps it on, and publish waits for the signer.
- Pushing to a local bare repo failed with `expected 'acknowledgments', received 'packfile'`. The driver clones the bare repo instead.
