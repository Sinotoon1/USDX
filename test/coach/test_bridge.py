import hashlib
import importlib.util
import json
import tempfile
import unittest
import wave
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2] / "tools" / "coach_bridge.py"


class BridgeTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("bridge", MODULE)
        self.bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.bridge)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.job = self.root / "reference"
        self.job.mkdir()
        self.out = self.root / "songs"
        for name in ("vocals.wav", "instrumental.wav"):
            with wave.open(str(self.job / name), "wb") as f:
                f.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
                f.writeframes(bytes(44100 * 2 * 2 * 3))
        pitch = {
            "status": "ready",
            "origin": "separated_vocals",
            "notes": [
                {
                    "start_seconds": 0.50,
                    "end_seconds": 1.00,
                    "midi": 69,
                    "target_hz": 440,
                    "confidence": 0.99,
                },
                {
                    "start_seconds": 1.50,
                    "end_seconds": 2.00,
                    "midi": 60,
                    "target_hz": 261.625565,
                    "confidence": 0.95,
                },
            ],
            "frames": [],
        }
        (self.job / "pitch.json").write_text(json.dumps(pitch), encoding="utf-8")
        self.metadata = {
            "job_id": "example-revision",
            "song_id": "example-song",
            "status": "ready",
            "review_status": "reviewed",
            "source_path": str(self.job / "vocals.wav"),
            "source_sha256": hashlib.sha256(
                (self.job / "vocals.wav").read_bytes()
            ).hexdigest(),
            "model_sha256": "b" * 64,
            "pipeline_version": "mdx-pyin-v1",
        }
        self.save_job()

    def save_job(self):
        self.metadata["artifacts"] = {
            n: hashlib.sha256((self.job / n).read_bytes()).hexdigest()
            for n in ("vocals.wav", "instrumental.wav", "pitch.json")
        }
        (self.job / "job.json").write_text(json.dumps(self.metadata), encoding="utf-8")

    def export(self, **kw):
        return self.bridge.export_reference(
            self.job, self.out, "测试歌曲", "歌手", **kw
        )

    def test_exports_exact_time_and_midi_mapping(self):
        target = self.export()
        text = (target / "song.txt").read_text(encoding="utf-8")
        self.assertIn("#BPM:1500\n", text)
        self.assertIn(": 50 50 9 la", text)
        self.assertIn(": 150 50 0 la", text)
        self.assertIn("#INSTRUMENTAL:instrumental.wav", text)
        self.assertEqual(
            (target / "pitch.json").read_bytes(), (self.job / "pitch.json").read_bytes()
        )
        manifest = json.loads((target / "coach.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["reference_revision"], "example-revision")
        self.assertNotIn(str(self.root), json.dumps(manifest))

    def test_refuses_overwrite(self):
        self.export()
        with self.assertRaises(FileExistsError):
            self.export()

    def test_unreviewed_requires_explicit_flag(self):
        self.metadata["review_status"] = "auto"
        self.save_job()
        with self.assertRaisesRegex(ValueError, "reference_not_reviewed"):
            self.export()
        target = self.export(allow_unreviewed=True)
        self.assertIn(
            "#COACH-REVIEW:auto", (target / "song.txt").read_text(encoding="utf-8")
        )

    def test_changed_artifact_is_rejected(self):
        (self.job / "pitch.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "artifact_hash_mismatch"):
            self.export()

    def test_invalid_notes_leave_no_partial_song(self):
        for change in (
            {"start_seconds": float("nan")},
            {"end_seconds": 0.4},
            {"midi": 200},
            {"start_seconds": 1.7, "end_seconds": 2.4},
        ):
            p = json.loads((self.job / "pitch.json").read_text(encoding="utf-8"))
            original = p["notes"][0].copy()
            p["notes"][0].update(change)
            (self.job / "pitch.json").write_text(json.dumps(p), encoding="utf-8")
            self.save_job()
            with self.assertRaises(ValueError):
                self.export()
            self.assertEqual(list(self.out.glob("*")) if self.out.exists() else [], [])
            p["notes"][0] = original
            (self.job / "pitch.json").write_text(json.dumps(p), encoding="utf-8")

    def test_metadata_cannot_inject_headers(self):
        target = self.bridge.export_reference(
            self.job, self.out, "a\n#BPM:1", "../歌手"
        )
        text = (target / "song.txt").read_text(encoding="utf-8")
        self.assertEqual(sum(line.startswith("#BPM:") for line in text.splitlines()), 1)
        self.assertEqual(target.parent, self.out)

    def test_stem_duration_mismatch_is_rejected(self):
        with wave.open(str(self.job / "vocals.wav"), "wb") as f:
            f.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
            f.writeframes(bytes(44100 * 4))
        self.save_job()
        with self.assertRaisesRegex(ValueError, "stem_timeline_mismatch"):
            self.export()


if __name__ == "__main__":
    unittest.main()
