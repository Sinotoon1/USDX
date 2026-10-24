# Native coach UI

## Scope and behavior

The 2026-10-24 UI increment keeps USDX's native renderer, song catalogue, input
pipeline and scoring policy. It adds no web wrapper or image-based screen.
Fresh configurations use Chinese and the Deluxe theme. A saved language/theme
choice is not overwritten; English and Modern remain available.

The home screen gives practice and play equal, fixed 352×220 mode cards. Practice
is initially focused. Secondary music library, statistics, editor and settings
actions remain direct native buttons. Profile initialization before song entry
is retained: skipping it leaves upstream singing-screen state uninitialized.

## Theme ownership

- `game/themes/Deluxe.ini`: fixed mode cards, secondary navigation, common dark
  menu backgrounds. Positions use USDX's existing 800×600 logical coordinate
  system and scale through its renderer, not physical window pixel coordinates.
- `game/themes/Modern.ini`: shared `Coach*` text, panel and control primitives,
  available to both bundled themes through the existing inheritance mechanism.
- Semantic colors: `CoachSurface`, `CoachSelected`, `CoachText`, `CoachMuted`,
  `CoachAccent`, `CoachFlat`, `CoachSharp`, `CoachClose`. Pitch states also have
  explicit translated text; color is never the sole signal.
- HUD depth must be **1**, not greater than 1. The renderer clips larger values.
  The panel uses 0.99. `AddButtonText` does not copy theme Z, so the controller
  explicitly transfers it to keep labels above notes.

The practice HUD reserves the top 252 logical units. Status, measurements,
readiness and controls occupy separate rows, above the existing note lane.
Six native buttons dispatch through the same `CoachAction` method as shortcuts.
The cursor remains available in practice, including after fullscreen changes.
The existing F8 gate remains session-only and does not perform a measurement.
Practice pause does not dim or cover the controls. Play pause uses translated
native text instead of the English bitmap.

## Localization and Chinese song names

Chinese now covers every English `[Text]` key (including 417 previously missing
translations). Format-argument indices and types are regression tested. Upstream
context-help pages without Chinese text still use their original English help
fallback; the native operational labels are translated.

The bundled Noto regular/fallback fonts cover the core Chinese coach labels; a
stdlib-only cmap test verifies coverage. No new font binaries were added.

Chinese title loading exposed an upstream AnyASCII defect: in its default FPC
mode, `Integer` is 16-bit, but the transliteration bank contains offsets above
32767. Only `boffset` is widened to `LongInt`; range checks stay enabled and
the tables, algorithm and musical pitch processing are unchanged. A native
regression checks `中文验收 -> ZhongWenYanShou` and preserves ASCII indexing.

## Verification

Run the Python contracts with `python -m unittest discover -s test/coach -p
'test_*.py' -v`. Native tests are `coach_core_test.pas` and
`coach_unicode_test.pas`; the latter must be compiled with range checks and
without globally forcing Delphi mode on the vendored unit. The Windows portable
workflow builds and runs both.

Manual native acceptance: fresh Chinese home, both mode entries, Chinese song
names, click next phrase, repeat, loop on/off, pause/resume, measured-delay
confirmation/revocation, return to songs, and play-to-results. Check the empty
library dialog and a deliberately unreviewed reference. Test at 800×600 as the
smallest supported logical canvas. Live hardware pitch/latency acceptance is a
separate audio task; screenshots and a synthetic fixture do not establish it.
