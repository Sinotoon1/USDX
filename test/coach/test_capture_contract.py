"""Capture wiring guards; coach_capture_test.pas executes the real URecord code."""

import json
import os
import unittest
from pathlib import Path

ROOT = Path(os.environ.get("USDX_ROOT", Path(__file__).resolve().parents[2]))


class CaptureContracts(unittest.TestCase):
    def test_no_format_is_rejected_before_pitch_analysis(self):
        source = (ROOT / "src/base/URecord.pas").read_text(encoding="utf-8")
        analysis = source.split("procedure TCaptureBuffer.AnalyzeBuffer;", 1)[1]
        analysis = analysis.split("function TCaptureBuffer.ArrayIndexOfMinimum", 1)[0]
        self.assertLess(
            analysis.index("if not Assigned(AudioFormat) then"),
            analysis.index("CoachDetectPitch("),
        )
        stop = source.split("procedure TCaptureBuffer.StopCapture();", 1)[1]
        stop = stop.split("{ TAudioInputProcessor }", 1)[0]
        self.assertIn("fCaptureActive := false", stop)
        self.assertNotIn("FreeAndNil(fAudioFormat)", stop)
        self.assertIn("ClearAnalysis;", stop)
        log = (ROOT / "src/base/ULog.pas").read_text(encoding="utf-8")
        self.assertIn("if not Assigned(FormatInfo) or not Assigned(Buffer) then", log)

    def test_failed_device_start_unlinks_capture_buffers(self):
        source = (ROOT / "src/base/URecord.pas").read_text(encoding="utf-8")
        start = source.split("if not Device.Start() then", 1)[1]
        start = start.split("Started := true;", 1)[0]
        self.assertIn("Device.LinkCaptureBuffer(ChannelIndex, nil)", start)

    def test_listening_hint_precedes_pitch_tick_gate(self):
        source = (ROOT / "src/screens/controllers/UScreenSingController.pas").read_text(
            encoding="utf-8"
        )
        update = source.split("procedure TScreenSingController.CoachUpdate;", 1)[1]
        self.assertLess(
            update.index("'COACH_NO_MIC'"),
            update.index("if Sound.CoachPitchTick = fCoachTick"),
        )
        self.assertIn(
            "CheckPlayerConfigOnNextSong and (CoachMode <> cmPractice)", source
        )
        copy = json.loads(
            (ROOT / "tools/studio-design.json").read_text(encoding="utf-8")
        )["copy"]
        for key in ("COACH_NO_MIC", "COACH_NO_MIC_HELP"):
            self.assertEqual(2, len(copy[key]))
            for lang in ("Chinese", "English"):
                self.assertIn(
                    key + "=",
                    (ROOT / f"game/languages/{lang}.ini").read_text(encoding="utf-8"),
                )

    def test_ci_runs_production_capture_fixture_after_native_compile(self):
        workflow = (ROOT / ".github/workflows/coach.yml").read_text(encoding="utf-8")
        self.assertLess(
            workflow.index("./autogen.sh && ./configure && make"),
            workflow.index("Real capture buffer no-microphone regression"),
        )
        self.assertIn("build_capture_project.py", workflow)
        self.assertIn("../coach-capture-bin/coach_capture_runtime.exe", workflow)
        self.assertIn("runtime_manifest.py", workflow)
        self.assertIn("USDX-Coach-windows-update", workflow)


if __name__ == "__main__":
    unittest.main()
