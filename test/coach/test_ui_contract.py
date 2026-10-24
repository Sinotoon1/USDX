"""Native theme/localization contracts; real rendered flows are checked separately."""

import configparser
import os
import re
import struct
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(os.environ.get("USDX_ROOT", Path(__file__).resolve().parents[2]))


def ini(path):
    # Match TMemIniFile: upstream help and Modern theme contain duplicate sections.
    result = configparser.RawConfigParser(strict=False)
    result.read(ROOT / path, encoding="utf-8-sig")
    return result


def theme(section):
    sources = [ini("game/themes/Deluxe.ini"), ini("game/themes/Modern.ini")]
    result = {}
    for _ in range(10):
        source = next((s[section] for s in sources if section in s), {})
        for key, value in source.items():
            result.setdefault(key, value)
        section = source.get("inherits")
        if not section:
            return result
    raise AssertionError("theme inheritance cycle")


def font_has(path, codepoint):
    """Read Unicode cmap coverage directly, without an optional font dependency."""
    data = path.read_bytes()
    tables = struct.unpack_from(">H", data, 4)[0]
    for i in range(tables):
        tag, _, offset, _ = struct.unpack_from(">4sIII", data, 12 + i * 16)
        if tag == b"cmap":
            break
    else:
        return False
    count = struct.unpack_from(">H", data, offset + 2)[0]
    for i in range(count):
        platform, encoding, sub = struct.unpack_from(">HHI", data, offset + 4 + i * 8)
        if platform != 0 and (platform, encoding) not in ((3, 1), (3, 10)):
            continue
        start = offset + sub
        fmt = struct.unpack_from(">H", data, start)[0]
        if fmt == 12:
            groups = struct.unpack_from(">I", data, start + 12)[0]
            for j in range(groups):
                first, last, glyph = struct.unpack_from(
                    ">III", data, start + 16 + j * 12
                )
                if first <= codepoint <= last and glyph + codepoint - first != 0:
                    return True
        elif fmt == 4 and codepoint < 65536:
            segments = struct.unpack_from(">H", data, start + 6)[0] // 2
            ends = start + 14
            starts = ends + segments * 2 + 2
            deltas = starts + segments * 2
            ranges = deltas + segments * 2
            for j in range(segments):
                first = struct.unpack_from(">H", data, starts + j * 2)[0]
                last = struct.unpack_from(">H", data, ends + j * 2)[0]
                if first <= codepoint <= last:
                    delta = struct.unpack_from(">h", data, deltas + j * 2)[0]
                    distance = struct.unpack_from(">H", data, ranges + j * 2)[0]
                    if not distance:
                        return (codepoint + delta) % 65536 != 0
                    glyph = struct.unpack_from(
                        ">H", data, ranges + j * 2 + distance + 2 * (codepoint - first)
                    )[0]
                    if glyph:
                        return (glyph + delta) % 65536 != 0
    return False


