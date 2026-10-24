# Studio acceptance — 2026-10-24

Runtime source: `1a38a72176d8901c392d64c46cd00cb74ac3078b` on
`feature/practice-play-python`; baseline `14dcc69`. Subsequent acceptance-metadata
changes do not change `src/`, `game/` or `tools/` runtime inputs.

- 30 Python bridge/UI/generator tests pass. A CP1252 default-locale regression
  reproduces the Windows CI encoding failure and passes after explicit UTF-8
  reads. Keep encodings explicit; do not hide this with a CI-only environment flag.
- Four native Pascal tests pass on Linux and Windows: core, window, motion and
  unicode. Motion additionally covers range/overflow/stack checks, variable
  frame steps, stalled/reversed animation, SDL tick wrap and pointer cancellation.
- Full Linux native build succeeds (42 warnings / 70 notes). The copied build has
  no Git metadata, so its upstream whitespace helper warns; `git diff --check`
  runs successfully in the actual source checkout.
- [Windows CI, tests and Win64 build](https://github.com/Sinotoon1/USDX/actions/runs/40075845102)
  succeeds. The complete portable package starts locally using an isolated fresh
  config, writes Studio/Studio/List, Off/1280x960 and reaches Main Loop; the test
  process is then stopped. The old portable remains unmodified.
- A separately extracted source copy restores all 1562 original raw SHA256
  values and its original 18 tests, removes added Studio files and preserves an
  unrelated user-data sentinel. The modified working source remains changed.
  A later-edit fixture is rejected before any restore write.

## Real native render/input matrix

An isolated Xvfb display runs the SDL x11 native binary with a zero-sample virtual
capture input. Images and frame sequences are actual rendered pixels, not UI
mockups. This is UI acceptance, not physical microphone or end-to-end latency
acceptance.

| Surface / action | Observed result |
| --- | --- |
| Home and profile | All-light chrome, Chinese labels, correctly sized avatar, real Continue action |
| Rapid F6 / Return / Return | Stops at profile; no input into an unshown page |
| List blank / drag-out / single / double click | Blank/cancel stay in list; single selects second row; double enters practice |
| Search and song submenu | Readable text entry/value, real filtering, 44-unit menu targets |
| Practice pause / next / repeat / loop | Controls remain readable and usable; phrase and loop state update |
| Play / pause / results / high scores | Light header and pause; real score/result flow retained |
| Settings / graphics | Native selectors retain binding; scroll reaches MicDelay without clipping the focused row |
| Statistics / editor / about | Light surfaces, common heading rhythm; Chinese prose wraps inside its panel |
| Empty library | Centered Chinese explanation/action; background receives no activation |
| Reduced motion | Hover color is settled by the next sampled frame; no delayed microanimation |
| Legacy Deluxe | Old dark paint and native practice controls still run |
| 800x600 / 1280x960 | Main, profile, library and practice fit the logical 4:3 canvas |

Native hover pixel at (700,432) changes from white to (244,249,245) to
(224,239,229) at the 0/70/220ms captures; reduced-motion 70/220ms captures match.
Pure tests check exact timing independent of screenshot/driver overhead.
A native W=0/two-line fixture reproduces the vertical-glyph regression before
the bounded-width guard and renders two correct lines after it. The fixture
theme is restored byte-for-byte afterward; actual source is never edited by QA.

## Review

Correctness: theme fallback is materialized per section; required button text
counts and dimensions survive; coordinates and text depth remain native.
Readability/architecture: semantic tokens, one generator, shared vector paint and
pure motion state; legacy paths are explicitly retained. Generated INI is not a
second hand-maintained source of truth.
Security/data integrity: no new service, credential flow or audio-data upload;
rollback preflights hashes and preserves later edits; portable migration changes
only Theme/Skin/SongMenu and copies the score database with SQLite backup.
Performance: motion is elapsed-time based; fixed-size corner geometry is bounded;
model inference, audio locks and scoring work are not added to the render path.

Durable UI runbook: [coach-ui.md](coach-ui.md). Existing audio/MicDelay/reference
and score-isolation contracts remain unchanged.
