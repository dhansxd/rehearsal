# Competitive landscape and defensible novelty

Date: 2026-07-18

## Research boundary

This review uses official product documentation and one primary security-warning study. It is not a patent search, systematic literature review, or legal freedom-to-operate opinion. The novelty statement below means novel **as a workflow composition among the reviewed sources**, not globally first-ever.

## Problem framing

Agent approval usually asks a user to authorize capabilities, tools, commands, or diffs. Rehearsal keeps approval but increases the information carried by it: the user reviews an executed candidate state, visible consequences, supported invariants, and the exact artifact identity before the target workspace changes.

Warning research supports the narrower claim that interstitial design affects comprehension and behavior; it does not establish a numeric prevalence for “agent approval fatigue.” Avoid unsupported frequency claims.

## Prior-art matrix

| System | Preview / isolation | Authorization / policy | Verification / rollback | Difference from Rehearsal |
|---|---|---|---|---|
| [Claude Code permissions](https://docs.anthropic.com/en/docs/claude-code/permissions) | Plan mode and sandbox interact with permission modes | `deny`, `ask`, `allow`; tool/command approval | Risk explanation, not an outcome receipt | Approval binds a capability or command class, not an exact preview ID and patch digest |
| [Claude Code checkpointing](https://docs.anthropic.com/en/docs/claude-code/checkpointing) | Snapshots before prompts; no required executed outcome preview | Separate from outcome contracts | Restores tracked edits/conversation | Checkpointing is recovery, not consequence-bound authorization |
| [OpenAI Codex approvals](https://developers.openai.com/codex/agent-approvals-security/) and [sandboxing](https://developers.openai.com/codex/sandboxing/) | OS sandbox and restricted execution modes | Escalation policy governs capability access | No reviewed domain-level postcondition receipt | Capability containment, not approval of one immutable state transition |
| [Cursor Agent Security](https://docs.cursor.com/en/account/agent-security) | Diff/review, terminal controls, checkpoints | Terminal approval by default | User reviews diff; checkpoints provide recovery | No reviewed binding between approval, semantic preview, and immutable patch identity |
| [Terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan) / [apply](https://developer.hashicorp.com/terraform/cli/commands/apply) | Saved execution plan previews intended changes | Applying a saved plan authorizes an exact artifact | State refresh and provider results | Closest protocol analogy, but for declarative IaC; no natural-language correction into a monotonic coding outcome contract |
| [Kubernetes dry-run](https://kubernetes.io/docs/reference/using-api/api-concepts/#dry-run) / [kubectl diff](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_diff/) | Server evaluates intended objects without persistence | Admission and RBAC remain active | Shows would-be object; rollback is separate | Strong state preview, not a human approval protocol bound to an agent-generated patch digest |
| [AWS EC2 DryRun](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_RunInstances.html) | Permission preflight only | IAM authorization | `DryRunOperation` / `UnauthorizedOperation` | No consequence preview or rollback |
| [Open Policy Agent](https://www.openpolicyagent.org/docs/latest/) | Evaluates structured input | General policy-as-code | Structured decision is integrator-owned | Supplies invariant machinery, not executed preview, correction compilation, or artifact-bound approval |
| [Git worktree](https://git-scm.com/docs/git-worktree), [diff](https://git-scm.com/docs/git-diff), [revert](https://git-scm.com/docs/git-revert) | Detached worktree and diff are conventional primitives | No human authorization protocol | Git records and reverses tracked changes | Rehearsal's differentiation must be the protocol, binding, contract, and receipt—not Git itself |
| [E2B](https://e2b.dev/docs) | Isolated VM execution and snapshots | Platform access control | Command output / telemetry | Sandbox substrate, not consequence-bound authorization |
| [Daytona](https://www.daytona.io/docs) | Isolated workspace and snapshots | Platform access control | Logs / stateful snapshots | Infrastructure substrate, not semantic outcome approval |
| [Sunshine et al., USENIX Security 2009](https://www.usenix.org/legacy/events/sec09/tech/full_papers/sunshine.pdf) | N/A | Browser-warning experiment | Warning design changed comprehension and behavior | Supports careful consequence presentation; does not prove agent-specific prevalence |

## Defensible novelty claim

> Rehearsal changes agent authorization from capability approval to consequence-bound authorization. It first materializes a candidate filesystem/Git change in an isolated worktree, presents concrete consequences and a supported Outcome Contract, and accepts approval only for the matching preview ID, patch digest, base state, and contract version. Drift or correction invalidates the prior approval. After apply, Rehearsal records observed postconditions in a verification receipt and supports verified rollback within its declared local scope.

Reviewed products provide important pieces—tool permission, sandboxing, planned transitions, declarative invariants, diff, snapshots, or rollback. This review did not find the complete sequence:

```text
natural-language correction
→ monotonic supported contract
→ executed filesystem/Git preview
→ exact preview + digest-bound approval
→ apply with drift rejection
→ observed verification receipt
→ material rollback
```

A useful positioning shorthand is: **Terraform plan/apply semantics for coding-agent changes, with OPA-like outcome invariants and Git-native receipts/rollback.** Rehearsal is not positioned as a sandbox competitor; E2B or Daytona could be future substrates.

## Claims narrowed by evidence

| Avoid | Use instead |
|---|---|
| “First system to preview agent actions” | “Previews filesystem/Git consequences by executing a candidate patch in an isolated worktree.” |
| “First safe AI coding agent” | “A consequence-bound authorization layer for coding agents.” |
| “Approval cannot be bypassed” | “Approval validity requires matching preview ID, patch digest, base state, and contract version.” |
| “Guarantees exact production outcome” | “Detects supported repo drift and verifies declared local postconditions; external side effects remain outside scope.” |
| “Natural-language policy engine” | “Compiles supported correction vocabulary into typed, monotonic predicates.” |
| “Cryptographically secure approval” | “Digest-bound approval.” No signature or non-repudiation is claimed. |
| “Sandbox” | “Isolated Git worktree.” A worktree is not an OS security boundary. |
| “Receipt proves correctness” | “Receipt records artifact identity and observed verification results.” |
| “Full rollback” | “Verified rollback for changes captured by the receipt within declared filesystem/Git scope.” |
| “Transactional recovery” | “Verified process-local apply/rollback recovery.” Crash-durable recovery is not claimed. |

## Judge framing

| Dimension | Demonstrable claim | Evidence to foreground |
|---|---|---|
| Technological implementation | Exact-state authorization over a real Git patch | Worktree, canonical patch digest, base-state revalidation, stale/replay rejection, 49+ tests |
| Design | User edits the desired outcome, not a command allow-list | Unsafe consequences, plain-language correction, visible contract strengthening, safe replacement preview |
| Impact | Raises information quality per approval for action-taking agents | One harmful deletion caught before target mutation; verified rollback after apply |
| Quality / novelty | The unit of authorization is an immutable state transition | Old approval rejected after correction/drift; receipt links preview, artifact, checks, and rollback |

## High-signal demo order

1. Materialize a risky patch only in the candidate worktree.
2. Show concrete deletion/reference/test consequences before target mutation.
3. Correct the outcome in plain language.
4. Show the strengthened contract and changed preview identity.
5. Reject stale approval; approve the new exact artifact.
6. Apply and re-evaluate observed checks.
7. Show the receipt and verified rollback.
