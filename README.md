# Rehearsal

**See what your agent will do. Correct the future. Then commit it.**

Rehearsal is an open-source outcome-approval layer for coding agents. It makes
a candidate change inside an isolated Git worktree, measures its consequences,
lets a person correct the desired outcome in natural language, and applies only
the exact approved state. Reality is re-measured after apply and can be rolled
back to the original checkpoint.

This Build Week vertical slice is deliberately narrow: a polished, local demo
for Git/filesystem cleanup tasks over the bundled trusted seed. It never
executes user-supplied commands or tests from an arbitrary repository.

## Run locally

Requirements: Git 2.20+ and Python 3.11+. There are no third-party packages.

```sh
./scripts/setup.sh
./scripts/start.sh
```

Open <http://127.0.0.1:8765>. For the live model path, export
`OPENAI_API_KEY` before starting. Without it, the UI prominently reports
**deterministic demo fallback**; all filesystem consequences, tests, hashes,
diffs, and proofs remain real in both modes.

## 42-second demo

1. Click **Run rehearsal** for “remove unused project files.”
2. The red future state genuinely deletes the documented public example. Its
   test fails and README reference scan reports the break.
3. Submit “Keep the public API example and make sure tests pass.” GPT-5.6
   compiles that correction into contract clauses (or the labeled fallback does
   so when no key is configured).
4. The second isolated rehearsal is green: junk is deleted, the example is
   preserved, tests and clauses pass.
5. Approve the exact state. Rehearsal applies the approved binary Git patch,
   matches the patch digest and every file hash, re-runs tests and proof, and
   emits an inspectable, downloadable receipt. Approvals expire after five
   minutes and are single-use.
6. Click **One-click rollback** to restore and verify the original tree.

The same path is available without a browser:

```sh
python3 scripts/demo.py
```

## Test and clean verification

```sh
python3 -m unittest discover -v
./scripts/verify-clean.sh
```

`verify-clean.sh` runs the full test suite and the full reset → unsafe rehearsal
→ correction → safe rehearsal → approve/verify → rollback path in a temporary
directory.

Expected proof shape:

```text
Ran 51 tests
OK
ready → unsafe → safe → applied → rolled_back
verified: true
rollback: completed and verified
```

## Runtime model integration

With `OPENAI_API_KEY`, Rehearsal calls the OpenAI Responses API using `gpt-5.6`
for two meaningful semantic jobs:

- strict-schema compilation of a natural-language correction into the Outcome
  Contract;
- concise explanation of deterministic, measured consequence data.

The model never supplies file lists, test outcomes, hashes, proof status, or
approval decisions. API errors fail closed; they do not silently switch modes.
No data is sent unless API-key mode is enabled. In that mode, contract
compilation sends the user's correction and current contract, including any
repository-relative paths in its clauses. Consequence explanation sends only
file/reference/violation counts, disk delta bytes, test/contract booleans, and a
generic deterministic summary—never file names, test output, contents, hashes,
or patches.

The server binds only to loopback. Requests require a loopback Host and POSTs
require a matching HTTP Origin plus a random per-process mutation nonce.
Approval binds the displayed preview ID and patch digest. This is single-user
local-demo protection, not authentication.

## Demo video

[Watch the 42-second enterprise live-product demo on YouTube](https://youtu.be/-yZ-59OqS2w).

## Built with Codex and GPT-5.6

Codex CLI with official ChatGPT authentication and GPT-5.6 served as the sole
implementation owner for product code. One canonical thread performed strict
TDD, implemented the engine and UI, fixed browser regressions, and closed the
independent security review. Dyra directed product scope, research, media, and
independent acceptance without becoming a second code owner. Rehearsal's optional live runtime
also uses GPT-5.6 for bounded contract compilation and consequence explanation;
deterministic measurement remains authoritative.

Canonical Codex `/feedback` Session ID:
`019f7351-793e-7093-bc96-72e49183379b`.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Safety boundaries](docs/SAFETY.md)
- [Prior-art challenge and product rationale](docs/PRODUCT_RATIONALE.md)
- [Competitive landscape and defensible novelty](docs/research/competitive-landscape.md)
- [Huashu render provenance and governance](docs/HUASHU_PROVENANCE.md)
- [TDD evidence](docs/TDD.md)

## License

MIT. See [LICENSE](LICENSE).
