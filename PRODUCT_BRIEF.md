# Rehearsal — OpenAI Build Week 2026

## Product

**Tagline:** See what your agent will do. Correct the future. Then commit it.

Rehearsal is an open-source outcome-approval layer for AI coding agents. It runs an agent task in an isolated Git worktree, converts the simulated result into a human-readable future-state preview, lets the user correct unwanted consequences in natural language, re-simulates, and applies only the approved state. It then verifies reality matches the approved preview and supports rollback.

## Problem

Agent approval today exposes commands and tool calls. Users understand consequences, not implementation steps. They must choose blind trust or technical micromanagement.

## Required vertical slice

1. Load a seeded demo repository.
2. User requests project cleanup.
3. Run first simulation in isolated Git worktree.
4. Show concrete consequences: deleted files, changed files, disk delta, test result, broken references/imports, preserved/violated contract clauses.
5. First simulation must intentionally reveal an unsafe consequence from genuine repository state, not hardcoded UI text.
6. User corrects outcome in natural language.
7. GPT-5.6 compiles correction into structured Outcome Contract clauses.
8. Codex re-simulates according to revised contract.
9. Show second future state with tests passing and protected files preserved.
10. User approves outcome.
11. Apply the exact approved patch/state to real demo workspace.
12. Verify file hashes, Git diff, tests, and contract proof match preview.
13. Emit execution receipt.
14. One-click rollback restores original state.

## Outcome Contract

Minimum schema:

```json
{
  "intent": "remove unused project files",
  "must_change": [],
  "must_preserve": [],
  "forbidden": [],
  "proof": [],
  "rollback": "git checkpoint"
}
```

## Technical constraints

- One implementation owner: this canonical Codex session.
- Must use GPT-5.6 meaningfully in runtime for contract compilation and semantic consequence explanation.
- Codex must build majority core functionality in this session for `/feedback` eligibility.
- Strict vertical TDD: failing behavior test, confirm RED, minimum implementation, confirm GREEN.
- Prefer Python stdlib and native Git. Add dependencies only when they materially shorten a working UI/API.
- Project must run locally from clean instructions.
- No edits outside this repository.
- Never execute arbitrary user shell input.
- Sandbox scope restricted to project-owned seeded demo workspace/worktree.
- No fake success, hardcoded test results, or fabricated consequence cards.
- Honest scope: Git/filesystem coding tasks only.

## Product quality

- Dark, polished, clear UI suitable for a 90-second demo.
- Main visual: before/after future-state diff and Outcome Contract.
- Red unsafe first rehearsal, green corrected rehearsal, verified applied state, rollback.
- Responsive desktop browser layout.
- Accessibility: keyboard controls, semantic labels, sufficient contrast.

## Verification

Required automated tests:

- worktree isolation;
- consequence extraction from real diff;
- contract violation detection;
- correction changes contract scope;
- approval cannot apply stale preview;
- apply result matches approved hashes/diff;
- failing tests block approval;
- rollback restores initial tree;
- path traversal and arbitrary command input rejected.

Required clean demo check:

```text
fresh clone/setup → start app → run unsafe rehearsal → correct → safe rehearsal → approve → verify → rollback
```

## Submission deliverables

- MIT license.
- English README with setup, architecture, demo path, safety boundaries, Codex/GPT-5.6 collaboration.
- Tests and seeded demo fixture.
- Screenshot-ready UI.
- No copyrighted assets or customer data.
