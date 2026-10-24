"""Native import wiring and stable theme geometry, supplemented by native flow QA."""

import configparser
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ImportNativeContracts(unittest.TestCase):
    def test_ready_lyrics_are_visible_and_freestyle_is_not_a_pitch_target(self):
        screen = (ROOT / "src/screens/UScreenCoachImport.pas").read_text(
            encoding="utf-8"
        )
        controller = (ROOT / "src/base/UCoachImport.pas").read_text(encoding="utf-8")
        self.assertIn("Language.Translate('IMPORT_LYRICS_PREVIEW')", screen)
        self.assertIn("Obj.Get('lyric_word_count', 0)", controller)
        singing = (
            ROOT / "src/screens/controllers/UScreenSingController.pas"
        ).read_text(encoding="utf-8")
        self.assertIn("Line.Notes[I].NoteType in [ntNormal, ntGolden]", singing)

    def test_shortcuts_use_event_modifiers_not_the_already_released_global_state(self):
        source = (ROOT / "src/base/UMain.pas").read_text(encoding="utf-8")
        screen = (ROOT / "src/screens/UScreenCoachImport.pas").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "ScreenCoachImport.InputModifiers := Event.key.keysym._mod", source
        )
        self.assertNotIn("SDL_GetModState", screen)

    def test_windows_picker_uses_an_explicit_wide_record_abi(self):
        source = (ROOT / "src/base/UCoachImport.pas").read_text(encoding="utf-8")
        self.assertIn("ImportOpenFileName(var Info: TOpenFilenameW)", source)
        self.assertIn("external 'comdlg32.dll' name 'GetOpenFileNameW'", source)

    def test_imported_covers_rebuild_resets_reserved_button_cursor(self):
        source = (ROOT / "src/screens/UScreenSong.pas").read_text(encoding="utf-8")
        body = source.split("procedure TScreenSong.RebuildImportedCatalogue;", 1)[
            1
        ].split("procedure TScreenSong.GenerateThumbnails", 1)[0]
        self.assertIn("ButtonPos := -1", body)
        self.assertIn("SetLength(Interactions, 0)", body)
        self.assertLess(body.index("ButtonPos := -1"), body.index("GenerateThumbnails"))

    def test_native_ime_delivers_the_complete_commit_not_just_first_codepoint(self):
        main = (ROOT / "src/base/UMain.pas").read_text(encoding="utf-8")
        self.assertIn("ScreenCoachImport.InsertText(UTF8String(Event.text.text))", main)

    def test_home_entry_and_import_page_are_real_native_routes(self):
        main = (ROOT / "src/screens/UScreenMain.pas").read_text(encoding="utf-8")
        self.assertIn("ScreenCoachImport", main)
        self.assertIn("SDLK_F7", main)
        screen = (ROOT / "src/screens/UScreenCoachImport.pas").read_text(
            encoding="utf-8"
        )
        self.assertIn("ImportCanPublish", screen)
        self.assertIn("AudioPlayback.Open", screen)

    def test_new_song_is_incremental_and_deduplicated(self):
        source = (ROOT / "src/base/USongs.pas").read_text(encoding="utf-8")
        self.assertIn("function TSongs.AddImportedSong", source)
        body = source.split("function TSongs.AddImportedSong", 1)[1].split(
            "procedure TSongs.", 1
        )[0]
        self.assertIn(".Equals", body)
        self.assertNotIn("LoadSongList", body)
        self.assertIn(".coach-staging-", source)

    def test_import_controls_fit_native_canvas_and_main_index_is_not_legacy_description(
        self,
    ):
        theme = configparser.RawConfigParser(strict=False)
        theme.read(ROOT / "game/themes/Studio.ini", encoding="utf-8")
        for name in ("File", "Title", "Artist", "Analyze", "Listen", "Publish", "Back"):
            p = theme["CoachImportButton" + name]
            x, y, w, h = [int(p[k]) for k in ("x", "y", "w", "h")]
            self.assertTrue(24 <= x < x + w <= 776 and 140 <= y < y + h <= 552)
            self.assertEqual("1", p["flat"])
        main = (ROOT / "src/screens/UScreenMain.pas").read_text(encoding="utf-8")
        self.assertIn("if Num = 8 then", main)


if __name__ == "__main__":
    unittest.main()
