# Product rationale and prior-art challenge

Research date: 2026-07-18

## Challenge

Rehearsal's original ingredients are not individually novel. VS Code's Agents
window, Phasr, h5i, Kagan, Agentplane, and `ait-vcs` already use isolated Git
worktrees, reviewable diffs, approval gates, and merge/discard or recovery
flows. A product framed as "run an agent in a worktree and approve its diff"
would therefore be incremental and easy to confuse with an agent workspace.

The more universal unresolved problem is **authorization drift**: people approve
an agent, plan, command, or diff, while the thing they actually care about is a
bounded future state. A correction such as "keep the public API example" must
become an enforceable condition, not merely another prompt, and approval must
not remain valid after that state changes.

## Product decision

Keep the vertical slice, but sharpen the product around a **counterfactual
Outcome Contract**:

1. Execute a real candidate change in an isolated worktree.
2. Measure filesystem, Git, references, tests, and contract evidence from that
   candidate; never ask the model to invent these facts.
3. Compile human corrections into explicit clauses and re-run from the original
   state.
4. Bind approval to the candidate's exact base commit, patch digest, file
   hashes, test result, and contract proof.
5. Apply that exact patch, independently re-measure reality, emit a receipt,
   and offer rollback to the checkpoint.

The model is useful at the semantic boundary—turning natural language into a
contract and explaining measured consequences. Deterministic code owns state,
policy, verification, and rollback. This separation is the original, demoable
claim: **correct the future, then authorize only that future**.

## Evidence reviewed

- [VS Code Agents window](https://code.visualstudio.com/docs/agents/agents-window): worktree-isolated sessions, file diffs, comments, merge/discard.
- [VS Code approvals](https://code.visualstudio.com/docs/agents/approvals): command/tool approval and sandbox controls.
- [h5i](https://h5i.dev/): sandboxed worktrees and auditable agent provenance.
- [Phasr](https://phasr.sh/): parallel worktrees, diff review, and controlled merges.
- [Kagan](https://docs.kagan.sh/): supervised worktree tasks with lifecycle gates.
- [Agentplane](https://agentplane.org/docs/user/workflow/): plan/approve/implement/verify workflow.
- [ait-vcs](https://pypi.org/project/ait-vcs/): Git-native isolation, provenance, apply, and recovery.

This is a targeted landscape check, not a patentability or freedom-to-operate
opinion.
