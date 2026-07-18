# Architecture

Rehearsal has three small stdlib-only layers.

```text
Browser UI → HTTP controller → Outcome Contract / Engine → isolated Git worktree
                                 │                         ↘ measured diff/tests
                                 └ GPT-5.6 semantic edge     proof + hashes

Approve → stale check → exact binary patch → independent measurement → receipt
Rollback ← verified reverse patch ← receipt-bound current-state check
```

`rehearsal.engine` owns trusted mechanics. Each rehearsal starts a detached
worktree at the demo repository's `HEAD`, runs a fixed cleanup behavior, and
derives status, binary patch, disk delta, Markdown reference breaks, test
result, contract evidence, and SHA-256 file hashes from disk and Git.

`rehearsal.contracts` owns the probabilistic semantic boundary. GPT-5.6 emits a
strict JSON Outcome Contract and explains already-measured facts. A deterministic
fallback makes the public demo reproducible without credentials and is labeled
in both API and UI.

`rehearsal.app` coordinates states; `rehearsal.server` exposes a loopback HTTP
API and static UI. The approved preview is process-local and cannot be replayed
after restart.

All mutable controller operations share one reentrant lock, including the
entire stale check, apply, verification, and receipt update. A preview replaced
by another browser is stale; approval carries both preview ID and patch digest.

Approval is a capability for one exact state. It requires a green test result
and proof, an unchanged base snapshot, identical post-apply file hashes, an
identical staged binary-patch digest, and independently green tests/proof.
The base binding also includes HEAD and a digest of index modes/object IDs.
Approval capabilities expire after five minutes, become obsolete when another
preview is generated, and are consumed before apply so they cannot be replayed.

Reset is confined to one canonical direct `demo-*` child of a dedicated runtime
root outside the source tree, home, and filesystem root. The default runtime
root is under the operating system temporary directory.

Receipts link preview, apply, verification, and rollback with one transaction
ID. They expose the full patch/contract/base/observed digests, contract revision,
UTC timestamps, branch/workspace, model modes, check totals, and rollback proof.
The UI can copy the full patch digest or export the complete receipt JSON.

The frontend exposes named progress after 500 ms and uses persistent structured
errors. These are presentation-level operation stages over the synchronous,
serialized controller; they do not claim a durable background workflow.
