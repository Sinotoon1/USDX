#!/usr/bin/env python3
"""Prepare UltraStar songs with the existing local singing_coach model pipeline.

No model code, service credentials or machine-specific paths are bundled in songs.
Copyright 2026. SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import re
import shutil
import sys
import tempfile
import wave
from pathlib import Path


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def header(value):
    return " ".join(str(value).split()).replace("\x00", "")


def export_target(job, songs_root, lyrics_sha256=None):
    name = "coach-" + job["song_id"] + "-" + job["job_id"]
    if lyrics_sha256:
        if not re.fullmatch("[0-9a-f]{64}", lyrics_sha256):
            raise ValueError("invalid_lyrics_hash")
        name += "-lyrics-" + lyrics_sha256[:16]
    return Path(songs_root) / name


def export_reference(
    job_dir,
    songs_root,
    title,
    artist,
    *,
    allow_unreviewed=False,
    lyrics_path=None,
    require_lyrics=False,
    lyrics_sha256=None,
):
    """Validate all inputs before atomically publishing a new immutable song."""
    job_dir, songs_root = Path(job_dir), Path(songs_root)
    job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
    if job["status"] != "ready":
        raise ValueError("reference_not_ready")
    reviewed = job.get("review_status") == "reviewed"
    if not reviewed and not allow_unreviewed:
        raise ValueError(
            "reference_not_reviewed: audition and confirm in Python UI first"
        )
    for name in ("vocals.wav", "instrumental.wav", "pitch.json"):
        if digest(job_dir / name) != job["artifacts"].get(name):
            raise ValueError("artifact_hash_mismatch: " + name)
    timelines = []
    for name in ("vocals.wav", "instrumental.wav"):
        with wave.open(str(job_dir / name), "rb") as f:
            timelines.append(
                (f.getnframes(), f.getframerate(), f.getnchannels(), f.getsampwidth())
            )
    if timelines[0] != timelines[1] or timelines[0][0] <= 0:
        raise ValueError("stem_timeline_mismatch")
    duration = timelines[0][0] / timelines[0][1]
    pitch = json.loads((job_dir / "pitch.json").read_text(encoding="utf-8"))
    if pitch.get("status") != "ready" or pitch.get("origin") != "separated_vocals":
        raise ValueError("invalid_reference_origin")
    notes = pitch["notes"]
    if not notes:
        raise ValueError("empty_notes")
    rows, previous, phrase_start = [], -1, 0
    for note in notes:
        start, end, midi, confidence = (
            note[k] for k in ("start_seconds", "end_seconds", "midi", "confidence")
        )
        if (
            not all(
                isinstance(v, (int, float)) and math.isfinite(v)
                for v in (start, end, midi, confidence)
            )
            or not 0 <= start < end <= duration + 0.01
            or not isinstance(midi, int)
            or not 0 <= midi <= 127
            or not 0.7 <= confidence <= 1
        ):
            raise ValueError("invalid_reference_note")
        tick_start, tick_end = round(start * 100), round(end * 100)
        if tick_start < previous or tick_end <= tick_start:
            raise ValueError("overlapping_or_subtick_notes")
        if rows and (tick_start - previous >= 35 or tick_start - phrase_start >= 500):
            rows.append(f"- {previous}")
            phrase_start = tick_start
        rows.append(f": {tick_start} {tick_end - tick_start} {midi - 60} la")
        previous = tick_end
    lyrics, lyric_hash, lyric_lrc, alignment = None, None, None, None
    if require_lyrics and lyrics_path is None:
        raise ValueError("lyrics_required")
    if lyrics_path is not None:
        from coach_lyrics import align_words, read_lyrics, render_lrc

        lyric_hash = lyrics_sha256 or digest(lyrics_path)
        lyrics = read_lyrics(lyrics_path, job, duration, expected_hash=lyric_hash)
        chart, alignment = align_words(notes, lyrics["words"], duration)
        lyric_lrc = render_lrc(lyrics["words"])
        rows, previous, phrase_start = [], -1, 0
        for row in chart:
            start, end = row["start_tick"], row["end_tick"]
            if not rows:
                phrase_start = start
            if rows and (start - previous >= 35 or start - phrase_start >= 500):
                rows.append(f"- {previous}")
                phrase_start = start
            rows.append(
                f"{row['kind']} {start} {end - start} {row['midi'] - 60} {row['text']}"
            )
            previous = end
    for key in ("song_id", "job_id"):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", job[key]):
            raise ValueError("invalid_reference_id")
    source = Path(job["source_path"])
    if digest(source) != job["source_sha256"]:
        raise ValueError("source_hash_mismatch")
    suffix = source.suffix.lower()
    if suffix not in {
        ".wav",
        ".mp3",
        ".m4a",
        ".flac",
        ".ogg",
        ".opus",
        ".aac",
        ".webm",
    }:
        raise ValueError("unsupported_source_extension")
    target = export_target(job, songs_root, lyric_hash)
    if target.exists():
        raise FileExistsError(target)
    songs_root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".coach-staging-", dir=songs_root))
    try:
        audio = "audio" + suffix
        shutil.copyfile(source, stage / audio)
        for name in ("vocals.wav", "instrumental.wav", "pitch.json"):
            shutil.copyfile(job_dir / name, stage / name)
        expected = {**job["artifacts"], audio: job["source_sha256"]}
        if lyrics is not None:
            shutil.copyfile(lyrics_path, stage / "lyrics.json")
            (stage / "lyrics.lrc").write_text(lyric_lrc, encoding="utf-8", newline="\n")
            expected["lyrics.json"] = lyric_hash
            expected["lyrics.lrc"] = hashlib.sha256(
                lyric_lrc.encode("utf-8")
            ).hexdigest()
        if any(digest(stage / name) != expected[name] for name in expected):
            raise ValueError("artifact_changed_during_export")
        status = "reviewed" if reviewed else "auto"
        text = "\n".join(
            [
                "#VERSION:1.0.0",
                "#ENCODING:UTF8",
                "#TITLE:" + header(title),
                "#ARTIST:" + header(artist),
                "#AUDIO:" + audio,
                "#MP3:" + audio,
                "#INSTRUMENTAL:instrumental.wav",
                "#VOCALS:vocals.wav",
                "#BPM:1500",
                "#GAP:0",
                "#CREATOR:Python Singing Coach",
                "#COACH-REVIEW:" + status,
                *rows,
                "E",
                "",
            ]
        )
        (stage / "song.txt").write_text(text, encoding="utf-8", newline="\n")
        manifest = {
            "schema_version": 1,
            "reference_revision": job["job_id"],
            "song_id": job["song_id"],
            "review_status": status,
            "pipeline_version": job["pipeline_version"],
            "model_sha256": job["model_sha256"],
            "source_sha256": job["source_sha256"],
            "tick_seconds": 0.01,
            "note_count": alignment["chart_note_count"] if alignment else len(notes),
            "lyrics": "asr_dtw_word_alignment"
            if lyrics
            else "placeholder_la_not_transcribed",
            "files": {p.name: digest(p) for p in stage.iterdir()},
        }
        if lyrics is not None:
            manifest["lyrics_alignment"] = alignment
            manifest["lyrics_model_sha256"] = lyrics["model_sha256"]
            manifest["lyrics_review_status"] = "reviewed" if reviewed else "auto"
        (stage / "coach.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        stage.rename(target)
    finally:
        if stage.exists():
            if stage.resolve().parent != songs_root.resolve():
                raise ValueError("staging_cleanup_path_changed")
            shutil.rmtree(stage)
    return target


def prepare_existing(args):
    """Import/call the actual external ReferenceService, not a second implementation."""
    root = args.coach_root.resolve()
    if not (root / "src/singing_coach/reference.py").is_file():
        raise ValueError("coach_root_invalid")
    sys.path.insert(0, str(root / "src"))
    from singing_coach.reference import ReferenceService
    from singing_coach.storage import SongStore
    from starlette.datastructures import UploadFile

    data_root = args.data_root.resolve() if args.data_root else root / "data"
    store = SongStore(data_root, 500_000_000)
    store.prepare()
    if args.audio:
        with args.audio.open("rb") as stream:
            song = asyncio.run(
                store.import_upload(
                    UploadFile(stream, filename=args.audio.name), args.audio.name
                )
            )
        print("IMPORTED_SONG_ID=" + song.song_id, flush=True)
    else:
        song = store.get(args.song_id)
        if song is None:
            raise ValueError("song_not_found")
    source = store.source_path(song)
    if source is None:
        raise ValueError("song_audio_missing")
    service = ReferenceService(data_root, recover=False)
    job, created = service.create(song.song_id, source)
    if created:
        service.execute(job, source)
        job = service.read(job.job_id)
    if job is None or job.status != "ready" or not service.valid(job):
        raise ValueError("reference_build_not_ready: inspect Python reference job")
    return export_reference(
        service.root / job.job_id,
        args.songs_root,
        args.title,
        args.artist,
        allow_unreviewed=args.allow_unreviewed,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coach-root", type=Path, required=True)
    parser.add_argument(
        "--data-root", type=Path, help="Optional isolated data root for verification"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--song-id")
    source.add_argument("--audio", type=Path)
    parser.add_argument("--songs-root", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--artist", default="Unknown")
    parser.add_argument(
        "--allow-unreviewed",
        action="store_true",
        help="Explicitly export AUTO / unranked material; audition first for teaching",
    )
    args = parser.parse_args()
    try:
        target = prepare_existing(args)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f"COACH_ERROR: {exc}\n")
    print("EXPORTED=" + str(target.resolve()))


if __name__ == "__main__":
    main()
