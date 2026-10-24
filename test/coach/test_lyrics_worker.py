"""ASR boundary/cache tests, independent from optional heavy packages."""

import json
import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from coach_lyrics import build_lyrics, file_hash, model_fingerprint  # noqa: E402
from coach_lyrics_worker import transcribe  # noqa: E402


class LyricWorkerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.vocals = self.root / "vocals.wav"
        with wave.open(str(self.vocals), "wb") as output:
            output.setparams((1, 2, 16000, 0, "NONE", "PCM"))
            output.writeframes(bytes(32000))
        self.model = self.root / "model"
        self.model.mkdir()
        for name in ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt"):
            (self.model / name).write_bytes(b"fixture model bytes; not executable")

    def fake_factory(self, words, captured):
        class Model:
            def __init__(self, model, **kwargs):
                captured.update(kwargs)

            def transcribe(self, audio, **kwargs):
                captured.update(kwargs)
                return iter([SimpleNamespace(id=0, words=words)]), SimpleNamespace(
                    language="zh"
                )

        return Model

    def word(self, start, end, text="字"):
        return SimpleNamespace(start=start, end=end, word=text, probability=0.9)

    def test_local_cpu_model_uses_real_dtw_word_timestamp_api(self):
        captured = {}
        result = transcribe(
            self.vocals,
            self.model,
            factory=self.fake_factory([self.word(0.2, 0.8, "原创")], captured),
        )
        self.assertTrue(captured["local_files_only"])
        self.assertTrue(captured["word_timestamps"])
        self.assertEqual("int8", captured["compute_type"])
        self.assertFalse(captured["condition_on_previous_text"])
        self.assertEqual(0.2, result["words"][0]["start_seconds"])
        self.assertEqual("原创", result["words"][0]["text"])

    def test_empty_output_does_not_become_placeholder_lyrics(self):
        with self.assertRaisesRegex(ValueError, "invalid_lyrics_words"):
            transcribe(self.vocals, self.model, factory=self.fake_factory([], {}))

    def test_zero_duration_tokens_are_counted_not_given_fake_timestamps(self):
        result = transcribe(
            self.vocals,
            self.model,
            factory=self.fake_factory(
                [self.word(0.1, 0.1, "。"), self.word(0.2, 0.8, "原创")], {}
            ),
        )
        self.assertEqual(1, result["discarded_token_count"])
        self.assertEqual(1, len(result["words"]))

    def test_invalid_model_output_fails_closed(self):
        for words in (
            [self.word(float("nan"), 0.5)],
            [self.word(0.8, 2)],
            [self.word(0.5, 0.8), self.word(0.2, 0.6)],
        ):
            with self.subTest(words=words), self.assertRaises(ValueError):
                transcribe(
                    self.vocals, self.model, factory=self.fake_factory(words, {})
                )

    def test_vocabulary_txt_is_required_and_part_of_model_fingerprint(self):
        first = model_fingerprint(self.model)
        (self.model / "vocabulary.txt").write_bytes(b"changed")
        self.assertNotEqual(first, model_fingerprint(self.model))
        (self.model / "vocabulary.txt").unlink()
        with self.assertRaisesRegex(ValueError, "lyrics_model_missing"):
            model_fingerprint(self.model)

    def test_valid_cache_reuses_child_but_corrupt_cache_is_rebuilt(self):
        job = dict(
            job_id="reference",
            source_sha256="a" * 64,
            duration_seconds=1.0,
            artifacts={"vocals.wav": file_hash(self.vocals)},
        )
        calls = []

        def runner(command, log, cancelled, emit, **kwargs):
            calls.append(command)
            output = Path(command[command.index("--output") + 1])
            output.write_text(
                json.dumps(
                    dict(
                        schema_version=1,
                        status="ready",
                        pipeline_version="faster-whisper-dtw-v1",
                        reference_revision="reference",
                        source_sha256="a" * 64,
                        vocals_sha256=file_hash(self.vocals),
                        model_sha256=model_fingerprint(self.model),
                        duration_seconds=1.0,
                        words=[
                            dict(
                                start_seconds=0.1,
                                end_seconds=0.8,
                                text="原创",
                                probability=0.9,
                            )
                        ],
                    )
                ),
                encoding="utf-8",
            )

        env = {
            "USDX_LYRICS_MODEL": str(self.model),
            "USDX_LYRICS_PYTHON": sys.executable,
        }
        with patch.dict(os.environ, env):

            def build():
                return build_lyrics(
                    self.root,
                    self.root / "data",
                    job,
                    self.root,
                    runner,
                    lambda **kw: None,
                    lambda: False,
                )

            path = build()
            self.assertEqual(path, build())
            self.assertEqual(1, len(calls))
            path.write_text("{}", encoding="utf-8")
            build()
            self.assertEqual(2, len(calls))


if __name__ == "__main__":
    unittest.main()
