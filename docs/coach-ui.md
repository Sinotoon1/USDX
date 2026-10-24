# Native Studio UI

## User-facing behavior

Studio is a native Pascal/SDL/OpenGL UI, not a web wrapper or a screenshot. Fresh
configurations use Chinese, Studio + Studio skin, and the list song catalogue.
Saved language/theme/catalogue and audio settings keep precedence. Deluxe and
Modern remain selectable and retain their legacy renderer/input behavior.

All Studio surfaces are light, including practice and play: cool gray
canvas, white panels, dark text and teal focus/action accents. Song
covers, avatars and optional song video remain real content, not theme chrome.
The home screen has two mode entries and direct library, statistics, editor and
settings actions. Player initialization is retained before entering songs.

List interaction is explicit: hover does not change selection; click selects;
double-click the selected row within 350ms or press Enter to start. Blank space,
release on a different target, drag-out, focus loss, resize and navigation cancel
a captured press. Keyboard/wheel controls, J search and M song menu remain.
Settings keep their original data bindings and scrolling behavior.

Practice shows phrase, pitch status, measurements, reference/delay readiness and
six mouse/keyboard actions. Play shows a dedicated light header with real song
metadata, keeps the classic full-song score and results, and uses flat score and
note rendering. Reference-note geometry, rap corners, golden-note cues and hit
state are preserved. Lyrics use dark readable ink while preserving player hue.

## Design ownership

- `tools/studio-design.json`: semantic colors, 8-unit spacing, radius, motion,
  typography, principal layout and bilingual UI copy.
- `tools/build_studio_theme.py`: reproducibly materializes Studio from the
  existing Modern functional geometry, then applies the Studio layout rules.
  Run `python tools/build_studio_theme.py`; CI checks with `--check`.
- `game/themes/Studio.ini`: generated native theme, not hand-maintained.
- `game/themes/Deluxe/Studio.ini`: Studio skin registration that reuses actual
  bundled cover/avatar/note/icon assets without copying binary resources.
- `UStudioUI`: shared vector rounded rectangles, buttons, selectors and shell.
  `UMenu*` integrates state while preserving the legacy branch.
- `UIMotion`: dependency-free elapsed-time interpolation and pointer capture.

USDX theme fallback is by **section**, not key. Materializing inherited sections
keeps required dimensions and button text counts. Color names are case-sensitive.
Flat controls clear inherited FadeTex, keep selected dimensions equal to hit
geometry, and explicitly transfer Z to dynamically regenerated labels. UI Z must
not exceed 1; the practice panel remains at 0.99.

## Motion and interaction

- Hover: 160ms; press/release feedback: 90ms; page crossfade/12-unit shift: 180ms.
- Smoothstep uses elapsed SDL ticks, not frame count; reversal starts from the
  current interpolated value. A long frame finishes rather than prolonging it.
- `Advanced / ScreenFade=Off` also disables all new microanimations immediately.
- Studio activates buttons on release over the same target, not on press.
- A transition cancels capture and rejects input to an unshown next page.
- Focus includes an outline/inset and pitch states include translated words;
  color alone does not carry the state.

## MiHome-Windows direction

The user's reference is pinned to
[MiHome-Windows b3b3b3f](https://github.com/huanyuejue/MiHome-Windows/tree/b3b3b3f5605a0494884c5e4c4d82bd6a10b54cdb/app/ui).
The light palette, compact header, white 14-unit rounded cards, circular teal
actions and short transitions inform this native implementation. No Qt runtime
or reference service layer is added to USDX. See `SPEC-ui-mihome.md`.

The two modes are equal-width cards; the tool area uses two columns, not a
sidebar or decorative tabs. Each mode has one interactive target: `Action=1`
paints a circular forward affordance through the existing button renderer.
The field defaults to false and is gated by Studio. Selection/hit geometry is
unchanged. `StudioAction` is the bright teal fill; `StudioAccent` is deliberately
darker for readable small text and focus outlines. `StudioOnAction` is dark ink.

The generator now updates the owned Studio copy keys in the Chinese/English
`[Text]` sections as well as the native theme. Other translations, comments and
sections remain intact. `--check` also catches stale live translations.

## Window and localization

Fresh configurations are windowed at up to 1280×960 in the native 4:3 layout.
The default scales to the SDL usable desktop minus 64 pixels of window margin;
unknown metrics use 800×600. Saved resolution/fullscreen values take precedence.
No layout coordinates depend on physical mouse pixels.

Chinese covers every English operational text key; format arguments and bundled
Noto regular/fallback font coverage are tested, including new Studio labels.
Studio also wraps unspaced Chinese text at UTF-8 codepoint boundaries; long
paragraphs do not overflow the content panel. The prior AnyASCII `boffset: LongInt` fix remains: Chinese title indexing must not
overflow FPC's default 16-bit Integer in that vendored unit. Upstream long-form
help without a Chinese page retains the original English fallback.

## Audio invariants

This UI change does not alter Python separation/reference models, capture,
confidence gating, target matching, scoring rules or persistent-score isolation.
F8 confirms a **previously measured** MicDelay for this session; it does not
measure latency. An AUTO/unreviewed reference still suppresses precise direction
and persistent high scores. Test fixtures and screenshots do not establish
physical microphone or end-to-end latency accuracy.

## Verification and maintenance

```text
python tools/build_studio_theme.py --check
python -m unittest discover -s test/coach -p 'test_*.py' -v
fpc -Cr -Co -Ct -Fusrc/base -FU<test-output> -FE<test-output> test/coach/coach_motion_test.pas
```

Native tests also include coach_core, coach_window and coach_unicode (compile the
vendored unicode unit without globally forcing Delphi mode). The Windows
portable workflow runs all four and builds the complete game/resource package.

Native acceptance uses an isolated SDL/Xvfb display and a zero-sample virtual
input, never the user's config or real microphone. Check home/profile/library,
search/menu, practice pause/actions, play-to-results, settings and scrolling,
empty library, reduced motion and legacy Deluxe. Check 800×600 and 1280×960,
press/drag-out/release, rapid navigation and animation frame progression.

Reusable change prompt:

> Update tools/studio-design.json and native Studio rendering only. Regenerate
> the theme, retain legacy themes, keep hit geometry independent of animation,
> preserve audio/scoring invariants, run all coach tests and native flow QA,
> and record source hashes plus a copy-tested rollback before delivery.
