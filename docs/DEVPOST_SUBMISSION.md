# Rehearsal — Devpost Submission Draft

## Tagline

See what your agent will do. Correct the future. Then commit it.

## Inspiration

AI agents ask people to approve commands, tool calls, and permissions. Most people cannot infer the real-world consequences of those technical steps. They understand outcomes: which files disappear, what breaks, who receives a message, or what amount gets charged.

Rehearsal explores a new interaction primitive: approve the simulated future, not the opaque action sequence.

## What it does

Rehearsal runs a coding-agent task in an isolated Git worktree and turns the result into a measured future-state preview. It shows deleted and changed files, disk delta, broken references, test results, and Outcome Contract violations.

A user can correct the unwanted future in plain English. GPT-5.6 compiles that correction into a bounded, monotonic Outcome Contract. Rehearsal simulates again, then allows approval only for the exact preview ID and patch digest. It applies the exact binary patch, re-measures hashes, tests, and contract proof, emits an execution receipt, and supports verified rollback.

## How we built it

- Python standard library only
- Native Git detached worktrees and binary patches
- SHA-256 state snapshots
- GPT-5.6 Responses API for semantic contract compilation and path-free consequence explanation
- Deterministic mechanics for diff, tests, hashes, approval, and rollback
- Local responsive HTML/CSS/JavaScript UI
- 51 automated behavior, security, recovery, and HTTP/UI tests

Codex GPT-5.6 served as the sole product-code implementation owner in one canonical official Codex thread. Dyra directed product scope, research, media, and independent acceptance without becoming a second code owner.

## Challenges

The hardest problem was making approval meaningful. A normal confirmation dialog approves an intention, not a specific result. Rehearsal binds approval to one preview ID, patch digest, HEAD, index metadata, and file-state snapshot.

Real browser acceptance also exposed two subtle bugs: a newly visible Approve button was briefly disabled, and stale JavaScript caching preserved the old behavior. Both received failing regression tests before fixes.

A security review exposed unsafe workspace deletion, cross-site local requests, approval TOCTOU, contract weakening, unverifiable recovery, and protected-path ambiguity. The final artifact fails closed on these boundaries.

## Accomplishments

- Real unsafe first rehearsal derived from repository state
- Natural-language correction into an enforceable Outcome Contract
- Exact preview-to-reality verification
- Verified process-local apply and rollback recovery
- Loopback-only, Origin/Host-protected local server
- 51 passing tests
- Full browser path verified: reset → rehearse → correct → approve → receipt → rollback
- No third-party dependencies

## What we learned

Git worktrees isolate state but do not sandbox code execution. Rehearsal therefore supports only its bundled trusted seed in this Build Week slice. Supporting arbitrary repositories honestly requires a container or VM boundary.

We also learned that model reasoning should never decide whether mechanical proof passed. GPT-5.6 handles semantics; deterministic tools own file lists, hashes, test outcomes, contract proof, approval, and rollback.

## What's next

- Container/VM isolation for untrusted repositories
- Adapters for email, calendars, cloud infrastructure, and purchases
- Richer consequence graph and policy contracts
- Signed portable execution receipts
- Agent-framework integration as a reusable outcome-approval layer

## Testing

```sh
python3 -m unittest discover -v
./scripts/verify-clean.sh
```

Expected result:

```text
Ran 51 tests
OK
ready → unsafe → safe → applied → rolled_back
verified: true
rollback: completed and verified
```

## Links

- Repository: https://github.com/dhansxd/rehearsal
- Demo video: https://youtu.be/-yZ-59OqS2w
- Codex `/feedback` session proof: `019f7351-793e-7093-bc96-72e49183379b` (canonical official GPT-5.6 Codex thread; feedback form submitted)

## Honest scope

Rehearsal is a single-user loopback demonstration for one trusted seeded Git/filesystem scenario. It is not a production sandbox for arbitrary repositories and does not claim to predict external side effects.
