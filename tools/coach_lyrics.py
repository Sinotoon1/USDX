"""Validated ASR words -> native lyric notes; no model dependencies at import time.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
from pathlib import Path
from uuid import uuid4

PIPELINE = "faster-whisper-dtw-v1"
MAX_LYRICS_BYTES = 2_000_000


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def model_fingerprint(directory):
    directory = Path(directory)
    required = ("config.json", "model.bin", "tokenizer.json")
    if not all((directory / name).is_file() for name in required):
        raise ValueError("lyrics_model_missing")
    names = list(required)
    if (directory / "vocabulary.json").is_file():
        names.append("vocabulary.json")
    names.sort()
    value = [(name, file_hash(directory / name)) for name in names]
    return hashlib.sha256(json.dumps(value).encode()).hexdigest()


def validate_words(words, duration):
    if (
        not isinstance(duration, (int, float))
        or not math.isfinite(duration)
        or not 0 < duration <= 600
    ):
        raise ValueError("invalid_lyrics_duration")
    if not isinstance(words, list) or not 0 < len(words) <= 20_000:
        raise ValueError("invalid_lyrics_words")
    previous = 0.0
    for word in words:
        if not isinstance(word, dict):
            raise ValueError("invalid_lyrics_word")
        start, end, probability = (
            word.get(k) for k in ("start_seconds", "end_seconds", "probability")
        )
        if (
            not all(
                isinstance(n, (int, float))
                and not isinstance(n, bool)
                and math.isfinite(n)
                for n in (start, end, probability)
            )
            or not previous <= start < end <= duration + 0.01
            or not 0 <= probability <= 1
            or round(end * 100) <= round(start * 100)
        ):
            raise ValueError("invalid_lyrics_timeline")
        text = word.get("text")
        if (
            not isinstance(text, str)
            or not text.strip()
            or len(text) > 120
            or any(ord(c) < 32 or ord(c) == 127 for c in text)
        ):
            raise ValueError("invalid_lyrics_text")
        previous = end
    return words


def read_lyrics(path, job, duration, *, expected_model=None, expected_hash=None):
    path = Path(path)
    if not 0 < path.stat().st_size <= MAX_LYRICS_BYTES:
        raise ValueError("invalid_lyrics_size")
    raw = path.read_bytes()
    if len(raw) > MAX_LYRICS_BYTES:
        raise ValueError("invalid_lyrics_size")
    if expected_hash and hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError("lyrics_changed")
    document = json.loads(raw.decode("utf-8"))
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != 1
        or document.get("status") != "ready"
        or document.get("pipeline_version") != PIPELINE
        or document.get("reference_revision") != job["job_id"]
        or document.get("source_sha256") != job["source_sha256"]
        or document.get("vocals_sha256") != job["artifacts"]["vocals.wav"]
        or not re.fullmatch("[0-9a-f]{64}", str(document.get("model_sha256", "")))
        or (expected_model and document["model_sha256"] != expected_model)
    ):
        raise ValueError("lyrics_reference_changed")
    actual = document.get("duration_seconds")
    if (
        not isinstance(actual, (int, float))
        or not math.isfinite(actual)
        or abs(actual - duration) > 0.03
    ):
        raise ValueError("lyrics_timeline_changed")
    validate_words(document.get("words"), duration)
    return document


def align_words(notes, words, duration):
    """Intersect measured intervals; retain pitch gaps as unscored freestyle.

    Word timestamps are never divided uniformly into invented character onsets.
    Work uses integer UltraStar ticks so rounding cannot produce overlapping notes.
    """
    validate_words(words, duration)
    pitches, previous = [], -1
    for note in notes:
        start, end, midi = (
            note.get(k) for k in ("start_seconds", "end_seconds", "midi")
        )
        if (
            not all(
                isinstance(n, (int, float)) and math.isfinite(n) for n in (start, end)
            )
            or not 0 <= start < end <= duration + 0.01
            or not isinstance(midi, int)
            or not 0 <= midi <= 127
        ):
            raise ValueError("invalid_reference_note")
        a, b = round(start * 100), round(end * 100)
        if a < previous or b <= a:
            raise ValueError("overlapping_or_subtick_notes")
        pitches.append((a, b, midi))
        previous = b
    rows, cursor = [], 0
    stats = dict(
        word_count=len(words),
        matched_word_count=0,
        freestyle_word_count=0,
        partially_pitched_word_count=0,
        low_confidence_word_count=sum(w["probability"] < 0.5 for w in words),
    )
    for index, word in enumerate(words):
        start, end = (
            round(word["start_seconds"] * 100),
            round(word["end_seconds"] * 100),
        )
        while cursor < len(pitches) and pitches[cursor][1] <= start:
            cursor += 1
        pieces, position, j = [], start, cursor
        while j < len(pitches) and pitches[j][0] < end:
            a, b, midi = pitches[j]
            a, b = max(a, start), min(b, end)
            if a > position:
                pieces.append(("F", position, a, 60))
            if b > a:
                pieces.append((":", a, b, midi))
            position = max(position, b)
            j += 1
        if position < end:
            pieces.append(("F", position, end, 60))
        pitched = any(p[0] == ":" for p in pieces)
        gaps = any(p[0] == "F" for p in pieces)
        stats["matched_word_count"] += pitched
        stats["freestyle_word_count"] += not pitched
        stats["partially_pitched_word_count"] += pitched and gaps
        for part, (kind, a, b, midi) in enumerate(pieces):
            rows.append(
                dict(
                    kind=kind,
                    start_tick=a,
                    end_tick=b,
                    midi=midi,
                    text=word["text"] if part == 0 else "~",
                    word_index=index,
                )
            )
    stats["chart_note_count"] = len(rows)
    stats["pitched_note_count"] = sum(r["kind"] == ":" for r in rows)
    return rows, stats


def render_lrc(words):
    lines = []
    for word in words:
        tick = round(word["start_seconds"] * 100)
        minute, remainder = divmod(tick, 6000)
        second, centisecond = divmod(remainder, 100)
        lines.append(f"[{minute:02}:{second:02}.{centisecond:02}]{word['text']}")
    return "\n".join(lines) + "\n"


def build_lyrics(engine_root, data_root, job, directory, runner, emit, cancelled):
    """Reuse a bound ASR cache or run the owned, independently installed child."""
    engine_root, data_root, directory = map(Path, (engine_root, data_root, directory))
    model = Path(
        os.environ.get(
            "USDX_LYRICS_MODEL", engine_root / ".models/faster-whisper-small"
        )
    ).resolve()
    emit(phase="lyrics")
    fingerprint = model_fingerprint(model)
    target = data_root / "lyrics" / job["job_id"] / fingerprint[:16] / "lyrics.json"
    if target.exists():
        try:
            read_lyrics(
                target, job, job["duration_seconds"], expected_model=fingerprint
            )
            return target
        except (OSError, ValueError, KeyError):
            pass
    runtime = Path(
        os.environ.get(
            "USDX_LYRICS_PYTHON",
            engine_root
            / ".lyrics-venv"
            / ("Scripts/python.exe" if os.name == "nt" else "bin/python"),
        )
    )
    if not runtime.is_file():
        raise ValueError("lyrics_runtime_missing")
    if cancelled():
        raise RuntimeError("cancelled")
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = target.with_name("pending-" + uuid4().hex + ".json")
    try:
        try:
            runner(
                [
                    str(runtime),
                    str(Path(__file__).with_name("coach_lyrics_worker.py")),
                    "--job",
                    str(directory / "job.json"),
                    "--model",
                    str(model),
                    "--output",
                    str(pending),
                    "--language",
                    os.environ.get("USDX_LYRICS_LANGUAGE", "zh"),
                ],
                target.parent / "worker.log",
                cancelled,
                emit,
                phase="lyrics",
            )
        except subprocess.CalledProcessError as error:
            raise RuntimeError("lyrics_recognition_failed") from error
        if cancelled():
            raise RuntimeError("cancelled")
        read_lyrics(pending, job, job["duration_seconds"], expected_model=fingerprint)
        pending.replace(target)
        return target
    finally:
        pending.unlink(missing_ok=True)
