#!/usr/bin/env python3
"""Local, isolated faster-whisper transcription with measured word timestamps.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import wave
from pathlib import Path
from uuid import uuid4

from coach_lyrics import PIPELINE, file_hash, model_fingerprint, validate_words


def transcribe(vocals, model, language="zh", threads=4, *, factory=None):
    if factory is None:
        from faster_whisper import WhisperModel

        factory = WhisperModel
    with wave.open(str(vocals), "rb") as audio:
        duration = audio.getnframes() / audio.getframerate()
    recognizer = factory(
        str(model),
        device="cpu",
        compute_type="int8",
        cpu_threads=threads,
        local_files_only=True,
    )
    segments, info = recognizer.transcribe(
        str(vocals),
        language=language or None,
        task="transcribe",
        word_timestamps=True,
        beam_size=5,
        vad_filter=False,
        condition_on_previous_text=False,
        temperature=0,
        hallucination_silence_threshold=2.0,
    )
    words, discarded, previous = [], 0, 0.0
    for segment in segments:
        for item in segment.words or ():
            text = item.word
            start, end = item.start, item.end
            if not all(math.isfinite(n) for n in (start, end, item.probability)):
                raise ValueError("invalid_asr_output")
            # Punctuation-only and zero-duration tokens have no singable interval.
            if (
                not text.strip()
                or not any(c.isalnum() for c in text)
                or round(end * 100) <= round(start * 100)
            ):
                discarded += 1
                continue
            if start < previous - 0.03 or end > duration + 0.03:
                raise ValueError("invalid_asr_timeline")
            start, end = max(previous, start, 0), min(end, duration)
            if round(end * 100) <= round(start * 100):
                discarded += 1
                continue
            words.append(
                dict(
                    start_seconds=start,
                    end_seconds=end,
                    text=text,
                    probability=item.probability,
                    segment=segment.id,
                )
            )
            previous = end
    validate_words(words, duration)
    return dict(
        duration_seconds=duration,
        language=info.language,
        words=words,
        discarded_token_count=discarded,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", default="zh")
    parser.add_argument("--threads", type=int, default=4, choices=range(1, 17))
    args = parser.parse_args()
    temporary = args.output.with_name(args.output.name + "." + uuid4().hex + ".tmp")
    try:
        job = json.loads(args.job.read_text(encoding="utf-8"))
        vocals = args.job.parent / "vocals.wav"
        if file_hash(vocals) != job["artifacts"]["vocals.wav"]:
            raise ValueError("vocals_changed")
        fingerprint = model_fingerprint(args.model)
        data = transcribe(vocals, args.model, args.language, args.threads)
        document = dict(
            schema_version=1,
            status="ready",
            pipeline_version=PIPELINE,
            reference_revision=job["job_id"],
            source_sha256=job["source_sha256"],
            vocals_sha256=job["artifacts"]["vocals.wav"],
            model_sha256=fingerprint,
            model_name=args.model.name,
            **data,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            json.dumps(document, ensure_ascii=False, allow_nan=False), encoding="utf-8"
        )
        temporary.replace(args.output)
        print(
            f"LYRICS_OK: {len(data['words'])} timestamped words; "
            f"{data['duration_seconds']:.3f} sec"
        )
        return 0
    except (OSError, ValueError, RuntimeError, ImportError, KeyError) as error:
        print("LYRICS_ERROR: " + str(error), file=sys.stderr)
        return 1
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
