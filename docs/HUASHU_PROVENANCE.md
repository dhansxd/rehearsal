# Huashu render provenance and governance

Date: 2026-07-18

This record covers the design/render tooling used around Rehearsal's public hybrid demo. Huashu is an isolated media-production dependency, not a runtime dependency of Rehearsal.

## Isolation and upstream pin

| Field | Verified value |
|---|---|
| Isolated checkout | `/Users/daniubaidillahhusaingmail.com/projects/huashu-design-pilot/upstream` |
| Rehearsal checkout | `/Users/daniubaidillahhusaingmail.com/Projects/rehearsal-agent` |
| Upstream remote | `https://github.com/alchaincyf/huashu-design.git` |
| Branch | `master`, tracking `origin/master` |
| Local + remote SHA | `6623ff01cfdcfc19f950bfa6fed91ca35ad619db` |
| Ahead / behind | `0 / 0` at audit time |
| Checkout state | clean, non-shallow |

Reproduction:

```bash
cd /Users/daniubaidillahhusaingmail.com/projects/huashu-design-pilot/upstream
git rev-parse --show-toplevel
git remote -v
git rev-parse HEAD
git status --short --branch
git rev-list --left-right --count HEAD...origin/master
git rev-parse --is-shallow-repository
git ls-remote --symref origin HEAD refs/heads/master
```

## License

Huashu is MIT licensed, copyright `2026 alchaincyf (花叔 · 花生)`.

```text
LICENSE SHA-256:
6d6a2a9caf2e6d2b76974050427053b2892d8aa4c33fd168ce63a537fcee9d96

LICENSE Git blob:
ed67368a2a79ed7be97b2a4852330cdac5b8b12a
```

The Rehearsal repository does not vendor Huashu source. If substantial Huashu source is distributed later, its MIT license text and copyright notice must accompany that distribution.

## Dependency manifest audit

Pinned upstream manifest hashes:

```text
package.json:
144b28fbf3911f2969589bbddb3208bb02e98bfb33988723d33d3a724ad3b7d5

package-lock.json:
0c334005bfe0da4ad5fa1ea805a1d99d3290f636add29faa861c841ddaac6a69
```

Root dependencies at audit time:

```text
pdf-lib ^1.17.1
playwright ^1.59.1
pptxgenjs ^4.0.1
sharp ^0.34.5
```

`package-lock.json` is lockfile v3 with 57 package entries. `sharp` and optional `fsevents` declare install surfaces. Therefore `npm install` / `npm ci` is not treated as inert: use the pinned lockfile inside the isolated workspace and review lifecycle scripts before reinstalling.

## Renderer fork used for native system Chrome

Local renderer:

```text
/Users/daniubaidillahhusaingmail.com/projects/huashu-design-pilot/work/render-video-seek-system-chrome.js
SHA-256 f022dfb9c1d34a22d6f37f91aed35cbe4f4f0d45c7f7e0d8a6ac8db0031eac78
```

Upstream renderer:

```text
scripts/render-video-seek.js
SHA-256 c6b68e89fc4f1709baf2b8a5e7910dfad5716aeb6bc40fb6aa4daaf92c7e9abb
Git blob 94b18369806ed5930ce0f5c814a1d434c91fc847
```

Exact functional delta:

```diff
- await page.goto(url, { waitUntil: 'load', timeout: 60000 });
+ await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });

- const browser = await chromium.launch();
+ const browser = await chromium.launch({
+   executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
+   headless: true
+ });
```

This fork is intentionally minimal: it selects installed system Chrome and avoids waiting for unrelated late network resources. It passed `node --check`. It remains production tooling outside the public runtime.

## Security surface

The renderer accepts trusted HTML only. It is not a sandbox.

- A `file://` page executes JavaScript and can request network resources.
- Output is overwritten with `ffmpeg -y`.
- `.seek-tmp-*` directories are created beside input and recursively removed after encoding.
- Input location determines the write/delete surface; keep inputs under the dedicated media workspace.
- Upstream demos may load Google Fonts, CDN React/Babel, Wikimedia images, Volcengine review, or ByteDance TTS.
- API/TTS scripts can read credentials from environment or `.env` and send content to third parties.
- Rehearsal's final render used trusted local HTML/assets and a separately aligned narration master. No Huashu service or code runs in the Rehearsal app.

Controls:

1. Pin upstream SHA and lockfile.
2. Keep checkout separate from Rehearsal runtime.
3. Treat HTML as trusted executable input.
4. Use local fonts/assets for deterministic final capture.
5. Review renderer diff and output path before execution.
6. Never expose `.env` or credential values in provenance.
7. Verify final output independently with frame count, decode, motion, audio, contact sheets, and native playback.

## Public hybrid artifact

```text
Public video: https://youtu.be/-yZ-59OqS2w
Local artifact: demo-assets/quality-media/live-tutorial/hybrid/rehearsal-hybrid-final-v3.mp4
SHA-256: c6a7cf1acd83fe1481456e296e2121cedf9183d7a64025739a7e3d54f92d181d
Size: 19,144,038 bytes
Duration: 42.000000 seconds
Video: H.264, yuv420p, 1920×1080, 60 fps, 2,520 frames
Audio: AAC, mono, 48 kHz
```

The binary and working media are intentionally outside tracked source to keep the repository small. Integrity is represented by this manifest and the public playback URL. The hybrid combines truthful live-product footage with a deterministic Huashu-derived HTML shell; it is not a direct export of an upstream example.

## Acceptance evidence

- Exact frame count and full decode passed.
- Black-frame scan found zero black frames.
- Temporal sample audit found 83 unique samples out of 84; only deliberate opener/closer holds remained.
- Verbatim narration subtitle cues were checked at all six voice windows and silence gaps.
- Subtitle lane was moved outside the product viewport after overlap defects were found at 12s, 25s, and 33s.
- QuickTime native playback reached `42.0 / 42.0` seconds and stopped normally.
- Product regression remained 49/49 with clean lifecycle verification at media lock.

These statements describe the audited local artifact and public URL. They do not imply bit-for-bit reproducibility across browser, font, OS, codec, or hardware versions.
