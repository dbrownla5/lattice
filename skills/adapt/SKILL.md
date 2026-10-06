---
name: adapt
description: How Claude teaches itself in this repo. Run after every correction from Dayna, at the start of every session on the last session, and whenever the reviewer posts a finding. Claude finds its own fault, checks all its work for it, writes the lesson, and rewrites its own skills. Dayna never signs off on lessons.
---

# Adapt

Every Claude in this repo teaches itself, through the session, while it works. Dayna is not the teacher and not the answer key. Lessons from what happened are Claude's to learn and apply. Dayna only says yes or no to words in Dayna's own documents.

## The loop (run it, don't announce it)
1. **Catch.** A correction from Dayna, a reviewer finding in the lattice, or a rubric check that fails on Claude's own reply.
2. **Name the fault.** Which line of skills/adapt/rubric.md failed? If none fits, the rubric is missing a line: add it.
3. **Sweep.** Look for that same fault on everything Claude made this session, not just the line Dayna pointed at. Fix every one.
4. **Teach.** Add the lesson with `python3 hooks/add.py claude "<lesson>"`. One lesson per entry, short, what happened and what to do instead. It goes to main right away.
5. **Re-engineer.** If the lesson changes how a task is done, edit the skill that does that task in skills/. If no skill covers the task, write one. Skills are Claude's own code: rewrite them like an engineer fixing a bug, and remove a rule that turns out wrong.
6. **Carry on** with Dayna's task using the fixed skill. Don't stop to report the lesson unless Dayna asks.

## At the start of a session
Read the last session's messages before working (`python3 hooks/review.py --last`). Look for where it went wrong and run the loop on each fault before touching Dayna's task.

## The reviewer
After every Claude turn, a second Claude reviews that turn against the rubric (hooks/reviewer.py). What it finds lands in the lattice and shows up at the top of the next turn as new entries. Treat a finding like a correction from Dayna: run the loop. The reviewer only sees the conversation, not the tools or files, so check its claim first. If it's wrong, add a correction with what you checked.

## Rules
- Quote marks only around Dayna's exact words. Everything else is Claude's read, labeled as such.
- Never fill a blank or invent a fact about Dayna.
- Lessons and skill changes never go to Dayna for approval.
- Never change the lattice except through hooks/add.py.
