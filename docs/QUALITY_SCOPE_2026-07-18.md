# Rehearsal — 3-Day Quality Scope Lock

Status: implementation-ready
Date: 2026-07-18
Deadline: 2026-07-21 17:00 PDT
Implementation owner: canonical Codex session `019f7351-793e-7093-bc96-72e49183379b`

## Positioning lock

**Approve outcomes, not actions.**

Rehearsal combines established infrastructure-plan, agent-approval, sandbox, policy, verification, and compensation patterns into one approval-bound transaction for agent actions:

`intent → simulate → correct → approve digest → apply matching artifact → observe → verify contract → rollback/commit → receipt`

Defensible distinction: reviewer approves a simulated future state and its Outcome Contract, not an opaque command, tool call, or intent summary.

Do not claim first approval, sandbox, dry-run, policy engine, verification, rollback, auditable agent, cryptographic correctness, production safety, arbitrary-repository safety, or enterprise readiness.

## Product scope lock

Supported:

- bundled trusted demo seed only;
- local, single-user, loopback-only runtime;
- Git/filesystem cleanup transaction;
- concrete preview, natural-language correction, contract revision, exact apply, observed verification, verified rollback, receipt.

Explicitly unsupported:

- arbitrary repositories;
- host-safe execution of untrusted tests;
- multi-user or remote deployment;
- production sandbox guarantees;
- irreversible external side effects;
- enterprise authentication, RBAC, SSO, SIEM, or compliance.

## P0 — must ship

### 1. Plain-language state and safety

Every state answers whether original workspace changed:

- `Preview only — your project has not changed.`
- `Blocked — issues must be fixed.`
- `Ready for review — no changes applied yet.`
- `Applied — exact approved preview verified.`
- `Rollback complete — original state restored.`

Acceptance:

- state never depends on color alone;
- approval hidden/disabled until every required check passes;
- CTA states effect, e.g. `Approve deletion of 2 files`;
- all paths and reasons visible before approval.

### 2. Persistent structured errors

Replace native `alert()` with panel containing operation, whether workspace changed, safe message, technical detail, run ID, and valid retry/reset/rollback actions.

Acceptance:

- `role="alert"`;
- focus moves to error heading;
- error persists until resolved/dismissed;
- apply/verify failure says fail-closed explicitly;
- rollback failure never claims restoration.

### 3. Accessibility and layout

Acceptance:

- no fixed footer covering content;
- clear `:focus-visible`;
- `aria-busy`, status/alert roles;
- `prefers-reduced-motion`;
- 44×44 pointer targets;
- 320 CSS px and 200% zoom without horizontal overflow or hidden content;
- no important 11px text;
- keyboard flow complete.

### 4. Contract correctness

Acceptance:

- reject same canonical path in `must_change` and `must_preserve`;
- normalize path aliases according to explicit demo policy;
- unknown deterministic-fallback correction fails explicitly instead of silent unchanged contract;
- proof label says exactly `Markdown inline local-link scan`.

### 5. Approval freshness

Acceptance:

- approval expires after bounded interval;
- reset, correction, rerun, apply, and rollback invalidate obsolete approval;
- stale or replayed approval hard-refused;
- tests cover expiry and replay.

### 6. HTTP boundary minimum

Acceptance:

- `Content-Length` constrained to `0..16384`, negative/invalid/duplicate rejected;
- bounded socket/read timeout;
- generic client errors, no raw internal exception leak;
- CSP, `X-Content-Type-Options`, frame policy;
- random per-process mutation nonce required for POST;
- tests cover malformed headers, nonce, timeout behavior where practical.

## P1 — ship if P0 green

### 7. Inspectable receipt

Minimum visible/exported fields:

- transaction/run ID;
- repository/workspace and branch;
- base HEAD/state digest;
- preview ID and full patch digest;
- contract digest and revision;
- generated/approved timestamps with timezone;
- model/explanation mode;
- checks and pass totals;
- observed state digest;
- rollback class and verification result.

Acceptance:

- preview, apply, verify, rollback linked by same transaction identity;
- full hashes copyable;
- receipt downloadable as JSON;
- `Verified` links to `How verified`.

### 8. Progress observability

Named stages: candidate workspace, task execution, diff measured, tests, contract, review, apply, reverify, rollback.

Acceptance:

- operation >500ms shows current stage and `aria-busy`;
- no unlabeled spinner;
- failed stage gives valid next action.

### 9. Crash-durable journal and process lease

Only if achievable without destabilizing P0:

- atomic JSON journal states `prepared`, `applying`, `verified`, `rolling_back`, `recovered`;
- startup reconciliation;
- process-level lease;
- crash-injection tests.

If not fully proven, document as post-hackathon limitation; do not half-claim durability.

## Required tests

- focused RED before each change;
- full unit suite;
- contract path conflict and fallback unknown correction;
- approval expiry/replay;
- malformed and duplicate HTTP header matrix;
- mutation nonce;
- frontend error panel and accessibility state;
- keyboard/browser flow;
- clean script;
- syntax/compile/diff checks;
- live browser full judge path after fresh restart and cache-busted assets.

## Deferred deliberately

- arbitrary repo support;
- host/container/VM sandbox;
- multi-process transaction atomicity beyond explicit demo limits;
- full Git/filesystem semantics: symlink, xattr, submodule, hardlink, sparse checkout;
- external deployment of destructive runtime;
- auth/RBAC/SSO;
- irreversible side-effect compensation;
- live OpenAI canary unless official credential is already safely available.

## Video implications

Final video must show:

1. opaque action approval problem;
2. preview explicitly changing no original files;
3. unsafe deletion and blocker;
4. natural-language correction becoming stricter contract revision;
5. corrected future preserving protected file;
6. exact approval and digest linkage;
7. observed checks and receipt;
8. one fail-closed proof, preferably stale approval refusal;
9. verified rollback;
10. close: `Approve outcomes, not actions.`

No claim beyond measured demo evidence.
