# Rehearsal — English Demo Script (target: 110–130 seconds)

## 0:00–0:12 — Problem

AI agents ask us to approve commands and tool calls. But people do not understand commands. They understand consequences. Rehearsal lets you see and correct the future before an agent changes reality.

## 0:12–0:28 — First rehearsal

Here I ask the agent to remove unused project files. Rehearsal runs the task in an isolated Git worktree. This is not a generated warning: the measured candidate deletes three real files, breaks a documented public example, and makes the tests fail.

## 0:28–0:46 — Correct the future

Instead of rejecting the whole task or editing technical commands, I correct the outcome in plain English: keep the public API example and make sure tests pass. GPT-5.6 compiles that correction into an Outcome Contract.

## 0:46–1:02 — Safe future

Rehearsal simulates again. The junk files are still removed, but the public example has an identical SHA-256 hash. Tests pass, references are clean, and every contract clause has deterministic evidence.

## 1:02–1:20 — Outcome-bound approval

Approval is bound to this exact preview ID, patch digest, Git HEAD, index, and file-state snapshot. Rehearsal applies the exact binary patch, re-runs proof, and issues a verified execution receipt. If anything changed after preview, approval would fail closed.

## 1:20–1:33 — Rollback

One click applies the verified reverse patch and proves the original state is restored. Rehearsal never asks you to trust a plan. It asks you to approve a future it can prove.

## 1:33–1:42 — Close

Rehearsal is open source and built with Codex and GPT-5.6. Approve outcomes, not actions.

## Capture checklist

1. Start at clean ready state.
2. Show task text and click Run rehearsal.
3. Pause on red BLOCKED state; zoom deleted public example and failing test.
4. Show correction text and click Re-rehearse.
5. Pause on green contract proof.
6. Click Approve exact state; highlight receipt digest and matched hashes.
7. Click One-click rollback; highlight ROLLED BACK.
8. End on product name and tagline.

## Audio

English narration required. Speak naturally, 125–140 words per minute. Keep final video below 3:00; target 1:42 plus short transitions.
