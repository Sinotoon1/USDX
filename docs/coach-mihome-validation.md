# MiHome-inspired Studio acceptance — 2026-10-24

Runtime commit: `7356493c6809f3f3320e261031f9c28849cb08d1` on
`feature/practice-play-python`; increment baseline `5f773b0`.
Reference: MiHome-Windows `b3b3b3f5605a0494884c5e4c4d82bd6a10b54cdb`.
Later acceptance documentation does not change runtime inputs.

## Automated gates
- Baseline source copy: 30 tests, 1577 original raw SHA256 values.
- Modified: 36 Python tests pass, including palette/layout, explicit Action
  plumbing, live bilingual copy, section-preserving generation and contrast.
- Four Pascal tests pass: core, window, motion and Unicode, with their existing
  range/overflow/stack gates. Linux native game compiles (42 warnings, 70 notes).
- Ruff E/F/I on the changed generator/new test and actual `git diff --check` pass.
- [Windows build and all tests](https://github.com/Sinotoon1/USDX/actions/runs/40079232506)
  pass; portable artifact is `USDX-Coach-windows-portable`.
- Downloaded Win64 portable starts locally with a fresh isolated config, reaches
  Main Loop, stays alive and saves Studio/Studio/List, windowed 1280×960. The
  smoke test stops only its own child process. The PE x86_64 header is verified.
- New package: `USDX-Coach-windows-mihome-7356493/game/ultrastardx.exe` under the
  workspace parent. SHA256:
  `b72d9d8da041a4a5f7a86dd8ae4bb0bcb75ba62b5a1ab0231f6c4efb40bfbcf7`.
  It retains the previous Studio package's config bytes and copies the score
  database via SQLite backup; the prior package is unchanged.
- Copy-only rollback restores the warm Studio baseline, all 1577 hashes and
  30 tests; unrelated user-data remains. Later edits reject before restore writes.

## Native rendering and input
The real Pascal/SDL executable runs on a private Xvfb display, with an isolated
HOME/config/database and zero-sample virtual audio. No physical microphone or
measured capture-delay claim follows from these UI fixtures.

| Scenario | Observed artifact in the evidence folder |
|---|---|
| Home in Chinese, 800×600 / 1280×960 | home-clean.png / home-1280.png |
| Press mode arrow, release outside: stays home | home-pressed.png / release-outside.png |
| Click circular arrow: same parent route to player setup | profile-ready.png / profile-play.png |
| Select second song without starting | library-selected-second.png |
| Practice controls and pause in both sizes | practice-paused.png / practice-paused-1280.png |
| Full play, pause/resume, completed results and highscores | play-paused.png / results-final-1280.png / highscores.png |
| Settings and focused MicDelay after scrolling | settings-correct.png / game-large-scroll.png |
| Search and song menu | search.png / song-menu.png |
| Empty-library modal retains input isolation | empty-popup.png / empty-background.png / empty-dismissed.png |
| Legacy theme remains legacy | legacy-home.png |
| English live copy fits the home cards | english-home.png |
| Real hover/page frames and reduced motion | verified-hover-* / verified-transition-* / off-hover-* / off-settings.png |

Native hover pixel at (700,480), outside the pointer: white → (251,251,252) →
(244,245,247) at the sampled 0/70/220ms frames. With ScreenFade=Off the latter
two frames are already (244,245,247). The page uses 180ms crossfade; frame capture
and software-renderer scheduling are evidence samples, not timing guarantees.

QA route correction: a surplus Escape from the highscores/home path opened the
exit modal; later inputs in that attempt were not counted as settings evidence.
The accepted settings run starts freshly at home. For keyboard scroll checks,
keep the pointer outside controls and begin from the known initial selector;
otherwise the initial hovered row changes how many Down presses reach MicDelay.
These are fixture routing corrections, not a runtime code change.

## Review
Correctness: field defaults false, Studio gates it, and the affordance is paint
on an existing button rather than a second focus/click target. Native content
and data bindings survive generated section materialization.

Readability/architecture: the semantic JSON remains the palette/layout/copy
source. Bright action fill and accessible small-text ink are separate tokens.
The generator owns only Studio translation keys in `[Text]`, with a regression
covering an unrelated section that has a similarly named key.

Data integrity: no model, audio queue, score rule, network service or credentials
are added. Rollback preflights hashes; the portable build is installed separately
and the prior package stays intact. Painting adds only bounded vector geometry,
not background jobs or model inference.

Runbook: [coach-ui.md](coach-ui.md). Specification: [SPEC-ui-mihome.md](../SPEC-ui-mihome.md).
