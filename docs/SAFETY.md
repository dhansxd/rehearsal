# Safety boundaries

## Enforced

- Reset can delete only one canonical direct `demo-*` child of an approved
  runtime root. Root, home, source-tree, nested, outside, and symlink paths are
  rejected.
- User input is plain-language data, never a shell command. Only fixed Git argv
  operations and `python3 -m unittest discover -s tests` execute.
- Test execution is refused unless the engine is explicitly constructed for
  the bundled trusted seed.
- Protected paths reject absolute paths, backslashes, NUL, empty/dot/traversal
  components, `.git`, resolution escape, and symlinks. Preservation requires an
  identical base SHA-256 hash.
- GPT contracts require the exact schema, bounded strings/lists, supported
  proof vocabulary, and monotonic union with every prior constraint.
- Preview approval binds file hashes, HEAD, index metadata, patch digest,
  preview ID, passing tests, and contract proof. It expires after five minutes,
  is invalidated by replacement, and is single-use.
- One controller lock serializes reset, rehearsal, correction, approval through
  verification, rollback, and state reads.
- Failed or interrupted apply/rollback recovers a checkpoint and reports it
  restored only after independent hash/index/digest verification. Otherwise the
  error says state is uncertain.
- The server refuses non-loopback binds. Requests require a loopback Host; POST
  additionally requires a matching HTTP Origin and random per-process mutation
  nonce. Body length is a single decimal `0..16384`, reads time out after five
  seconds, and responses carry CSP, nosniff, and frame-denial headers. Static
  assets use `no-store`.

## Model data disclosure

With API-key mode enabled, contract compilation sends the user's correction and
current contract, including repository-relative clause paths. Explanation sends
only file/reference/violation counts, disk delta bytes, test/contract booleans,
and a path-free generic summary. It does not send file names, contents, test
output, hashes, or patches. Deterministic fallback sends nothing externally.

## Honest limitations

- This slice handles one deterministic cleanup scenario and bundled trusted
  seed, not arbitrary repositories, coding tasks, or agent runners.
- Supporting untrusted repositories is intentionally scoped out; it requires a
  container or VM without network, secrets, or host writes. A Git worktree is
  isolation from the source checkout, not an execution sandbox.
- Markdown scanning is narrow, not a compiler-wide dependency graph.
- There are no accounts, sessions, or authentication. Loopback Host/Origin
  controls are suitable only for this single-user local demo.
- State and rollback capability do not survive process restart. Locking is
  process-local, not cross-process.
- A crash-durable journal and process lease are deliberately deferred. No
  partial journal or durability claim is shipped.
- Semantic model interpretation can still miss the user's intended meaning;
  deterministic enforcement cannot prove an unstated constraint.