class NativeUIContractTests(unittest.TestCase):
    def test_fresh_install_defaults_to_chinese_without_forcing_saved_language(self):
        source = (ROOT / "src/base/UIni.pas").read_text(encoding="utf-8-sig")
        self.assertTrue(
            "'Game', 'Language', IGNORE_INDEX, 'Chinese'" in source,
            "fresh install must use Chinese",
        )
        self.assertTrue(
            "DEFAULT_THEME = 'Deluxe'" in source,
            "fresh install must use the coach layout",
        )
        self.assertIn("GetArrayIndex(ILanguage, 'English')", source)
        self.assertIn(
            "IniFile.WriteString('Game', 'Language', ILanguage[Language])", source
        )

    def test_chinese_covers_every_english_ui_key(self):
        english = ini("game/languages/English.ini")["Text"]
        chinese = ini("game/languages/Chinese.ini")["Text"]
        self.assertEqual([], sorted(set(english) - set(chinese)))
        self.assertTrue(all(chinese[k].strip() for k in english))

    def test_translations_preserve_pascal_format_arguments(self):
        english = ini("game/languages/English.ini")["Text"]
        chinese = ini("game/languages/Chinese.ini")["Text"]
        tokens = re.compile(r"%(?:\d+:)?[-+0-9.]*[dsfuxegpnm]")
        for key in english.keys() & chinese.keys():
            with self.subTest(key=key):
                self.assertEqual(
                    Counter(tokens.findall(english[key])),
                    Counter(tokens.findall(chinese[key])),
                )

    def test_two_primary_entries_have_equal_fixed_geometry(self):
        boxes = []
        for name in ("MainButtonSolo", "MainButtonMulti"):
            props = theme(name)
            x, y, w, h = (int(props[k]) for k in ("x", "y", "w", "h"))
            self.assertEqual((w, h), (352, 220))
            self.assertEqual("0", props.get("fade", "0"))
            self.assertEqual("0", props.get("parent", "0"))
            self.assertLessEqual(x + w, 800)
            self.assertLessEqual(y + h, 600)
            boxes.append((x, y, w, h))
        self.assertGreaterEqual(abs(boxes[0][0] - boxes[1][0]), 368)

    def test_settings_and_secondary_entries_are_not_hidden_in_tools(self):
        for name in ("Jukebox", "Stats", "Editor", "Options"):
            props = theme("MainButton" + name)
            self.assertEqual("0", props.get("parent", "0"), name)
            self.assertEqual(44, int(props["h"]), name)

    def test_practice_hud_has_room_above_notes_and_draws_in_front(self):
        for name in (
            "CoachTitle",
            "CoachStatus",
            "CoachMetrics",
            "CoachState",
            "CoachHelp",
        ):
            props = theme(name)
            self.assertEqual(float(props.get("z", 0)), 1)
            self.assertGreaterEqual(int(props["size"]), 18)
            self.assertLess(int(props["y"]), 260)
        for i in range(1, 7):
            props = theme("CoachButton" + str(i))
            self.assertLessEqual(int(props["y"]) + int(props["h"]), 260)
            self.assertEqual(float(props.get("z", 0)), 1)

    def test_practice_copy_distinguishes_loop_reference_and_delay_state(self):
        chinese = ini("game/languages/Chinese.ini")["Text"]
        for key in (
            "coach_loop_on",
            "coach_loop_off",
            "coach_delay_pending",
            "coach_delay_ready",
            "coach_reference_ready",
            "coach_reference_auto",
            "coach_cents",
            "coach_paused",
        ):
            self.assertRegex(chinese.get(key, ""), r"[\u4e00-\u9fff]")

    def test_bundled_gui_font_covers_core_chinese_labels(self):
        chinese = ini("game/languages/Chinese.ini")["Text"]
        labels = "".join(v for k, v in chinese.items() if k.startswith("coach_"))
        fonts = ini("game/fonts/fonts.ini")
        gui = fonts[fonts.sections()[0]]
        paths = [
            ROOT / "game/fonts" / value
            for key, value in gui.items()
            if key == "regularfile" or key.startswith("regularfallbackfile")
        ]
        for character in sorted(set(labels)):
            if "\u4e00" <= character <= "\u9fff":
                self.assertTrue(
                    any(font_has(path, ord(character)) for path in paths), character
                )

    def test_practice_retains_mouse_hit_testing_even_after_fullscreen_change(self):
        source = (ROOT / "src/menu/UDisplay.pas").read_text(encoding="utf-8-sig")
        self.assertTrue("and (CoachMode <> cmPractice)" in source)
        self.assertTrue("Cursor_HiddenByScreen := HideForSong" in source)

    def test_practice_keeps_profile_initialization_before_song_start(self):
        source = (ROOT / "src/screens/UScreenMain.pas").read_text(encoding="utf-8-sig")
        self.assertTrue(
            "if Ini.OnSongClick = sSelectPlayer then FadeTo(@ScreenSong)" in source
        )
        self.assertTrue("ScreenName.Goto_SingScreen := false" in source)


if __name__ == "__main__":
    unittest.main()
