"""Synthetic original lyrics exercise alignment without distributing song lyrics."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import test_bridge as fixtures  # noqa: E402
from coach_lyrics import align_words, read_lyrics, render_lrc  # noqa: E402


def word(start, end, text, probability=0.95):
    return dict(
        start_seconds=start,
        end_seconds=end,
        text=text,
        probability=probability,
        segment=0,
    )


def note(start, end, midi=69):
    return dict(start_seconds=start, end_seconds=end, midi=midi)


class LyricAlignmentTests(unittest.TestCase):
    def test_two_words_split_one_pitch_note_at_actual_word_boundary(self):
        rows, stats = align_words(
            [note(0.1, 1.5)], [word(0.1, 0.7, "星"), word(0.7, 1.5, "光")], 2
        )
        self.assertEqual(
            [(10, 70, "星"), (70, 150, "光")],
            [(r["start_tick"], r["end_tick"], r["text"]) for r in rows],
        )
        self.assertTrue(all(r["kind"] == ":" and r["midi"] == 69 for r in rows))
        self.assertEqual(2, stats["matched_word_count"])

    def test_melisma_has_one_real_word_then_continuation_not_repetition(self):
        rows, _ = align_words(
            [note(0.1, 0.4), note(0.4, 0.8, 72)], [word(0.1, 0.8, "亮")], 2
        )
        self.assertEqual(["亮", "~"], [r["text"] for r in rows])

    def test_missing_pitch_keeps_words_as_unscored_freestyle_not_fake_pitch(self):
        rows, stats = align_words(
            [note(0.5, 1.0)], [word(0.1, 0.3, "看"), word(0.5, 1.0, "见")], 2
        )
        self.assertEqual(["F", ":"], [r["kind"] for r in rows])
        self.assertEqual(["看", "见"], [r["text"] for r in rows])
        self.assertEqual(1, stats["freestyle_word_count"])

    def test_partially_pitched_word_keeps_gap_as_freestyle(self):
        rows, stats = align_words([note(0.4, 0.6)], [word(0.2, 0.8, "你")], 2)
        self.assertEqual(["F", ":", "F"], [r["kind"] for r in rows])
        self.assertEqual(["你", "~", "~"], [r["text"] for r in rows])
        self.assertEqual(1, stats["partially_pitched_word_count"])

    def test_invalid_word_timeline_and_control_text_are_rejected(self):
        for words in (
            [word(0.4, 0.3, "字")],
            [word(0, 3, "字")],
            [word(float("nan"), 0.4, "字")],
            [word(0, 1, "#TITLE:假\n字")],
            [word(0, 1, " ")],
            [word(0, 1, "字", float("nan"))],
            [word(0.5, 1, "一"), word(0.4, 0.8, "二")],
            [],
        ):
            with self.subTest(words=words), self.assertRaises(ValueError):
                align_words([note(0, 1)], words, 2)

    def test_lrc_uses_word_onsets_without_inventing_character_timestamps(self):
        result = render_lrc([word(59.999, 60.8, "微风"), word(61, 62, "来")])
        self.assertIn("[01:00.00]微风", result)
        self.assertIn("[01:01.00]来", result)
        self.assertNotIn("[01:00.40]", result)

    def test_quantization_does_not_create_overlapping_or_zero_tick_rows(self):
        rows, _ = align_words(
            [note(0.101, 0.207), note(0.207, 0.4)],
            [word(0.101, 0.209, "一"), word(0.209, 0.4, "二")],
            1,
        )
        self.assertTrue(all(r["end_tick"] > r["start_tick"] for r in rows))
        self.assertTrue(
            all(a["end_tick"] <= b["start_tick"] for a, b in zip(rows, rows[1:]))
        )


class LyricsBridgeTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.BridgeTests(methodName="runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.doc = dict(
            schema_version=1,
            status="ready",
            pipeline_version="faster-whisper-dtw-v1",
            reference_revision="example-revision",
            source_sha256=fixture.metadata["source_sha256"],
            vocals_sha256=fixture.metadata["artifacts"]["vocals.wav"],
            model_sha256="c" * 64,
            model_name="small",
            language="zh",
            duration_seconds=3,
            words=[word(0.5, 1.0, "晨"), word(1.5, 2.0, "光")],
        )
        self.lyrics = fixture.root / "lyrics.json"
        self.save()

    def save(self):
        self.lyrics.write_text(
            json.dumps(self.doc, ensure_ascii=False), encoding="utf-8"
        )

    def export(self, **kwargs):
        return self.fixture.bridge.export_reference(
            self.fixture.job,
            self.fixture.out,
            "原创测试",
            "测试",
            lyrics_path=self.lyrics,
            require_lyrics=True,
            **kwargs,
        )

    def test_real_lyrics_and_alignment_sidecars_are_in_atomic_pack(self):
        pack = self.export()
        text = (pack / "song.txt").read_text(encoding="utf-8")
        self.assertIn(": 50 50 9 晨", text)
        self.assertIn(": 150 50 0 光", text)
        self.assertNotIn(" la", text)
        manifest = json.loads((pack / "coach.json").read_text(encoding="utf-8"))
        self.assertEqual("asr_dtw_word_alignment", manifest["lyrics"])
        for name in ("lyrics.json", "lyrics.lrc"):
            self.assertEqual(
                self.fixture.bridge.digest(pack / name), manifest["files"][name]
            )

    def test_changed_source_or_reference_cannot_reuse_lyrics(self):
        for key in ("source_sha256", "vocals_sha256", "reference_revision"):
            original = self.doc[key]
            self.doc[key] = "wrong"
            self.save()
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.export()
            self.doc[key] = original

    def test_missing_lyrics_never_falls_back_to_la_when_required(self):
        with self.assertRaisesRegex(ValueError, "lyrics_required"):
            self.fixture.export(require_lyrics=True)
        self.assertFalse(self.fixture.out.exists())

    def test_oversized_lyrics_json_is_rejected(self):
        self.lyrics.write_bytes(b" " * 2_000_001)
        with self.assertRaisesRegex(ValueError, "invalid_lyrics"):
            read_lyrics(self.lyrics, self.fixture.metadata, 3)

    def test_old_placeholder_pack_is_preserved_beside_lyric_revision(self):
        old = self.fixture.export()
        before = (old / "song.txt").read_bytes()
        new = self.export()
        self.assertNotEqual(old, new)
        self.assertEqual(before, (old / "song.txt").read_bytes())
        self.assertIn("-lyrics-", new.name)

    def test_intro_does_not_split_the_first_lyric_word_into_its_own_phrase(self):
        import wave

        f = self.fixture
        for name in ("vocals.wav", "instrumental.wav"):
            with wave.open(str(f.job / name), "wb") as audio:
                audio.setparams((2, 2, 44100, 0, "NONE", "PCM"))
                audio.writeframes(bytes(44100 * 4 * 9))
        pitch = json.loads((f.job / "pitch.json").read_text(encoding="utf-8"))
        for index, n in enumerate(pitch["notes"]):
            n["start_seconds"], n["end_seconds"] = 6 + index * 0.5, 6.5 + index * 0.5
        (f.job / "pitch.json").write_text(json.dumps(pitch), encoding="utf-8")
        f.metadata["source_sha256"] = f.bridge.digest(f.job / "vocals.wav")
        f.save_job()
        self.doc.update(
            duration_seconds=9,
            source_sha256=f.metadata["source_sha256"],
            vocals_sha256=f.metadata["artifacts"]["vocals.wav"],
            words=[word(6, 6.5, "晨"), word(6.5, 7, "光")],
        )
        self.save()
        text = (self.export() / "song.txt").read_text(encoding="utf-8")
        self.assertFalse(any(line.startswith("- ") for line in text.splitlines()))


if __name__ == "__main__":
    unittest.main()
