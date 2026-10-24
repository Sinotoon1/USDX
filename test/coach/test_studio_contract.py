"""Studio native UI contracts; runtime input/render scenarios are separate."""

import configparser
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(os.environ.get("USDX_ROOT", Path(__file__).resolve().parents[2]))


class StudioContracts(unittest.TestCase):
    def test_native_text_hard_wrap_requires_a_bounded_width(self):
        # Companion native fixture: explicit two-line text with W=0.
        source = (ROOT / "src/menu/UMenuText.pas").read_text(encoding="utf-8")
        start = source.index("procedure BreakLongWord;")
        helper = source[start : source.index("Bound := LastBreak;", start)]
        self.assertIn("if (W <= 0)", helper)

    def test_generator_handles_non_utf8_windows_system_locale(self):
        spec = importlib.util.spec_from_file_location(
            "studio_generator", ROOT / "tools/build_studio_theme.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original_open = io.open

        def western_open(
            file,
            mode="r",
            buffering=-1,
            encoding=None,
            errors=None,
            newline=None,
            closefd=True,
            opener=None,
        ):
            if "b" not in mode and encoding in (None, "locale"):
                encoding = "cp1252"
            return original_open(
                file, mode, buffering, encoding, errors, newline, closefd, opener
            )

        with patch("io.open", western_open):
            outputs, design = module.generate()
        self.assertIn("game/themes/Studio.ini", outputs)
        self.assertEqual("声乐练习室", design["copy"]["STUDIO_BRAND"][0])

    def test_all_loaded_pages_have_explicit_light_backgrounds(self):
        source = (ROOT / "src/base/UThemes.pas").read_text(encoding="utf-8")
        pages = set(re.findall(r"ThemeLoadBasic\s*\([^,]+,\s*'([^']+)'\)", source))
        theme = configparser.RawConfigParser(strict=False)
        theme.read(ROOT / "game/themes/Studio.ini", encoding="utf-8")
        self.assertIn("Edit", pages)
        for page in pages:
            with self.subTest(page=page):
                background = theme[page + "Background"]
                if background["type"] == "Color":
                    self.assertTrue(
                        all(
                            float(background[k]) > 0.9 for k in ("colr", "colg", "colb")
                        )
                    )
                else:
                    self.assertEqual("Fade", background["type"])

    def test_flat_controls_keep_stable_geometry_and_no_bitmap_fade(self):
        theme = configparser.RawConfigParser(strict=False)
        theme.read(ROOT / "game/themes/Studio.ini", encoding="utf-8")
        for name in theme.sections():
            props = theme[name]
            if "Button" in name and props.get("flat") == "1":
                with self.subTest(name=name):
                    self.assertEqual("", props.get("fadetex", ""))
                    self.assertEqual(props["w"], props.get("selectw"))
                    self.assertEqual(props["h"], props.get("selecth"))

    def test_song_list_and_stage_use_readable_native_rendering(self):
        song = (ROOT / "src/screens/UScreenSong.pas").read_text(encoding="utf-8")
        draw = (ROOT / "src/base/UDraw.pas").read_text(encoding="utf-8")
        self.assertIn("if Theme.Studio.Enabled then Alpha := 1", song)
        self.assertIn("StaticsList[I].Visible := I <= High(SongID)", song)
        self.assertIn("StudioNoteBar", draw)
        self.assertIn(
            "if not Theme.Studio.Enabled then Renderer.DrawTexture(Texture)", draw
        )

    def test_search_popup_and_library_heading_do_not_reuse_legacy_white_text(self):
        theme = configparser.RawConfigParser(strict=False)
        theme.read(ROOT / "game/themes/Studio.ini", encoding="utf-8")
        search = theme["SongJumptoSelectSlideType"]
        self.assertEqual("StudioInk", search["tcolor"])
        self.assertEqual("StudioAccent", search["stcolor"])
        self.assertEqual("1", theme["SongJumptoButtonSearchText"]["texts"])
        self.assertEqual("", theme["SongListTextCat"]["text"])
        self.assertGreaterEqual(int(theme["SongListTextCat"]["y"]), 500)

    def test_native_required_fields_survive_section_level_inheritance(self):
        theme = configparser.RawConfigParser(strict=False)
        theme.read(ROOT / "game/themes/Studio.ini", encoding="utf-8")
        for name in (
            "NamePlayerButtonName",
            "MainButtonMulti",
            "MainButtonSolo",
            "OptionsSubButton",
        ):
            with self.subTest(name=name):
                self.assertGreater(int(theme[name]["w"]), 0)
                self.assertGreater(int(theme[name]["h"]), 0)
                self.assertGreater(int(theme[name]["texts"]), 0)
                self.assertGreater(int(theme[name + "Text1"]["size"]), 0)
        for name in ("NameSelectPlayerCount", "OptionsSubSelectSlide"):
            self.assertGreater(int(theme[name]["sbgw"]), 0)

    def test_all_light_surfaces_have_readable_text(self):
        colors = json.loads(
            (ROOT / "tools/studio-design.json").read_text(encoding="utf-8")
        )["colors"]

        def luminance(rgb):
            linear = [
                c / 3294.6 if c <= 10 else ((c / 255 + 0.055) / 1.055) ** 2.4
                for c in rgb
            ]
            return sum(c * w for c, w in zip(linear, (0.2126, 0.7152, 0.0722)))

        for ink, paper in (
            ("StudioInk", "StudioCanvas"),
            ("StudioMuted", "StudioSurface"),
            ("StudioStageText", "StudioStage"),
            ("StudioFlat", "StudioStage"),
            ("StudioSharp", "StudioStage"),
            ("StudioClose", "StudioStage"),
        ):
            a, b = sorted((luminance(colors[ink]), luminance(colors[paper])))
            self.assertGreaterEqual((b + 0.05) / (a + 0.05), 4.5, ink)
        self.assertGreater(luminance(colors["StudioStage"]), 0.9)

    def test_studio_is_a_real_native_theme_with_own_skin(self):
        theme = configparser.RawConfigParser(strict=False)
        theme.read(ROOT / "game/themes/Studio.ini", encoding="utf-8")
        self.assertIn("Studio", theme, "native Studio theme must exist")
        self.assertEqual("1", theme["Studio"]["Enabled"])
        self.assertTrue((ROOT / "game/themes/Deluxe/Studio.ini").is_file())

    def test_design_has_motion_and_semantic_palette(self):
        design = json.loads(
            (ROOT / "tools/studio-design.json").read_text(encoding="utf-8")
        )
        self.assertEqual(8, design["spacing"])
        self.assertLessEqual(design["motion"]["PageMs"], 240)
        for name in (
            "StudioCanvas",
            "StudioSurface",
            "StudioInk",
            "StudioMuted",
            "StudioAccent",
            "StudioSoft",
            "StudioBorder",
            "StudioStage",
        ):
            self.assertIn(name, design["colors"])

    def test_native_controls_and_transition_use_the_shared_motion(self):
        button = (ROOT / "src/menu/UMenuButton.pas").read_text(encoding="utf-8")
        menu = (ROOT / "src/menu/UMenu.pas").read_text(encoding="utf-8")
        display = (ROOT / "src/menu/UDisplay.pas").read_text(encoding="utf-8")
        self.assertIn("RetargetMotion", button)
        self.assertIn("PointerUp", menu)
        self.assertIn("StudioPageProgress", display)
        self.assertIn("Studio.Enabled", display)

    def test_theme_generation_is_reproducible(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/build_studio_theme.py"), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
