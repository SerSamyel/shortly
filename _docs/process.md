# Process

## Tasks

- Tasks are GitHub issues in this repository. The issue tracker is the only backlog.
- `_docs/backlog/` holds the initial groomed issues; `scripts/create-issues.ps1` imports them once. After import, edit issues on GitHub, not these files.
- One issue at a time per agent. Read the acceptance criteria before starting and again before finishing.
- Every issue is groomed (see `_docs/task-template.md`) before anyone implements it.
- Commit regularly. Reference the issue in commit messages: `Add alias validation (#12)`.

## Agent team

| Role | Definition | Does | Never does |
| --- | --- | --- | --- |
| PM | `_docs/team/pm.md` | Grooms an issue into goal, checkable acceptance criteria, out of scope, constraints | Writes code |
| Software engineer | `_docs/team/software-engineer.md` | Implements one groomed issue with tests | Changes acceptance criteria, closes issues |
| QA engineer | `_docs/team/qa-engineer.md` | Verifies the running code against every criterion, posts PASS or FAIL | Fixes code |

The roles are also registered as Claude Code subagents in `.claude/agents/`.

## Orchestrator

The main session is the orchestrator. It launches the roles as subagents, each in a fresh context.
It does not groom, implement or test itself.

Lifecycle of one issue:

1. Pick the next open issue that is not blocked
2. PM grooms it (skip only if the issue already carries the `groomed` label)
3. Engineer implements it
4. QA verifies it and posts `## QA: PASS` or `## QA: FAIL`
5. On FAIL, back to step 3 with the QA comment as input
6. On PASS, the orchestrator closes the issue
7. Repeat until the backlog is empty

Rules:

- QA always runs in a fresh context, never in the session that wrote the code
- The orchestrator closes an issue only after a QA PASS comment exists on it

## Parallel work

When several open issues touch different areas, the orchestrator may run up to three issues in parallel:

- Each issue gets its own git worktree and branch `issue-<n>`
- Issues that touch the same files are never run at the same time
- Finished work is merged into `main` one issue at a time, after QA PASS
- The worktree is removed after the merge

## Running the backlog

`/goal work through the backlog` - the stop condition is "no open issues without the `blocked` label".
