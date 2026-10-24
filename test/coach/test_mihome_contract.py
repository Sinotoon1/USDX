"""MiHome-inspired native design contracts; no dependency on the reference app."""

import configparser
import importlib.util
import json
import os
import unittest
from pathlib import Path

ROOT = Path(os.environ.get("USDX_ROOT", Path(__file__).resolve().parents[2]))


class MiHomeContracts(unittest.TestCase):
    def setUp(self):
        self.design = json.loads(
            (ROOT / "tools/studio-design.json").read_text(encoding="utf-8")
        )
        self.theme = configparser.RawConfigParser(strict=False)
        self.theme.read(ROOT / "game/themes/Studio.ini", encoding="utf-8")

    def test_live_translations_match_design_copy(self):
        for index, language in enumerate(("Chinese", "English")):
            translated = configparser.RawConfigParser(strict=False)
            translated.optionxform = str
            translated.read(
                ROOT / f"game/languages/{language}.ini", encoding="utf-8-sig"
            )
            for key, values in self.design["copy"].items():
                self.assertEqual(
                    values[index].replace("\n", r"\n"), translated["Text"][key]
                )

    def test_copy_generator_only_updates_the_text_section(self):
        spec = importlib.util.spec_from_file_location(
            "studio", ROOT / "tools/build_studio_theme.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = (
            "[Text]\nOTHER=keep\nSTUDIO_HOME=old\n\n[config]\nSTUDIO_HOME=untouched\n"
        )
        expected = (
            "[Text]\nOTHER=keep\nSTUDIO_HOME=new\n\nSTUDIO_NEW=one\\ntwo\n"
            "[config]\nSTUDIO_HOME=untouched\n"
        )
        self.assertEqual(
            expected,
            module.update_studio_copy(
                source, {"STUDIO_HOME": "new", "STUDIO_NEW": "one\ntwo"}
            ),
        )

    def test_cool_light_palette_and_distinct_action_ink(self):
        colors = self.design["colors"]
        self.assertEqual([242, 243, 245], colors["StudioCanvas"])
        self.assertEqual([61, 187, 164], colors["StudioAction"])
        self.assertEqual([255, 255, 255], colors["StudioSurface"])
        self.assertNotEqual(colors["StudioAction"], colors["StudioAccent"])
        self.assertEqual(14, self.design["radius"])

    def test_modes_are_equal_white_cards_with_single_action_target(self):
        practice, play = [self.theme[n] for n in ("MainButtonMulti", "MainButtonSolo")]
        self.assertEqual(practice["w"], play["w"])
        self.assertEqual(practice["h"], play["h"])
        for card in (practice, play):
            self.assertEqual("StudioSurface", card["dcolor"])
            self.assertEqual("StudioHover", card["color"])
            self.assertEqual("1", card["action"])
        self.assertLessEqual(int(self.theme["MainText1"]["size"]), 34)

    def test_home_targets_are_on_canvas_and_do_not_overlap(self):
        rects = []
        for name in (
            "Multi",
            "Solo",
            "Jukebox",
            "Stats",
            "Editor",
            "Options",
            "About",
            "Exit",
        ):
            p = self.theme["MainButton" + name]
            rect = tuple(int(p[k]) for k in ("x", "y", "w", "h"))
            x, y, w, h = rect
            self.assertTrue(24 <= x < x + w <= 776 and 56 <= y < y + h <= 552, name)
            for xx, yy, ww, hh in rects:
                self.assertTrue(
                    x + w <= xx or xx + ww <= x or y + h <= yy or yy + hh <= y
                )
            rects.append(rect)

    def test_action_field_is_explicit_opt_in_not_screen_specific(self):
        loader = (ROOT / "src/base/UThemes.pas").read_text(encoding="utf-8")
        menu = (ROOT / "src/menu/UMenu.pas").read_text(encoding="utf-8")
        button = (ROOT / "src/menu/UMenuButton.pas").read_text(encoding="utf-8")
        self.assertIn(
            "ThemeButton.Action := ReadBool(SectionList, 'Action', false)", loader
        )
        self.assertIn("Theme.Studio.Enabled and ThemeButton.Action", menu)
        self.assertIn("PressValue, Selectable, Action)", button)


if __name__ == "__main__":
    unittest.main()
