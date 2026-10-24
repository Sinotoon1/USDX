"""Import workflow contracts; model work is injected, export uses the real bridge."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class ImportTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(ROOT / "tools"))
        self.addCleanup(sys.path.remove, str(ROOT / "tools"))
        spec = importlib.util.spec_from_file_location(
            "import_worker", ROOT / "tools/coach_import.py"
        )
        self.worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.worker)
        self.tmp = tempfile.TemporaryDirectory(prefix="中文 import ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / "task.json"
        self.source = self.root / "歌曲 sample.wav"
        with wave.open(str(self.source), "wb") as audio:
            audio.setparams((2, 2, 44100, 0, "NONE", "PCM"))
            audio.writeframes(bytes(44100 * 4 * 2))
        self.engine = self.fake_engine()

    def fake_engine(self):
        worker, root, source = self.worker, self.root, self.source

        class Engine:
            data_root = root / "data"
            directory = data_root / "references/revision"
            calls = 0

            def prepare(self, audio, emit, cancelled):
                self.calls += 1
                self.directory.mkdir(parents=True, exist_ok=True)
                import shutil

                for name in ("vocals.wav", "instrumental.wav"):
                    shutil.copyfile(audio, self.directory / name)
                pitch = {
                    "status": "ready",
                    "origin": "separated_vocals",
                    "notes": [
                        {
                            "start_seconds": 0.1,
                            "end_seconds": 1.2,
                            "midi": 69,
                            "confidence": 0.99,
                            "target_hz": 440,
                        }
                    ],
                    "frames": [],
                }
                (self.directory / "pitch.json").write_text(
                    json.dumps(pitch), encoding="utf-8"
                )
                self.job = {
                    "job_id": "revision",
                    "song_id": "song",
                    "status": "ready",
                    "review_status": "auto",
                    "source_path": str(source),
                    "source_sha256": worker.digest(source),
                    "model_sha256": "a" * 64,
                    "pipeline_version": "mdx-pyin-v1",
                    "duration_seconds": 2,
                    "note_count": 1,
                    "voiced_coverage": 0.8,
                    "artifacts": {
                        n: worker.digest(self.directory / n)
                        for n in ("vocals.wav", "instrumental.wav", "pitch.json")
                    },
                }
                self.save()
                emit(phase="separating")
                if cancelled():
                    raise worker.Cancelled()
                emit(phase="pitch")
                return self.job

            def verify(self, job_id):
                if job_id != self.job["job_id"]:
                    raise ValueError("reference_changed")
                for name, sha in self.job["artifacts"].items():
                    if worker.digest(self.directory / name) != sha:
                        raise ValueError("artifact_hash_mismatch")
                return self.job, self.directory

            def confirm(self, job):
                self.job["review_status"] = "reviewed"
                self.save()

            def prepare_lyrics(self, job, directory, emit, cancelled):
                emit(phase="lyrics")
                path = directory / "recognized-lyrics.json"
                path.write_text(
                    json.dumps(
                        dict(
                            schema_version=1,
                            status="ready",
                            pipeline_version="faster-whisper-dtw-v1",
                            reference_revision=job["job_id"],
                            source_sha256=job["source_sha256"],
                            vocals_sha256=job["artifacts"]["vocals.wav"],
                            model_sha256="b" * 64,
                            duration_seconds=job["duration_seconds"],
                            words=[
                                dict(
                                    start_seconds=0.1,
                                    end_seconds=0.6,
                                    text="晨",
                                    probability=0.9,
                                    segment=0,
                                ),
                                dict(
                                    start_seconds=0.6,
                                    end_seconds=1.2,
                                    text="光",
                                    probability=0.95,
                                    segment=0,
                                ),
                            ],
                        )
                    ),
                    encoding="utf-8",
                )
                return path

            def save(self):
                (self.directory / "job.json").write_text(
                    json.dumps(self.job), encoding="utf-8"
                )

        return Engine()

    def prepare(self):
        return self.worker.prepare(self.source, self.state, self.engine)

    def publish(self, confirmation="revision", title="歌曲"):
        return self.worker.publish(
            self.state, self.root / "songs", title, "歌手", confirmation, self.engine
        )

    def test_prepare_waits_for_confirmation_and_has_real_preview(self):
        result = self.prepare()
        self.assertEqual("ready", result["status"])
        self.assertEqual([[0.1, 1.2, 69]], result["preview"])
        self.assertEqual("auto", self.engine.job["review_status"])
        self.assertFalse((self.root / "songs").exists())
        self.assertEqual(result, self.worker.read_state(self.state))
        self.assertEqual(2, result["lyric_word_count"])
        self.assertTrue(Path(result["lyrics_path"]).is_file())
        self.assertEqual("晨光", result["lyrics_preview"])

    def test_modified_lyrics_cannot_be_confirmed_or_silently_export_la(self):
        ready = self.prepare()
        Path(ready["lyrics_path"]).write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "lyrics_changed"):
            self.publish()
        self.assertEqual("auto", self.engine.job["review_status"])
        self.assertFalse((self.root / "songs").exists())

    def test_explicit_current_revision_confirmation_required(self):
        self.prepare()
        for confirm in ("", "old-revision"):
            with self.assertRaisesRegex(ValueError, "confirmation_required"):
                self.publish(confirm)
        self.assertEqual("auto", self.engine.job["review_status"])
        self.assertFalse((self.root / "songs").exists())

    def test_publish_is_reviewed_atomic_idempotent_and_keeps_metadata(self):
        self.prepare()
        result = self.publish()
        target = Path(result["output_path"])
        before = {p.name: p.read_bytes() for p in target.iterdir()}
        self.assertIn(
            "#COACH-REVIEW:reviewed", (target / "song.txt").read_text(encoding="utf-8")
        )
        self.assertIn("#TITLE:歌曲", (target / "song.txt").read_text(encoding="utf-8"))
        again = self.publish()
        self.assertEqual(result["output_path"], again["output_path"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir()})
        with self.assertRaises(FileExistsError):
            self.publish(title="不覆盖")
        self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir()})

    def test_corrupt_reference_does_not_become_reviewed(self):
        self.prepare()
        (self.engine.directory / "pitch.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "artifact_hash_mismatch"):
            self.publish()
        self.assertEqual("auto", self.engine.job["review_status"])

    def test_cancel_before_work_leaves_no_reference_or_library(self):
        self.worker.cancel_path(self.state).touch()
        with self.assertRaises(self.worker.Cancelled):
            self.prepare()
        self.assertEqual(0, self.engine.calls)
        self.assertFalse((self.root / "songs").exists())

    def test_cancel_runner_reaps_its_child(self):
        flag = self.root / "cancel.flag"
        child = SimpleNamespace(
            returncode=None,
            poll=lambda: None,
            terminate=lambda: None,
            wait=lambda timeout: 0,
            kill=lambda: None,
        )
        with (
            patch.object(self.worker.subprocess, "Popen", return_value=child),
            patch.object(child, "terminate") as terminate,
            patch.object(child, "wait") as wait,
        ):
            flag.touch()
            with self.assertRaises(self.worker.Cancelled):
                self.worker.run_child(
                    [sys.executable, "worker.py"],
                    self.root / "worker.log",
                    flag.exists,
                    lambda **k: None,
                )
            terminate.assert_called_once()
            wait.assert_called()

    def test_invalid_file_and_oversized_state_fail_before_engine(self):
        invalid = self.root / "a.exe"
        invalid.write_bytes(b"x")
        with self.assertRaisesRegex(ValueError, "unsupported_audio"):
            self.worker.prepare(invalid, self.state, self.engine)
        self.assertEqual(0, self.engine.calls)
        self.state.write_bytes(b" " * 262145)
        with self.assertRaisesRegex(ValueError, "invalid_state"):
            self.worker.read_state(self.state)

    def test_cli_missing_engine_writes_terminal_error(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/coach_import.py"),
                "prepare",
                "--coach-root",
                str(self.root / "missing"),
                "--state",
                str(self.state),
                "--audio",
                str(self.source),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(1, result.returncode)
        self.assertEqual("failed", self.worker.read_state(self.state)["status"])
        self.assertEqual(
            "engine_missing", self.worker.read_state(self.state)["error_code"]
        )

    def test_native_json_request_preserves_unicode_and_quotes(self):
        self.prepare()
        request = self.root / "请求.json"
        self.worker.save_state(
            request,
            {"title": '中文 "歌曲"', "artist": "歌 手", "confirmation": "revision"},
        )
        args = [
            "coach_import.py",
            "publish",
            "--coach-root",
            str(self.root),
            "--state",
            str(self.state),
            "--songs-root",
            str(self.root / "songs"),
            "--request",
            str(request),
        ]
        with (
            patch.object(self.worker, "CoachEngine", return_value=self.engine),
            patch.object(sys, "argv", args),
        ):
            self.assertEqual(0, self.worker.main())
        text = Path(self.worker.read_state(self.state)["song_file"]).read_text(
            encoding="utf-8"
        )
        self.assertIn('#TITLE:中文 "歌曲"', text)
        self.assertIn("#ARTIST:歌 手", text)

    def test_corrupt_published_pack_is_not_reused(self):
        self.prepare()
        target = Path(self.publish()["output_path"])
        (target / "instrumental.wav").write_bytes(b"changed")
        with self.assertRaises(FileExistsError):
            self.publish()
        self.assertEqual(b"changed", (target / "instrumental.wav").read_bytes())


if __name__ == "__main__":
    unittest.main()
